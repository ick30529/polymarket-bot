import time
import pytest
from core.event_bus import OrderbookEvent
from strategies.arbitrage import ArbitrageStrategy

MARKET_MAP = {"m1": {"yes_token_id": "yes1", "no_token_id": "no1", "event_id": "evt1"}}

def yes_event(ask: float) -> OrderbookEvent:
    return OrderbookEvent("m1", "yes1", [(ask - 0.02, 100)], [(ask, 100)], time.time())

def no_event(ask: float) -> OrderbookEvent:
    return OrderbookEvent("m1", "no1", [(ask - 0.02, 100)], [(ask, 100)], time.time())

@pytest.mark.asyncio
async def test_arb_signal_when_both_asks_sum_below_one(config):
    arb = ArbitrageStrategy(config, MARKET_MAP)
    await arb.on_orderbook_update(yes_event(0.47))
    signals = await arb.on_orderbook_update(no_event(0.47))
    assert signals is not None
    assert len(signals) == 2
    sides = {s.token_id: s.side for s in signals}
    assert sides["yes1"] == "BUY"
    assert sides["no1"] == "BUY"

@pytest.mark.asyncio
async def test_no_signal_when_sum_above_threshold(config):
    arb = ArbitrageStrategy(config, MARKET_MAP)
    await arb.on_orderbook_update(yes_event(0.51))
    signals = await arb.on_orderbook_update(no_event(0.51))
    assert signals is None

@pytest.mark.asyncio
async def test_no_signal_on_first_leg_only(config):
    arb = ArbitrageStrategy(config, MARKET_MAP)
    signals = await arb.on_orderbook_update(yes_event(0.47))
    assert signals is None

@pytest.mark.asyncio
async def test_signal_edge_calculated_correctly(config):
    arb = ArbitrageStrategy(config, MARKET_MAP)
    await arb.on_orderbook_update(yes_event(0.47))
    signals = await arb.on_orderbook_update(no_event(0.47))
    assert signals is not None
    total_cost = sum(s.implied_prob for s in signals)
    assert total_cost == pytest.approx(0.94, rel=1e-3)
