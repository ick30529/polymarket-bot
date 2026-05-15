import pytest
from db.database import (
    insert_trade, update_trade, get_open_trades, get_trade_history,
    is_circuit_breaker_triggered, trigger_circuit_breaker, reset_circuit_breaker,
    get_performance_summary,
)

@pytest.mark.asyncio
async def test_insert_and_retrieve_trade(db):
    tid = await insert_trade(db, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    assert tid == 1
    trades = await get_open_trades(db)
    assert len(trades) == 1
    assert trades[0]['market_id'] == 'm1'

@pytest.mark.asyncio
async def test_update_trade_status(db):
    tid = await insert_trade(db, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    await update_trade(db, tid, status='closed', exit_price=0.55, realized_pnl=0.50)
    trades = await get_open_trades(db)
    assert len(trades) == 0

@pytest.mark.asyncio
async def test_filter_open_trades_by_strategy(db):
    await insert_trade(db, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    await insert_trade(db, 'arbitrage', 'm2', 'tok2', 'BUY', 5.0, 0.48)
    scalping_trades = await get_open_trades(db, strategy='scalping')
    assert len(scalping_trades) == 1
    assert scalping_trades[0]['strategy'] == 'scalping'

@pytest.mark.asyncio
async def test_circuit_breaker_default_not_triggered(db):
    assert not await is_circuit_breaker_triggered(db)

@pytest.mark.asyncio
async def test_trigger_and_reset_circuit_breaker(db):
    await trigger_circuit_breaker(db, "drawdown exceeded")
    assert await is_circuit_breaker_triggered(db)
    await reset_circuit_breaker(db)
    assert not await is_circuit_breaker_triggered(db)

@pytest.mark.asyncio
async def test_performance_summary_empty(db):
    summary = await get_performance_summary(db)
    assert summary['scalping']['pnl'] == 0.0
    assert summary['arbitrage']['pnl'] == 0.0
