import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from db.database import init_db, insert_trade


@pytest_asyncio.fixture
async def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    db = await init_db(path)
    await db.close()
    return path


@pytest.fixture
def positions():
    return []


@pytest.fixture
def app(db_path, config, positions):
    from dashboard.server import create_app
    return create_app(db_path, config, positions_ref=positions)


@pytest.mark.asyncio
async def test_performance_endpoint_returns_summary(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/performance")
    assert response.status_code == 200
    data = response.json()
    assert "total_pnl" in data
    assert "scalping" in data
    assert "arbitrage" in data


@pytest.mark.asyncio
async def test_trades_endpoint_returns_list(app, db_path):
    db = await init_db(db_path)
    await insert_trade(db, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    await db.close()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/trades?limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_trades_endpoint_filters_by_strategy(app, db_path):
    db = await init_db(db_path)
    await insert_trade(db, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    await insert_trade(db, 'arbitrage', 'm2', 'tok2', 'BUY', 5.0, 0.47)
    await db.close()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/trades?strategy=scalping&limit=10")
    trades = response.json()
    assert all(t["strategy"] == "scalping" for t in trades)


@pytest.mark.asyncio
async def test_positions_endpoint_returns_list(app, positions):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/positions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_positions_endpoint_returns_live_data(app, positions):
    positions.append({"trade_id": 1, "strategy": "scalping", "market_id": "m1",
                      "token_id": "tok1", "side": "BUY", "size": 10.0,
                      "entry_price": 0.50, "current_price": 0.52})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/positions")
    data = response.json()
    assert len(data) == 1
    assert data[0]["trade_id"] == 1
