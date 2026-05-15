import pytest
from httpx import AsyncClient, ASGITransport
from db.database import insert_trade

@pytest.fixture
def app(db, config):
    from dashboard.server import create_app
    positions = []
    return create_app(db, config, positions_ref=positions)

@pytest.mark.asyncio
async def test_performance_endpoint_returns_summary(app, db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/performance")
    assert response.status_code == 200
    data = response.json()
    assert "total_pnl" in data
    assert "scalping" in data
    assert "arbitrage" in data

@pytest.mark.asyncio
async def test_trades_endpoint_returns_list(app, db):
    await insert_trade(db, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/trades?limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_trades_endpoint_filters_by_strategy(app, db):
    await insert_trade(db, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    await insert_trade(db, 'arbitrage', 'm2', 'tok2', 'BUY', 5.0, 0.47)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/trades?strategy=scalping&limit=10")
    trades = response.json()
    assert all(t["strategy"] == "scalping" for t in trades)

@pytest.mark.asyncio
async def test_positions_endpoint_returns_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/positions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
