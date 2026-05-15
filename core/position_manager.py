import aiosqlite
from db.database import update_trade


class PositionManager:
    def __init__(self, starting_bankroll: float, db: aiosqlite.Connection):
        self.bankroll = starting_bankroll
        self._db = db
        self._positions: dict[int, dict] = {}

    async def open_position(self, trade_id: int, strategy: str, market_id: str,
                            token_id: str, side: str, size: float, entry_price: float) -> None:
        self._positions[trade_id] = {
            "trade_id": trade_id,
            "strategy": strategy,
            "market_id": market_id,
            "token_id": token_id,
            "side": side,
            "size": size,
            "entry_price": entry_price,
            "current_price": entry_price,
        }

    async def close_position(self, trade_id: int, exit_price: float) -> float:
        pos = self._positions.pop(trade_id)
        pnl = (exit_price - pos["entry_price"]) * pos["size"]
        if pos["side"] == "SELL":
            pnl = -pnl
        self.bankroll += pnl
        await update_trade(
            self._db, trade_id,
            status="closed",
            exit_price=exit_price,
            realized_pnl=pnl,
        )
        return pnl

    async def get_positions(self) -> list[dict]:
        return list(self._positions.values())

    async def count_open(self) -> int:
        return len(self._positions)

    async def update_price(self, token_id: str, price: float) -> None:
        for pos in self._positions.values():
            if pos["token_id"] == token_id:
                pos["current_price"] = price
