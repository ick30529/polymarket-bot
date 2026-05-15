import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    api_key: str
    api_secret: str
    api_passphrase: str
    wallet_private_key: str
    chain_id: int
    volume_threshold_usd: float
    dashboard_port: int
    min_spread_pct: float
    min_arb_edge_pct: float
    max_hold_seconds: int
    kelly_fraction: float
    max_positions: int
    daily_loss_limit_pct: float
    drawdown_limit_pct: float
    starting_bankroll: float

def load_config() -> Config:
    return Config(
        api_key=os.environ["POLYMARKET_API_KEY"],
        api_secret=os.environ["POLYMARKET_API_SECRET"],
        api_passphrase=os.environ["POLYMARKET_API_PASSPHRASE"],
        wallet_private_key=os.environ["POLYMARKET_WALLET_PRIVATE_KEY"],
        chain_id=int(os.environ.get("POLYMARKET_CHAIN_ID", "137")),
        volume_threshold_usd=float(os.environ.get("VOLUME_THRESHOLD_USD", "10000")),
        dashboard_port=int(os.environ.get("DASHBOARD_PORT", "8080")),
        min_spread_pct=float(os.environ.get("MIN_SPREAD_PCT", "2.0")),
        min_arb_edge_pct=float(os.environ.get("MIN_ARB_EDGE_PCT", "1.5")),
        max_hold_seconds=int(os.environ.get("MAX_HOLD_SECONDS", "60")),
        kelly_fraction=float(os.environ.get("KELLY_FRACTION", "0.25")),
        max_positions=int(os.environ.get("MAX_POSITIONS", "5")),
        daily_loss_limit_pct=float(os.environ.get("DAILY_LOSS_LIMIT_PCT", "15")),
        drawdown_limit_pct=float(os.environ.get("DRAWDOWN_LIMIT_PCT", "30")),
        starting_bankroll=float(os.environ.get("STARTING_BANKROLL", "300.0")),
    )
