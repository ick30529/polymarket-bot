import asyncio
import logging
import threading
from datetime import date

from config import load_config
from core.event_bus import EventBus, OrderbookEvent
from core.market_scanner import MarketScanner
from core.order_executor import OrderExecutor
from core.position_manager import PositionManager
from core.price_feed import PriceFeed
from core.risk_manager import RiskManager
from dashboard.server import run_dashboard
from db.database import init_db, upsert_daily_stats, get_daily_stats, is_circuit_breaker_triggered
from log_config.logger import setup_logger
from strategies.arbitrage import ArbitrageStrategy
from strategies.scalping import ScalpingStrategy

SCAN_INTERVAL = 30


async def strategy_loop(event_bus: EventBus, scalping: ScalpingStrategy,
                        arbitrage: ArbitrageStrategy, executor: OrderExecutor) -> None:
    ob_queue: asyncio.Queue = asyncio.Queue()
    event_bus.subscribe(OrderbookEvent, ob_queue)
    while True:
        event = await ob_queue.get()
        for strategy in (scalping, arbitrage):
            signals = await strategy.on_orderbook_update(event)
            if signals:
                for signal in signals:
                    await executor.execute_signal(signal)


async def scanner_loop(clob_client, scanner: MarketScanner, price_feed: PriceFeed,
                       arbitrage: ArbitrageStrategy, volume_threshold: float) -> None:
    while True:
        markets = await scanner.scan(clob_client, volume_threshold)
        token_ids = []
        market_map = {}
        for m in markets:
            token_ids += [m.yes_token_id, m.no_token_id]
            market_map[m.condition_id] = {
                "yes_token_id": m.yes_token_id,
                "no_token_id": m.no_token_id,
                "event_id": m.event_id,
            }
        arbitrage._market_map = market_map
        arbitrage._rebuild_token_index()
        await price_feed.update_subscriptions(token_ids)
        await asyncio.sleep(SCAN_INTERVAL)


async def exit_monitor_loop(position_manager: PositionManager, executor: OrderExecutor,
                            config) -> None:
    open_times: dict[int, float] = {}
    while True:
        await asyncio.sleep(1)
        positions = await position_manager.get_positions()
        now = asyncio.get_event_loop().time()
        active_ids = set()
        for pos in positions:
            tid = pos["trade_id"]
            active_ids.add(tid)
            open_times.setdefault(tid, now)
            elapsed = now - open_times[tid]
            if pos["strategy"] == "scalping" and elapsed >= config.max_hold_seconds:
                logger = logging.getLogger("system")
                logger.info(f"Time stop for trade {tid} after {elapsed:.0f}s")
                await executor.exit_position(tid, pos)
                open_times.pop(tid, None)
        open_times = {k: v for k, v in open_times.items() if k in active_ids}


async def risk_monitor_loop(position_manager: PositionManager, risk_manager: RiskManager,
                            db, config) -> None:
    today = date.today().isoformat()
    stats = await get_daily_stats(db, today)
    day_start_bankroll = stats["start_bankroll"] if stats else config.starting_bankroll
    peak_bankroll = stats["peak_bankroll"] if stats else config.starting_bankroll

    while True:
        bankroll = position_manager.bankroll
        peak_bankroll = max(peak_bankroll, bankroll)
        await upsert_daily_stats(db, today, day_start_bankroll, peak_bankroll)
        await risk_manager.check_daily_loss(bankroll, day_start_bankroll)
        await risk_manager.check_drawdown(bankroll, peak_bankroll)
        await asyncio.sleep(10)


async def main() -> None:
    config = load_config()

    setup_logger("scalping", "scalping.log")
    setup_logger("arbitrage", "arbitrage.log")
    setup_logger("system", "system.log")
    sys_logger = logging.getLogger("system")

    db = await init_db("polymarket.db")

    today = date.today().isoformat()
    stats = await get_daily_stats(db, today)
    if not stats:
        await upsert_daily_stats(db, today, config.starting_bankroll, config.starting_bankroll)

    if await is_circuit_breaker_triggered(db):
        sys_logger.warning("Circuit breaker is active. Reset it manually before starting.")
        await db.close()
        return

    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import ApiCreds

    clob_client = ClobClient(
        host="https://clob.polymarket.com",
        key=config.wallet_private_key,
        chain_id=config.chain_id,
        creds=ApiCreds(config.api_key, config.api_secret, config.api_passphrase),
    )

    event_bus = EventBus()
    position_manager = PositionManager(starting_bankroll=config.starting_bankroll, db=db)
    risk_manager = RiskManager(config=config, db=db)
    scalping = ScalpingStrategy(config=config)
    arbitrage = ArbitrageStrategy(config=config, market_map={})
    order_executor = OrderExecutor(clob_client, position_manager, risk_manager, db, config)
    scanner = MarketScanner()
    price_feed = PriceFeed(event_bus=event_bus)

    positions_ref: list[dict] = []

    async def sync_positions_loop() -> None:
        while True:
            positions_ref.clear()
            positions_ref.extend(await position_manager.get_positions())
            await asyncio.sleep(2)

    dashboard_thread = threading.Thread(
        target=run_dashboard, args=("polymarket.db", config, positions_ref), daemon=True
    )
    dashboard_thread.start()
    sys_logger.info(f"Dashboard running on port {config.dashboard_port}")

    markets = await scanner.scan(clob_client, config.volume_threshold_usd)
    markets = sorted(markets, key=lambda m: m.volume, reverse=True)[:50]
    token_ids = [t for m in markets for t in (m.yes_token_id, m.no_token_id)]
    sys_logger.info(f"Found {len(markets)} markets, {len(token_ids)} token feeds")

    await asyncio.gather(
        price_feed.start(token_ids),
        strategy_loop(event_bus, scalping, arbitrage, order_executor),
        scanner_loop(clob_client, scanner, price_feed, arbitrage, config.volume_threshold_usd),
        exit_monitor_loop(position_manager, order_executor, config),
        risk_monitor_loop(position_manager, risk_manager, db, config),
        sync_positions_loop(),
    )


if __name__ == "__main__":
    asyncio.run(main())
