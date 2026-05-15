import aiosqlite
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
_SCHEMA = SCHEMA_PATH.read_text()

ALLOWED_TRADE_FIELDS = {"status", "exit_price", "realized_pnl", "closed_at", "order_id"}


async def init_db(db_path: str) -> aiosqlite.Connection:
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.executescript(_SCHEMA)
    await db.commit()
    return db


async def insert_trade(db: aiosqlite.Connection, strategy: str, market_id: str,
                       token_id: str, side: str, size: float,
                       entry_price: float, order_id: str | None = None) -> int:
    cursor = await db.execute(
        """INSERT INTO trades (strategy, market_id, token_id, side, size, entry_price, order_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (strategy, market_id, token_id, side, size, entry_price, order_id),
    )
    await db.commit()
    return cursor.lastrowid


async def update_trade(db: aiosqlite.Connection, trade_id: int, **kwargs) -> None:
    if not kwargs:
        return
    bad = set(kwargs) - ALLOWED_TRADE_FIELDS
    if bad:
        raise ValueError(f"Unknown/disallowed trade fields: {bad}")
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [trade_id]
    await db.execute(f"UPDATE trades SET {fields} WHERE id = ?", values)
    await db.commit()


async def get_open_trades(db: aiosqlite.Connection,
                          strategy: str | None = None) -> list[dict]:
    if strategy:
        cursor = await db.execute(
            "SELECT * FROM trades WHERE status = 'open' AND strategy = ?", (strategy,)
        )
    else:
        cursor = await db.execute("SELECT * FROM trades WHERE status = 'open'")
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_trade_history(db: aiosqlite.Connection,
                            strategy: str | None = None, limit: int = 50) -> list[dict]:
    if strategy:
        cursor = await db.execute(
            "SELECT * FROM trades WHERE strategy = ? ORDER BY opened_at DESC LIMIT ?",
            (strategy, limit),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM trades ORDER BY opened_at DESC LIMIT ?", (limit,)
        )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def is_circuit_breaker_triggered(db: aiosqlite.Connection) -> bool:
    cursor = await db.execute(
        "SELECT triggered FROM circuit_breaker WHERE id = 1"
    )
    row = await cursor.fetchone()
    return bool(row and row["triggered"])


async def trigger_circuit_breaker(db: aiosqlite.Connection, reason: str) -> None:
    await db.execute(
        """INSERT INTO circuit_breaker (id, triggered, triggered_at, reason)
           VALUES (1, 1, CURRENT_TIMESTAMP, ?)
           ON CONFLICT(id) DO UPDATE SET triggered=1, triggered_at=CURRENT_TIMESTAMP, reason=?""",
        (reason, reason),
    )
    await db.commit()


async def reset_circuit_breaker(db: aiosqlite.Connection) -> None:
    await db.execute(
        "UPDATE circuit_breaker SET triggered=0, triggered_at=NULL, reason=NULL WHERE id=1"
    )
    await db.commit()


async def upsert_daily_stats(db: aiosqlite.Connection, date_str: str,
                             start_bankroll: float, peak_bankroll: float,
                             scalping_pnl: float = 0.0,
                             arbitrage_pnl: float = 0.0) -> None:
    await db.execute(
        """INSERT INTO daily_stats (date, start_bankroll, peak_bankroll, scalping_pnl, arbitrage_pnl)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(date) DO UPDATE SET
               peak_bankroll=MAX(peak_bankroll, excluded.peak_bankroll),
               scalping_pnl=excluded.scalping_pnl,
               arbitrage_pnl=excluded.arbitrage_pnl""",
        (date_str, start_bankroll, peak_bankroll, scalping_pnl, arbitrage_pnl),
    )
    await db.commit()


async def get_daily_stats(db: aiosqlite.Connection,
                          date_str: str) -> dict | None:
    cursor = await db.execute(
        "SELECT * FROM daily_stats WHERE date = ?", (date_str,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_performance_summary(db: aiosqlite.Connection) -> dict:
    cursor = await db.execute(
        """SELECT
            strategy,
            SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
            COUNT(*) as total,
            COALESCE(SUM(realized_pnl), 0) as pnl
           FROM trades WHERE status = 'closed'
           GROUP BY strategy"""
    )
    rows = await cursor.fetchall()
    result = {"scalping": {"pnl": 0.0, "wins": 0, "total": 0},
              "arbitrage": {"pnl": 0.0, "wins": 0, "total": 0}}
    for row in rows:
        result[row["strategy"]] = dict(row)
    return result
