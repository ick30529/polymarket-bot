import pytest
from unittest.mock import AsyncMock, MagicMock
from core.order_executor import OrderExecutor
from core.event_bus import SignalEvent
from db.database import get_open_trades

@pytest.fixture
def mock_clob():
    client = MagicMock()
    client.create_order = MagicMock(return_value=MagicMock())
    client.post_order = MagicMock(return_value={"orderID": "order123", "status": "LIVE"})
    client.cancel = MagicMock(return_value={"canceled": [{"orderID": "order123"}]})
    return client

@pytest.fixture
def mock_pm():
    pm = MagicMock()
    pm.bankroll = 300.0
    pm.open_position = AsyncMock()
    pm.close_position = AsyncMock(return_value=0.42)
    return pm

@pytest.fixture
def mock_rm():
    rm = MagicMock()
    rm.can_place_order = AsyncMock(return_value=True)
    rm.is_halted = AsyncMock(return_value=False)
    return rm

@pytest.mark.asyncio
async def test_execute_signal_places_order(db, config, mock_clob, mock_pm, mock_rm):
    executor = OrderExecutor(mock_clob, mock_pm, mock_rm, db, config)
    signal = SignalEvent(strategy='scalping', market_id='m1', token_id='tok1', side='BUY', estimated_prob=0.6, implied_prob=0.5, edge=0.1)
    order_id = await executor.execute_signal(signal)
    assert order_id == "order123"
    trades = await get_open_trades(db)
    assert len(trades) == 1

@pytest.mark.asyncio
async def test_execute_blocked_by_risk_manager(db, config, mock_clob, mock_pm, mock_rm):
    mock_rm.can_place_order = AsyncMock(return_value=False)
    executor = OrderExecutor(mock_clob, mock_pm, mock_rm, db, config)
    signal = SignalEvent('scalping', 'm1', 'tok1', 'BUY', 0.6, 0.5, 0.1)
    order_id = await executor.execute_signal(signal)
    assert order_id is None
    trades = await get_open_trades(db)
    assert len(trades) == 0

@pytest.mark.asyncio
async def test_cancel_order(db, config, mock_clob, mock_pm, mock_rm):
    executor = OrderExecutor(mock_clob, mock_pm, mock_rm, db, config)
    result = await executor.cancel_order("order123")
    assert result is True
    mock_clob.cancel.assert_called_once()

@pytest.mark.asyncio
async def test_exit_position_closes_trade(db, config, mock_clob, mock_pm, mock_rm):
    executor = OrderExecutor(mock_clob, mock_pm, mock_rm, db, config)
    pos = {"trade_id": 1, "strategy": "scalping", "market_id": "m1", "token_id": "tok1", "side": "BUY", "size": 10.0, "entry_price": 0.50, "current_price": 0.55}
    await executor.exit_position(trade_id=1, pos=pos)
    mock_pm.close_position.assert_called_once_with(1, 0.55)
