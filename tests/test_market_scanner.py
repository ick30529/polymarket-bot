import pytest
from unittest.mock import MagicMock
from core.market_scanner import MarketScanner

@pytest.fixture
def mock_clob():
    client = MagicMock()
    client.get_markets = MagicMock(return_value={
        "data": [
            {"condition_id": "cond1", "tokens": [{"token_id": "yes1", "outcome": "Yes"}, {"token_id": "no1", "outcome": "No"}], "volume": "50000.00", "active": True, "event_id": "evt1"},
            {"condition_id": "cond2", "tokens": [{"token_id": "yes2", "outcome": "Yes"}, {"token_id": "no2", "outcome": "No"}], "volume": "5000.00", "active": True, "event_id": "evt2"},
            {"condition_id": "cond3", "tokens": [{"token_id": "yes3", "outcome": "Yes"}, {"token_id": "no3", "outcome": "No"}], "volume": "80000.00", "active": False, "event_id": "evt3"},
        ]
    })
    return client

@pytest.mark.asyncio
async def test_filters_by_volume_threshold(mock_clob):
    scanner = MarketScanner()
    markets = await scanner.scan(mock_clob, volume_threshold_usd=10000.0)
    assert len(markets) == 1
    assert markets[0].condition_id == "cond1"

@pytest.mark.asyncio
async def test_filters_inactive_markets(mock_clob):
    scanner = MarketScanner()
    markets = await scanner.scan(mock_clob, volume_threshold_usd=10000.0)
    assert all(m.condition_id != "cond3" for m in markets)

@pytest.mark.asyncio
async def test_returns_correct_token_ids(mock_clob):
    scanner = MarketScanner()
    markets = await scanner.scan(mock_clob, volume_threshold_usd=10000.0)
    assert markets[0].yes_token_id == "yes1"
    assert markets[0].no_token_id == "no1"
