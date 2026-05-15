import pytest
from core.position_manager import PositionManager

@pytest.mark.asyncio
async def test_open_position_tracked(db, config):
    pm = PositionManager(starting_bankroll=300.0, db=db)
    await pm.open_position(1, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    positions = await pm.get_positions()
    assert len(positions) == 1
    assert positions[0]['trade_id'] == 1

@pytest.mark.asyncio
async def test_close_position_calculates_pnl(db, config):
    from db.database import insert_trade
    pm = PositionManager(starting_bankroll=300.0, db=db)
    tid = await insert_trade(db, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    await pm.open_position(tid, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    pnl = await pm.close_position(trade_id=tid, exit_price=0.55)
    assert pnl == pytest.approx(0.50, rel=1e-3)
    positions = await pm.get_positions()
    assert len(positions) == 0

@pytest.mark.asyncio
async def test_bankroll_updates_on_close(db, config):
    from db.database import insert_trade
    pm = PositionManager(starting_bankroll=300.0, db=db)
    tid = await insert_trade(db, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    await pm.open_position(tid, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    await pm.close_position(trade_id=tid, exit_price=0.55)
    assert pm.bankroll == pytest.approx(300.50, rel=1e-3)

@pytest.mark.asyncio
async def test_count_open_positions(db, config):
    pm = PositionManager(starting_bankroll=300.0, db=db)
    await pm.open_position(1, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    await pm.open_position(2, 'arbitrage', 'm2', 'tok2', 'BUY', 5.0, 0.47)
    assert await pm.count_open() == 2
