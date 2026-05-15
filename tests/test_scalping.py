import time
import pytest
from core.event_bus import OrderbookEvent
from strategies.scalping import ScalpingStrategy

def make_event(bid: float, ask: float, token_id: str = "tok1") -> OrderbookEvent:
    return OrderbookEvent(market_id="m1", token_id=token_id, bids=[(bid, 100.0)], asks=[(ask, 100.0)], timestamp=time.time())

def rising_events(n: int = 12) -> list[OrderbookEvent]:
    return [make_event(0.42 + i*0.005 - 0.005, 0.42 + i*0.005 + 0.005) for i in range(n)]

def falling_events(n: int = 12) -> list[OrderbookEvent]:
    return [make_event(0.62 - i*0.005 - 0.005, 0.62 - i*0.005 + 0.005) for i in range(n)]

@pytest.mark.asyncio
async def test_no_signal_when_spread_too_tight(config):
    strategy = ScalpingStrategy(config)
    for e in rising_events():
        await strategy.on_orderbook_update(e)
    signal = await strategy.on_orderbook_update(make_event(0.498, 0.502))
    assert signal is None

@pytest.mark.asyncio
async def test_buy_signal_on_wide_spread_and_rising(config):
    strategy = ScalpingStrategy(config)
    for e in rising_events():
        await strategy.on_orderbook_update(e)
    signal = await strategy.on_orderbook_update(make_event(0.47, 0.53))
    assert signal is not None
    assert signal[0].side == "BUY"
    assert signal[0].strategy == "scalping"

@pytest.mark.asyncio
async def test_sell_signal_on_wide_spread_and_falling(config):
    strategy = ScalpingStrategy(config)
    for e in falling_events():
        await strategy.on_orderbook_update(e)
    signal = await strategy.on_orderbook_update(make_event(0.37, 0.43))
    assert signal is not None
    assert signal[0].side == "SELL"

@pytest.mark.asyncio
async def test_no_signal_with_flat_momentum(config):
    strategy = ScalpingStrategy(config)
    flat = make_event(0.47, 0.53)
    for _ in range(12):
        await strategy.on_orderbook_update(flat)
    signal = await strategy.on_orderbook_update(make_event(0.47, 0.53))
    assert signal is None
