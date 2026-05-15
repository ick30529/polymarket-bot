import pytest
from core.risk_manager import RiskManager
from db.database import insert_trade, trigger_circuit_breaker

@pytest.mark.asyncio
async def test_allows_order_when_under_limits(db, config):
    rm = RiskManager(config, db)
    assert await rm.can_place_order('scalping', 10.0, 300.0) is True

@pytest.mark.asyncio
async def test_blocks_when_max_positions_reached(db, config):
    rm = RiskManager(config, db)
    for i in range(5):
        await insert_trade(db, 'scalping', f'm{i}', f'tok{i}', 'BUY', 10.0, 0.50)
    assert await rm.can_place_order('scalping', 10.0, 300.0) is False

@pytest.mark.asyncio
async def test_blocks_when_circuit_breaker_triggered(db, config):
    await trigger_circuit_breaker(db, "test")
    rm = RiskManager(config, db)
    assert await rm.can_place_order('scalping', 10.0, 300.0) is False

@pytest.mark.asyncio
async def test_daily_loss_triggers_pause(db, config):
    rm = RiskManager(config, db)
    paused = await rm.check_daily_loss(current_bankroll=255.0, day_start_bankroll=300.0)
    assert paused is True

@pytest.mark.asyncio
async def test_daily_loss_no_pause_under_limit(db, config):
    rm = RiskManager(config, db)
    paused = await rm.check_daily_loss(current_bankroll=280.0, day_start_bankroll=300.0)
    assert paused is False

@pytest.mark.asyncio
async def test_drawdown_triggers_circuit_breaker(db, config):
    rm = RiskManager(config, db)
    triggered = await rm.check_drawdown(current_bankroll=210.0, peak_bankroll=300.0)
    assert triggered is True
    assert await rm.is_halted()

@pytest.mark.asyncio
async def test_drawdown_no_trigger_under_limit(db, config):
    rm = RiskManager(config, db)
    triggered = await rm.check_drawdown(current_bankroll=250.0, peak_bankroll=300.0)
    assert triggered is False
