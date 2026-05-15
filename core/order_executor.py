import asyncio
import logging
import aiosqlite
from config import Config
from core.event_bus import SignalEvent
from core.kelly_sizer import compute_bet_size
from core.position_manager import PositionManager
from core.risk_manager import RiskManager
from db.database import insert_trade

logger = logging.getLogger("system")


class OrderExecutor:
    def __init__(self, clob_client, position_manager: PositionManager,
                 risk_manager: RiskManager, db: aiosqlite.Connection, config: Config):
        self._clob = clob_client
        self._pm = position_manager
        self._rm = risk_manager
        self._db = db
        self._config = config

    async def execute_signal(self, signal: SignalEvent) -> str | None:
        if not await self._rm.can_place_order(signal.strategy, 0.0, self._pm.bankroll):
            return None

        size = compute_bet_size(
            estimated_prob=signal.estimated_prob,
            implied_prob=signal.implied_prob,
            bankroll=self._pm.bankroll,
            kelly_fraction=self._config.kelly_fraction,
        )
        if size == 0.0:
            return None

        price = signal.implied_prob if signal.side == "BUY" else 1.0 - signal.implied_prob

        try:
            from py_clob_client.clob_types import OrderArgs, OrderType
            order_args = OrderArgs(token_id=signal.token_id, price=price, size=size, side=signal.side)
            signed = await asyncio.to_thread(self._clob.create_order, order_args)
            resp = await asyncio.to_thread(self._clob.post_order, signed, OrderType.GTC)
            order_id = resp.get("orderID")
        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            return None

        trade_id = await insert_trade(
            self._db,
            strategy=signal.strategy,
            market_id=signal.market_id,
            token_id=signal.token_id,
            side=signal.side,
            size=size,
            entry_price=price,
            order_id=order_id,
        )
        await self._pm.open_position(
            trade_id=trade_id, strategy=signal.strategy, market_id=signal.market_id,
            token_id=signal.token_id, side=signal.side, size=size, entry_price=price,
        )
        logger.info(f"Order placed: {order_id} | {signal.strategy} | {signal.side} {size} @ {price}")
        return order_id

    async def cancel_order(self, order_id: str) -> bool:
        try:
            await asyncio.to_thread(self._clob.cancel, order_id=order_id)
            return True
        except Exception as e:
            logger.error(f"Cancel failed for {order_id}: {e}")
            return False

    async def exit_position(self, trade_id: int, pos: dict) -> None:
        exit_price = pos.get("current_price", pos["entry_price"])
        try:
            from py_clob_client.clob_types import OrderArgs, OrderType
            exit_side = "BUY" if pos["side"] == "SELL" else "SELL"
            exit_price_limit = (exit_price + 0.01) if exit_side == "BUY" else max(exit_price - 0.01, 0.01)
            order_args = OrderArgs(
                token_id=pos["token_id"],
                price=exit_price_limit,
                size=pos["size"],
                side=exit_side,
            )
            signed = await asyncio.to_thread(self._clob.create_order, order_args)
            await asyncio.to_thread(self._clob.post_order, signed, OrderType.GTC)
        except Exception as e:
            logger.error(f"Exit order failed for trade {trade_id}: {e}")

        pnl = await self._pm.close_position(trade_id, exit_price)
        logger.info(f"Closed trade {trade_id}: PnL={pnl:+.4f}")
