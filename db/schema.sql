CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy TEXT NOT NULL CHECK (strategy IN ('scalping', 'arbitrage')),
    market_id TEXT NOT NULL,
    token_id TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    size REAL NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL,
    order_id TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'filled', 'cancelled', 'closed')),
    realized_pnl REAL,
    opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TEXT
);

CREATE TABLE IF NOT EXISTS circuit_breaker (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    triggered INTEGER NOT NULL DEFAULT 0,
    triggered_at TEXT,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS daily_stats (
    date TEXT PRIMARY KEY,
    start_bankroll REAL NOT NULL,
    peak_bankroll REAL NOT NULL,
    scalping_pnl REAL NOT NULL DEFAULT 0.0,
    arbitrage_pnl REAL NOT NULL DEFAULT 0.0
);
