import os
from dataclasses import dataclass, field
from dotenv import load_dotenv


def _parse_int(value: str, env_var_name: str) -> int:
    """Parse a string to int with helpful error message."""
    try:
        return int(value)
    except ValueError:
        raise ValueError(
            f"Invalid value for {env_var_name}: '{value}' — expected int"
        )


def _parse_float(value: str, env_var_name: str) -> float:
    """Parse a string to float with helpful error message."""
    try:
        return float(value)
    except ValueError:
        raise ValueError(
            f"Invalid value for {env_var_name}: '{value}' — expected float"
        )


@dataclass(frozen=True)
class Config:
    api_key: str
    api_secret: str = field(repr=False)
    api_passphrase: str
    wallet_private_key: str = field(repr=False)
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
    """Load and validate configuration from environment variables.

    Raises:
        ValueError: If required env vars are missing or invalid values are provided.
    """
    load_dotenv()

    # Check all required env vars at once
    required_vars = {
        "POLYMARKET_API_KEY": os.environ.get("POLYMARKET_API_KEY"),
        "POLYMARKET_API_SECRET": os.environ.get("POLYMARKET_API_SECRET"),
        "POLYMARKET_API_PASSPHRASE": os.environ.get("POLYMARKET_API_PASSPHRASE"),
        "POLYMARKET_WALLET_PRIVATE_KEY": os.environ.get("POLYMARKET_WALLET_PRIVATE_KEY"),
    }

    missing_vars = [name for name, value in required_vars.items() if value is None]
    if missing_vars:
        raise ValueError(f"Missing required env vars: {', '.join(missing_vars)}")

    # Parse numeric values with validation
    chain_id = _parse_int(
        os.environ.get("POLYMARKET_CHAIN_ID", "137"),
        "POLYMARKET_CHAIN_ID"
    )
    volume_threshold_usd = _parse_float(
        os.environ.get("VOLUME_THRESHOLD_USD", "10000"),
        "VOLUME_THRESHOLD_USD"
    )
    dashboard_port = _parse_int(
        os.environ.get("DASHBOARD_PORT", "8080"),
        "DASHBOARD_PORT"
    )
    min_spread_pct = _parse_float(
        os.environ.get("MIN_SPREAD_PCT", "2.0"),
        "MIN_SPREAD_PCT"
    )
    min_arb_edge_pct = _parse_float(
        os.environ.get("MIN_ARB_EDGE_PCT", "1.5"),
        "MIN_ARB_EDGE_PCT"
    )
    max_hold_seconds = _parse_int(
        os.environ.get("MAX_HOLD_SECONDS", "60"),
        "MAX_HOLD_SECONDS"
    )
    kelly_fraction = _parse_float(
        os.environ.get("KELLY_FRACTION", "0.25"),
        "KELLY_FRACTION"
    )
    max_positions = _parse_int(
        os.environ.get("MAX_POSITIONS", "5"),
        "MAX_POSITIONS"
    )
    daily_loss_limit_pct = _parse_float(
        os.environ.get("DAILY_LOSS_LIMIT_PCT", "15"),
        "DAILY_LOSS_LIMIT_PCT"
    )
    drawdown_limit_pct = _parse_float(
        os.environ.get("DRAWDOWN_LIMIT_PCT", "30"),
        "DRAWDOWN_LIMIT_PCT"
    )
    starting_bankroll = _parse_float(
        os.environ.get("STARTING_BANKROLL", "300.0"),
        "STARTING_BANKROLL"
    )

    # Validate numeric param ranges
    if not (0 < kelly_fraction < 1):
        raise ValueError(
            f"Invalid value for KELLY_FRACTION: {kelly_fraction} — "
            "must be 0 < kelly_fraction < 1"
        )

    if max_positions < 1:
        raise ValueError(
            f"Invalid value for MAX_POSITIONS: {max_positions} — "
            "must be >= 1"
        )

    if not (0 < daily_loss_limit_pct <= 100):
        raise ValueError(
            f"Invalid value for DAILY_LOSS_LIMIT_PCT: {daily_loss_limit_pct} — "
            "must be 0 < daily_loss_limit_pct <= 100"
        )

    if not (0 < drawdown_limit_pct <= 100):
        raise ValueError(
            f"Invalid value for DRAWDOWN_LIMIT_PCT: {drawdown_limit_pct} — "
            "must be 0 < drawdown_limit_pct <= 100"
        )

    return Config(
        api_key=required_vars["POLYMARKET_API_KEY"],
        api_secret=required_vars["POLYMARKET_API_SECRET"],
        api_passphrase=required_vars["POLYMARKET_API_PASSPHRASE"],
        wallet_private_key=required_vars["POLYMARKET_WALLET_PRIVATE_KEY"],
        chain_id=chain_id,
        volume_threshold_usd=volume_threshold_usd,
        dashboard_port=dashboard_port,
        min_spread_pct=min_spread_pct,
        min_arb_edge_pct=min_arb_edge_pct,
        max_hold_seconds=max_hold_seconds,
        kelly_fraction=kelly_fraction,
        max_positions=max_positions,
        daily_loss_limit_pct=daily_loss_limit_pct,
        drawdown_limit_pct=drawdown_limit_pct,
        starting_bankroll=starting_bankroll,
    )
