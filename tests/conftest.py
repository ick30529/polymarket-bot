import pytest
import pytest_asyncio
from config import Config
from db.database import init_db

@pytest.fixture
def config() -> Config:
    return Config(
        api_key="test_key",
        api_secret="test_secret",
        api_passphrase="test_passphrase",
        wallet_private_key="0x" + "a" * 64,
        chain_id=137,
        volume_threshold_usd=10000.0,
        dashboard_port=8080,
        min_spread_pct=2.0,
        min_arb_edge_pct=1.5,
        max_hold_seconds=60,
        kelly_fraction=0.25,
        max_positions=5,
        daily_loss_limit_pct=15.0,
        drawdown_limit_pct=30.0,
        starting_bankroll=300.0,
    )

@pytest_asyncio.fixture
async def db():
    conn = await init_db(":memory:")
    yield conn
    await conn.close()
