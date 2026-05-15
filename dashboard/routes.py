import aiosqlite
from fastapi import APIRouter, Query
from config import Config
from db.database import get_trade_history, get_performance_summary


def create_router(db: aiosqlite.Connection, config: Config,
                  positions_ref: list[dict]) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/performance")
    async def performance():
        summary = await get_performance_summary(db)
        scalping = summary.get("scalping", {"pnl": 0.0, "wins": 0, "total": 0})
        arbitrage = summary.get("arbitrage", {"pnl": 0.0, "wins": 0, "total": 0})
        total_pnl = scalping["pnl"] + arbitrage["pnl"]
        total_closed = scalping["total"] + arbitrage["total"]
        total_wins = scalping["wins"] + arbitrage["wins"]
        win_rate = (total_wins / total_closed * 100) if total_closed > 0 else 0.0
        return {
            "total_pnl": round(total_pnl, 4),
            "win_rate": round(win_rate, 2),
            "scalping": {"pnl": round(scalping["pnl"], 4), "wins": scalping["wins"], "total": scalping["total"]},
            "arbitrage": {"pnl": round(arbitrage["pnl"], 4), "wins": arbitrage["wins"], "total": arbitrage["total"]},
        }

    @router.get("/trades")
    async def trades(
        strategy: str | None = Query(None),
        limit: int = Query(50, ge=1, le=500),
    ):
        return await get_trade_history(db, strategy=strategy, limit=limit)

    @router.get("/positions")
    async def positions():
        return positions_ref

    return router
