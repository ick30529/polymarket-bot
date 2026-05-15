import aiosqlite
from config import Config
from db.database import get_open_trades, is_circuit_breaker_triggered, trigger_circuit_breaker


class RiskManager:
    def __init__(self, config: Config, db: aiosqlite.Connection):
        self._config = config
        self._db = db
        self._paused = False

    async def can_place_order(self, strategy: str, size: float, bankroll: float) -> bool:
        if self._paused:
            return False
        if await is_circuit_breaker_triggered(self._db):
            return False
        open_trades = await get_open_trades(self._db)
        if len(open_trades) >= self._config.max_positions:
            return False
        return True

    async def check_daily_loss(self, current_bankroll: float, day_start_bankroll: float) -> bool:
        loss_pct = (day_start_bankroll - current_bankroll) / day_start_bankroll * 100
        if loss_pct >= self._config.daily_loss_limit_pct:
            self._paused = True
            return True
        return False

    async def check_drawdown(self, current_bankroll: float, peak_bankroll: float) -> bool:
        drawdown_pct = (peak_bankroll - current_bankroll) / peak_bankroll * 100
        if drawdown_pct >= self._config.drawdown_limit_pct:
            await trigger_circuit_breaker(self._db, "drawdown circuit breaker triggered")
            return True
        return False

    async def is_halted(self) -> bool:
        return self._paused or await is_circuit_breaker_triggered(self._db)

    def unpause(self) -> None:
        self._paused = False
