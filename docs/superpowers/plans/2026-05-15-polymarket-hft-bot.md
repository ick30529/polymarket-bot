# Polymarket HFT Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a high-frequency scalping and arbitrage bot for Polymarket's CLOB that manages two isolated strategy workers, enforces Kelly-criterion position sizing and hard risk limits, and exposes a live web dashboard on port 8080.

**Architecture:** Single Python 3.11+ asyncio process: a `MarketScanner` and `PriceFeed` publish typed events onto a central `EventBus`; two strategy workers (`ScalpingStrategy`, `ArbitrageStrategy`) consume those events and emit `SignalEvent`s; `OrderExecutor` checks `RiskManager`, sizes via `KellySizer`, then submits to Polymarket CLOB via `py-clob-client`. A `FastAPI` dashboard runs in a background thread reading from SQLite.

**Tech Stack:** Python 3.11+, `py-clob-client`, `aiosqlite`, `fastapi`, `uvicorn`, `aiohttp`, `websockets`, `python-dotenv`, `pytest`, `pytest-asyncio`, `httpx`

---

## File Map

```
polymarket/
├── requirements.txt
├── .gitignore
├── .env.example
├── config.py
├── main.py
├── db/
│   ├── __init__.py
│   ├── schema.sql
│   └── database.py
├── core/
│   ├── __init__.py
│   ├── event_bus.py
│   ├── kelly_sizer.py
│   ├── risk_manager.py
│   ├── position_manager.py
│   ├── market_scanner.py
│   ├── price_feed.py
│   └── order_executor.py
├── strategies/
│   ├── __init__.py
│   ├── base_strategy.py
│   ├── scalping.py
│   └── arbitrage.py
├── logging/
│   ├── __init__.py
│   ├── logger.py
│   └── logs/             (created at runtime)
├── dashboard/
│   ├── __init__.py
│   ├── server.py
│   ├── routes.py
│   └── static/
│       ├── index.html
│       └── charts.js
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_kelly_sizer.py
│   ├── test_risk_manager.py
│   ├── test_position_manager.py
│   ├── test_market_scanner.py
│   ├── test_scalping.py
│   ├── test_arbitrage.py
│   └── test_routes.py
├── deploy.sh
└── polymarket-bot.service
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `config.py`
- Create: `db/__init__.py`, `core/__init__.py`, `strategies/__init__.py`, `logging/__init__.py`, `dashboard/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
py-clob-client>=0.17.0
python-dotenv>=1.0.0
fastapi>=0.109.0
uvicorn>=0.27.0
aiohttp>=3.9.0
websockets>=12.0
aiosqlite>=0.19.0
pytest>=7.4.0
pytest-asyncio>=0.23.0
httpx>=0.26.0
```

- [ ] **Step 2: Create .gitignore**

```
.env
*.db
logging/logs/
__pycache__/
*.pyc
.pytest_cache/
venv/
```

- [ ] **Step 3: Create .env.example**

```
POLYMARKET_API_KEY=
POLYMARKET_API_SECRET=
POLYMARKET_API_PASSPHRASE=
POLYMARKET_WALLET_PRIVATE_KEY=
POLYMARKET_CHAIN_ID=137
VOLUME_THRESHOLD_USD=10000
DASHBOARD_PORT=8080
MIN_SPREAD_PCT=2.0
MIN_ARB_EDGE_PCT=1.5
MAX_HOLD_SECONDS=60
KELLY_FRACTION=0.25
MAX_POSITIONS=5
DAILY_LOSS_LIMIT_PCT=15
DRAWDOWN_LIMIT_PCT=30
STARTING_BANKROLL=300.0
```

- [ ] **Step 4: Create config.py**

```python
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
```

- [ ] **Step 5: Create package __init__.py files**

Create empty `__init__.py` in: `db/`, `core/`, `strategies/`, `logging/`, `dashboard/`, `tests/`

```bash
touch db/__init__.py core/__init__.py strategies/__init__.py logging/__init__.py dashboard/__init__.py tests/__init__.py
```

- [ ] **Step 6: Install dependencies**

```bash
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

Expected: All packages install without error.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .gitignore .env.example config.py db/__init__.py core/__init__.py strategies/__init__.py logging/__init__.py dashboard/__init__.py tests/__init__.py
git commit -m "feat: project scaffold, config, and dependencies"
```

---

## Task 2: Database Layer

**Files:**
- Create: `db/schema.sql`
- Create: `db/database.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create db/schema.sql**

```sql
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
```

- [ ] **Step 2: Create db/database.py**

```python
import aiosqlite
from datetime import date
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def init_db(db_path: str) -> aiosqlite.Connection:
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    schema = SCHEMA_PATH.read_text()
    await db.executescript(schema)
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
```

- [ ] **Step 3: Create tests/conftest.py**

```python
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
```

- [ ] **Step 4: Write database tests**

Create `tests/test_database.py`:

```python
import pytest
from db.database import (
    insert_trade, update_trade, get_open_trades, get_trade_history,
    is_circuit_breaker_triggered, trigger_circuit_breaker, reset_circuit_breaker,
    get_performance_summary,
)

@pytest.mark.asyncio
async def test_insert_and_retrieve_trade(db):
    tid = await insert_trade(db, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    assert tid == 1
    trades = await get_open_trades(db)
    assert len(trades) == 1
    assert trades[0]['market_id'] == 'm1'

@pytest.mark.asyncio
async def test_update_trade_status(db):
    tid = await insert_trade(db, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    await update_trade(db, tid, status='closed', exit_price=0.55, realized_pnl=0.50)
    trades = await get_open_trades(db)
    assert len(trades) == 0

@pytest.mark.asyncio
async def test_filter_open_trades_by_strategy(db):
    await insert_trade(db, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    await insert_trade(db, 'arbitrage', 'm2', 'tok2', 'BUY', 5.0, 0.48)
    scalping_trades = await get_open_trades(db, strategy='scalping')
    assert len(scalping_trades) == 1
    assert scalping_trades[0]['strategy'] == 'scalping'

@pytest.mark.asyncio
async def test_circuit_breaker_default_not_triggered(db):
    assert not await is_circuit_breaker_triggered(db)

@pytest.mark.asyncio
async def test_trigger_and_reset_circuit_breaker(db):
    await trigger_circuit_breaker(db, "drawdown exceeded")
    assert await is_circuit_breaker_triggered(db)
    await reset_circuit_breaker(db)
    assert not await is_circuit_breaker_triggered(db)

@pytest.mark.asyncio
async def test_performance_summary_empty(db):
    summary = await get_performance_summary(db)
    assert summary['scalping']['pnl'] == 0.0
    assert summary['arbitrage']['pnl'] == 0.0
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_database.py -v
```

Expected: 6 tests pass.

- [ ] **Step 6: Commit**

```bash
git add db/ tests/conftest.py tests/test_database.py tests/__init__.py
git commit -m "feat: database schema and async SQLite layer"
```

---

## Task 3: Event Bus

**Files:**
- Create: `core/event_bus.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_event_bus.py`:

```python
import asyncio
import pytest
from core.event_bus import EventBus, OrderbookEvent, SignalEvent, FillEvent

@pytest.mark.asyncio
async def test_subscribers_receive_published_events():
    bus = EventBus()
    queue = asyncio.Queue()
    bus.subscribe(OrderbookEvent, queue)

    event = OrderbookEvent(
        market_id='m1', token_id='tok1',
        bids=[(0.48, 100.0)], asks=[(0.52, 100.0)],
        timestamp=1000.0
    )
    await bus.publish(event)
    received = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert received.market_id == 'm1'

@pytest.mark.asyncio
async def test_non_subscribers_do_not_receive():
    bus = EventBus()
    queue = asyncio.Queue()
    bus.subscribe(SignalEvent, queue)

    event = OrderbookEvent('m1', 'tok1', [], [], 1000.0)
    await bus.publish(event)
    assert queue.empty()

@pytest.mark.asyncio
async def test_multiple_subscribers_all_receive():
    bus = EventBus()
    q1, q2 = asyncio.Queue(), asyncio.Queue()
    bus.subscribe(OrderbookEvent, q1)
    bus.subscribe(OrderbookEvent, q2)

    await bus.publish(OrderbookEvent('m1', 'tok1', [], [], 1000.0))
    assert not q1.empty()
    assert not q2.empty()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_event_bus.py -v
```

Expected: ImportError — `core.event_bus` does not exist.

- [ ] **Step 3: Create core/event_bus.py**

```python
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OrderbookEvent:
    market_id: str
    token_id: str
    bids: list[tuple[float, float]]
    asks: list[tuple[float, float]]
    timestamp: float


@dataclass
class SignalEvent:
    strategy: str
    market_id: str
    token_id: str
    side: str
    estimated_prob: float
    implied_prob: float
    edge: float


@dataclass
class FillEvent:
    trade_id: int
    order_id: str
    strategy: str
    market_id: str
    token_id: str
    side: str
    size: float
    price: float
    timestamp: float


class EventBus:
    def __init__(self):
        self._subscribers: dict[type, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, event_type: type, queue: asyncio.Queue) -> None:
        self._subscribers[event_type].append(queue)

    async def publish(self, event: Any) -> None:
        for queue in self._subscribers[type(event)]:
            await queue.put(event)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_event_bus.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add core/event_bus.py tests/test_event_bus.py
git commit -m "feat: typed event bus with asyncio queues"
```

---

## Task 4: Kelly Sizer

**Files:**
- Create: `core/kelly_sizer.py`
- Create: `tests/test_kelly_sizer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_kelly_sizer.py
import pytest
from core.kelly_sizer import compute_bet_size

def test_zero_edge_returns_zero():
    assert compute_bet_size(0.5, 0.5, 300.0) == 0.0

def test_negative_edge_returns_zero():
    assert compute_bet_size(0.4, 0.5, 300.0) == 0.0

def test_positive_edge_computes_bet():
    # estimated_prob=0.6, implied_prob=0.5
    # net_odds = (1-0.5)/0.5 = 1.0
    # full_kelly = (0.6*1.0 - 0.4)/1.0 = 0.2
    # fractional = 0.2 * 0.25 = 0.05
    # bet = 300 * 0.05 = 15.0
    result = compute_bet_size(0.6, 0.5, 300.0)
    assert result == pytest.approx(15.0, rel=1e-3)

def test_clamps_to_min_bet():
    # Tiny edge → Kelly gives < $2, clamps to min
    result = compute_bet_size(0.501, 0.500, 300.0, min_bet=2.0)
    assert result == 2.0

def test_clamps_to_max_bet_pct():
    # Huge edge → capped at 10% of bankroll = $30
    result = compute_bet_size(0.95, 0.10, 300.0, max_bet_pct=0.10)
    assert result == pytest.approx(30.0, rel=1e-3)

def test_kelly_fraction_scales_bet():
    # Higher fraction → larger bet
    small = compute_bet_size(0.6, 0.5, 300.0, kelly_fraction=0.10)
    large = compute_bet_size(0.6, 0.5, 300.0, kelly_fraction=0.50)
    assert large > small

def test_returns_zero_when_full_kelly_non_positive():
    # edge > 0 but odds structure gives non-positive Kelly
    result = compute_bet_size(0.51, 0.99, 300.0)
    assert result == 0.0
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_kelly_sizer.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create core/kelly_sizer.py**

```python
def compute_bet_size(
    estimated_prob: float,
    implied_prob: float,
    bankroll: float,
    kelly_fraction: float = 0.25,
    min_bet: float = 2.0,
    max_bet_pct: float = 0.10,
) -> float:
    edge = estimated_prob - implied_prob
    if edge <= 0:
        return 0.0
    # Binary Kelly: f* = (p*b - q) / b where b = net odds
    net_odds = (1.0 - implied_prob) / implied_prob
    full_kelly = (estimated_prob * net_odds - (1.0 - estimated_prob)) / net_odds
    if full_kelly <= 0:
        return 0.0
    bet = bankroll * full_kelly * kelly_fraction
    max_bet = bankroll * max_bet_pct
    return max(min_bet, min(bet, max_bet))
```

- [ ] **Step 4: Run to verify passing**

```bash
pytest tests/test_kelly_sizer.py -v
```

Expected: 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add core/kelly_sizer.py tests/test_kelly_sizer.py
git commit -m "feat: fractional Kelly position sizer"
```

---

## Task 5: Risk Manager

**Files:**
- Create: `core/risk_manager.py`
- Create: `tests/test_risk_manager.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_risk_manager.py
import pytest
from core.risk_manager import RiskManager
from db.database import insert_trade, trigger_circuit_breaker

@pytest.mark.asyncio
async def test_allows_order_when_under_limits(db, config):
    rm = RiskManager(config, db)
    allowed = await rm.can_place_order('scalping', 10.0, 300.0)
    assert allowed is True

@pytest.mark.asyncio
async def test_blocks_when_max_positions_reached(db, config):
    rm = RiskManager(config, db)
    for i in range(5):
        await insert_trade(db, 'scalping', f'm{i}', f'tok{i}', 'BUY', 10.0, 0.50)
    allowed = await rm.can_place_order('scalping', 10.0, 300.0)
    assert allowed is False

@pytest.mark.asyncio
async def test_blocks_when_circuit_breaker_triggered(db, config):
    await trigger_circuit_breaker(db, "test")
    rm = RiskManager(config, db)
    allowed = await rm.can_place_order('scalping', 10.0, 300.0)
    assert allowed is False

@pytest.mark.asyncio
async def test_daily_loss_triggers_pause(db, config):
    rm = RiskManager(config, db)
    # 15% loss on $300 = $45 loss → bankroll = $255
    paused = await rm.check_daily_loss(current_bankroll=255.0, day_start_bankroll=300.0)
    assert paused is True

@pytest.mark.asyncio
async def test_daily_loss_no_pause_under_limit(db, config):
    rm = RiskManager(config, db)
    paused = await rm.check_daily_loss(current_bankroll=280.0, day_start_bankroll=300.0)
    assert paused is False

@pytest.mark.asyncio
async def test_drawdown_triggers_circuit_breaker(db, config):
    rm = RiskManager(config, db)
    # 30% drawdown from $300 peak = $210
    triggered = await rm.check_drawdown(current_bankroll=210.0, peak_bankroll=300.0)
    assert triggered is True
    assert await rm.is_halted()

@pytest.mark.asyncio
async def test_drawdown_no_trigger_under_limit(db, config):
    rm = RiskManager(config, db)
    triggered = await rm.check_drawdown(current_bankroll=250.0, peak_bankroll=300.0)
    assert triggered is False
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_risk_manager.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create core/risk_manager.py**

```python
import aiosqlite
from config import Config
from db.database import (
    get_open_trades, is_circuit_breaker_triggered, trigger_circuit_breaker
)


class RiskManager:
    def __init__(self, config: Config, db: aiosqlite.Connection):
        self._config = config
        self._db = db
        self._paused = False

    async def can_place_order(self, strategy: str, size: float,
                              bankroll: float) -> bool:
        if self._paused:
            return False
        if await is_circuit_breaker_triggered(self._db):
            return False
        open_trades = await get_open_trades(self._db)
        if len(open_trades) >= self._config.max_positions:
            return False
        if size > bankroll * (self._config.max_positions / 10):
            return False
        return True

    async def check_daily_loss(self, current_bankroll: float,
                               day_start_bankroll: float) -> bool:
        loss_pct = (day_start_bankroll - current_bankroll) / day_start_bankroll * 100
        if loss_pct >= self._config.daily_loss_limit_pct:
            self._paused = True
            return True
        return False

    async def check_drawdown(self, current_bankroll: float,
                             peak_bankroll: float) -> bool:
        drawdown_pct = (peak_bankroll - current_bankroll) / peak_bankroll * 100
        if drawdown_pct >= self._config.drawdown_limit_pct:
            await trigger_circuit_breaker(self._db, "drawdown circuit breaker triggered")
            return True
        return False

    async def is_halted(self) -> bool:
        return self._paused or await is_circuit_breaker_triggered(self._db)

    def unpause(self) -> None:
        self._paused = False
```

- [ ] **Step 4: Run to verify passing**

```bash
pytest tests/test_risk_manager.py -v
```

Expected: 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add core/risk_manager.py tests/test_risk_manager.py
git commit -m "feat: risk manager with position limits and circuit breaker"
```

---

## Task 6: Position Manager

**Files:**
- Create: `core/position_manager.py`
- Create: `tests/test_position_manager.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_position_manager.py
import pytest
from core.position_manager import PositionManager

@pytest.mark.asyncio
async def test_open_position_tracked(db, config):
    pm = PositionManager(starting_bankroll=300.0, db=db)
    await pm.open_position(
        trade_id=1, strategy='scalping', market_id='m1',
        token_id='tok1', side='BUY', size=10.0, entry_price=0.50
    )
    positions = await pm.get_positions()
    assert len(positions) == 1
    assert positions[0]['trade_id'] == 1

@pytest.mark.asyncio
async def test_close_position_calculates_pnl(db, config):
    pm = PositionManager(starting_bankroll=300.0, db=db)
    await pm.open_position(1, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    pnl = await pm.close_position(trade_id=1, exit_price=0.55)
    # PnL = (0.55 - 0.50) * 10.0 = 0.50
    assert pnl == pytest.approx(0.50, rel=1e-3)
    positions = await pm.get_positions()
    assert len(positions) == 0

@pytest.mark.asyncio
async def test_bankroll_updates_on_close(db, config):
    pm = PositionManager(starting_bankroll=300.0, db=db)
    await pm.open_position(1, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    await pm.close_position(trade_id=1, exit_price=0.55)
    assert pm.bankroll == pytest.approx(300.50, rel=1e-3)

@pytest.mark.asyncio
async def test_count_open_positions(db, config):
    pm = PositionManager(starting_bankroll=300.0, db=db)
    await pm.open_position(1, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    await pm.open_position(2, 'arbitrage', 'm2', 'tok2', 'BUY', 5.0, 0.47)
    assert await pm.count_open() == 2
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_position_manager.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create core/position_manager.py**

```python
import aiosqlite
from db.database import insert_trade, update_trade, get_open_trades


class PositionManager:
    def __init__(self, starting_bankroll: float, db: aiosqlite.Connection):
        self.bankroll = starting_bankroll
        self._db = db
        self._positions: dict[int, dict] = {}

    async def open_position(self, trade_id: int, strategy: str, market_id: str,
                            token_id: str, side: str, size: float,
                            entry_price: float) -> None:
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
            closed_at="CURRENT_TIMESTAMP",
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
```

- [ ] **Step 4: Run to verify passing**

```bash
pytest tests/test_position_manager.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add core/position_manager.py tests/test_position_manager.py
git commit -m "feat: position manager tracks open positions and bankroll"
```

---

## Task 7: Market Scanner

**Files:**
- Create: `core/market_scanner.py`
- Create: `tests/test_market_scanner.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_market_scanner.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from core.market_scanner import MarketScanner, Market

@pytest.fixture
def mock_clob():
    client = MagicMock()
    client.get_markets = MagicMock(return_value={
        "data": [
            {
                "condition_id": "cond1",
                "tokens": [
                    {"token_id": "yes1", "outcome": "Yes"},
                    {"token_id": "no1", "outcome": "No"},
                ],
                "volume": "50000.00",
                "active": True,
                "event_id": "evt1",
            },
            {
                "condition_id": "cond2",
                "tokens": [
                    {"token_id": "yes2", "outcome": "Yes"},
                    {"token_id": "no2", "outcome": "No"},
                ],
                "volume": "5000.00",  # below threshold
                "active": True,
                "event_id": "evt2",
            },
            {
                "condition_id": "cond3",
                "tokens": [
                    {"token_id": "yes3", "outcome": "Yes"},
                    {"token_id": "no3", "outcome": "No"},
                ],
                "volume": "80000.00",
                "active": False,  # inactive
                "event_id": "evt3",
            },
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
    condition_ids = [m.condition_id for m in markets]
    assert "cond3" not in condition_ids

@pytest.mark.asyncio
async def test_returns_correct_token_ids(mock_clob):
    scanner = MarketScanner()
    markets = await scanner.scan(mock_clob, volume_threshold_usd=10000.0)
    assert markets[0].token_yes_id == "yes1"
    assert markets[0].token_no_id == "no1"
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_market_scanner.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create core/market_scanner.py**

```python
from dataclasses import dataclass


@dataclass
class Market:
    condition_id: str
    event_id: str
    token_yes_id: str
    token_no_id: str
    volume: float


class MarketScanner:
    async def scan(self, clob_client, volume_threshold_usd: float) -> list[Market]:
        response = clob_client.get_markets()
        markets = []
        for item in response.get("data", []):
            if not item.get("active"):
                continue
            volume = float(item.get("volume", "0"))
            if volume < volume_threshold_usd:
                continue
            tokens = item.get("tokens", [])
            yes_token = next((t for t in tokens if t["outcome"] == "Yes"), None)
            no_token = next((t for t in tokens if t["outcome"] == "No"), None)
            if not yes_token or not no_token:
                continue
            markets.append(Market(
                condition_id=item["condition_id"],
                event_id=item.get("event_id", ""),
                token_yes_id=yes_token["token_id"],
                token_no_id=no_token["token_id"],
                volume=volume,
            ))
        return markets
```

- [ ] **Step 4: Run to verify passing**

```bash
pytest tests/test_market_scanner.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add core/market_scanner.py tests/test_market_scanner.py
git commit -m "feat: market scanner filters by volume and active status"
```

---

## Task 8: Price Feed

**Files:**
- Create: `core/price_feed.py`

No unit tests — WebSocket connectivity is tested manually. This task wires the WebSocket stream to the event bus.

- [ ] **Step 1: Create core/price_feed.py**

```python
import asyncio
import json
import logging
import websockets
from core.event_bus import EventBus, OrderbookEvent

WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
logger = logging.getLogger("system")


class PriceFeed:
    def __init__(self, event_bus: EventBus):
        self._bus = event_bus
        self._subscribed: set[str] = set()
        self._ws = None
        self._running = False

    async def start(self, token_ids: list[str]) -> None:
        self._running = True
        self._subscribed = set(token_ids)
        while self._running:
            try:
                await self._connect_and_stream()
            except Exception as e:
                logger.warning(f"PriceFeed disconnected: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    async def _connect_and_stream(self) -> None:
        async with websockets.connect(WS_URL) as ws:
            self._ws = ws
            for token_id in self._subscribed:
                await ws.send(json.dumps({
                    "type": "subscribe",
                    "channel": "market",
                    "market": token_id,
                }))
            async for message in ws:
                await self._handle_message(json.loads(message))

    async def _handle_message(self, data: dict) -> None:
        token_id = data.get("asset_id") or data.get("token_id")
        bids_raw = data.get("bids", [])
        asks_raw = data.get("asks", [])
        if not token_id or (not bids_raw and not asks_raw):
            return
        bids = sorted(
            [(float(b["price"]), float(b["size"])) for b in bids_raw],
            reverse=True
        )
        asks = sorted(
            [(float(a["price"]), float(a["size"])) for a in asks_raw]
        )
        event = OrderbookEvent(
            market_id=data.get("market", ""),
            token_id=token_id,
            bids=bids,
            asks=asks,
            timestamp=float(data.get("timestamp", 0)),
        )
        await self._bus.publish(event)

    async def update_subscriptions(self, token_ids: list[str]) -> None:
        new_tokens = set(token_ids) - self._subscribed
        self._subscribed = set(token_ids)
        if self._ws and new_tokens:
            for token_id in new_tokens:
                await self._ws.send(json.dumps({
                    "type": "subscribe",
                    "channel": "market",
                    "market": token_id,
                }))

    def stop(self) -> None:
        self._running = False
```

- [ ] **Step 2: Commit**

```bash
git add core/price_feed.py
git commit -m "feat: WebSocket price feed with auto-reconnect"
```

---

## Task 9: Order Executor

**Files:**
- Create: `core/order_executor.py`
- Create: `tests/test_order_executor.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_order_executor.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.order_executor import OrderExecutor
from core.event_bus import SignalEvent
from db.database import get_open_trades

@pytest.fixture
def mock_clob():
    client = MagicMock()
    client.create_order = MagicMock(return_value=MagicMock())
    client.post_order = MagicMock(return_value={"orderID": "order123", "status": "LIVE"})
    client.cancel = MagicMock(return_value={"canceled": [{"orderID": "order123"}]})
    return client

@pytest.fixture
def mock_position_manager():
    pm = MagicMock()
    pm.bankroll = 300.0
    pm.open_position = AsyncMock()
    return pm

@pytest.fixture
def mock_risk_manager():
    rm = MagicMock()
    rm.can_place_order = AsyncMock(return_value=True)
    rm.is_halted = AsyncMock(return_value=False)
    return rm

@pytest.mark.asyncio
async def test_execute_signal_places_order(db, config, mock_clob,
                                           mock_position_manager, mock_risk_manager):
    executor = OrderExecutor(mock_clob, mock_position_manager, mock_risk_manager, db, config)
    signal = SignalEvent(
        strategy='scalping', market_id='m1', token_id='tok1',
        side='BUY', estimated_prob=0.6, implied_prob=0.5, edge=0.1
    )
    order_id = await executor.execute_signal(signal)
    assert order_id == "order123"
    trades = await get_open_trades(db)
    assert len(trades) == 1

@pytest.mark.asyncio
async def test_execute_blocked_by_risk_manager(db, config, mock_clob,
                                               mock_position_manager, mock_risk_manager):
    mock_risk_manager.can_place_order = AsyncMock(return_value=False)
    executor = OrderExecutor(mock_clob, mock_position_manager, mock_risk_manager, db, config)
    signal = SignalEvent('scalping', 'm1', 'tok1', 'BUY', 0.6, 0.5, 0.1)
    order_id = await executor.execute_signal(signal)
    assert order_id is None
    trades = await get_open_trades(db)
    assert len(trades) == 0

@pytest.mark.asyncio
async def test_cancel_order(db, config, mock_clob,
                            mock_position_manager, mock_risk_manager):
    executor = OrderExecutor(mock_clob, mock_position_manager, mock_risk_manager, db, config)
    result = await executor.cancel_order("order123")
    assert result is True
    mock_clob.cancel.assert_called_once()
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_order_executor.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create core/order_executor.py**

```python
import logging
import aiosqlite
from config import Config
from core.event_bus import SignalEvent
from core.kelly_sizer import compute_bet_size
from core.position_manager import PositionManager
from core.risk_manager import RiskManager
from db.database import insert_trade

logger = logging.getLogger("system")


class OrderExecutor:
    def __init__(self, clob_client, position_manager: PositionManager,
                 risk_manager: RiskManager, db: aiosqlite.Connection,
                 config: Config):
        self._clob = clob_client
        self._pm = position_manager
        self._rm = risk_manager
        self._db = db
        self._config = config

    async def execute_signal(self, signal: SignalEvent) -> str | None:
        if not await self._rm.can_place_order(
            signal.strategy, 0.0, self._pm.bankroll
        ):
            return None

        size = compute_bet_size(
            estimated_prob=signal.estimated_prob,
            implied_prob=signal.implied_prob,
            bankroll=self._pm.bankroll,
            kelly_fraction=self._config.kelly_fraction,
        )
        if size == 0.0:
            return None

        price = signal.implied_prob if signal.side == "BUY" else 1.0 - signal.implied_prob

        try:
            from py_clob_client.clob_types import OrderArgs, OrderType
            order_args = OrderArgs(
                token_id=signal.token_id,
                price=price,
                size=size,
                side=signal.side,
            )
            signed = self._clob.create_order(order_args)
            resp = self._clob.post_order(signed, OrderType.GTC)
            order_id = resp.get("orderID")
        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            return None

        trade_id = await insert_trade(
            self._db,
            strategy=signal.strategy,
            market_id=signal.market_id,
            token_id=signal.token_id,
            side=signal.side,
            size=size,
            entry_price=price,
            order_id=order_id,
        )
        await self._pm.open_position(
            trade_id=trade_id,
            strategy=signal.strategy,
            market_id=signal.market_id,
            token_id=signal.token_id,
            side=signal.side,
            size=size,
            entry_price=price,
        )
        logger.info(f"Order placed: {order_id} | {signal.strategy} | {signal.side} {size} @ {price}")
        return order_id

    async def cancel_order(self, order_id: str) -> bool:
        try:
            self._clob.cancel(order_id=order_id)
            return True
        except Exception as e:
            logger.error(f"Cancel failed for {order_id}: {e}")
            return False
```

- [ ] **Step 4: Run to verify passing**

```bash
pytest tests/test_order_executor.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add core/order_executor.py tests/test_order_executor.py
git commit -m "feat: order executor with Kelly sizing and CLOB submission"
```

---

## Task 9b: Position Exit Manager

**Files:**
- Modify: `core/order_executor.py` — add `exit_position()` method
- Modify: `main.py` — add `exit_monitor()` coroutine (added in Task 15)

This task fills the gap between opening scalping positions and closing them at the 60-second time stop or price-reversion exit.

- [ ] **Step 1: Write failing test for exit_position**

Add to `tests/test_order_executor.py`:

```python
@pytest.mark.asyncio
async def test_exit_position_closes_trade(db, config, mock_clob,
                                          mock_position_manager, mock_risk_manager):
    mock_position_manager.close_position = AsyncMock(return_value=0.42)
    executor = OrderExecutor(mock_clob, mock_position_manager, mock_risk_manager, db, config)
    pos = {
        "trade_id": 1, "strategy": "scalping", "market_id": "m1",
        "token_id": "tok1", "side": "BUY", "size": 10.0,
        "entry_price": 0.50, "current_price": 0.55,
    }
    await executor.exit_position(trade_id=1, pos=pos)
    mock_position_manager.close_position.assert_called_once_with(1, 0.55)
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_order_executor.py::test_exit_position_closes_trade -v
```

Expected: AttributeError — `exit_position` does not exist.

- [ ] **Step 3: Add exit_position to core/order_executor.py**

Add this method to the `OrderExecutor` class (after `cancel_order`):

```python
async def exit_position(self, trade_id: int, pos: dict) -> None:
    try:
        from py_clob_client.clob_types import OrderArgs, OrderType
        exit_price = pos.get("current_price", pos["entry_price"])
        order_args = OrderArgs(
            token_id=pos["token_id"],
            price=max(exit_price - 0.01, 0.01),
            size=pos["size"],
            side="SELL",
        )
        signed = self._clob.create_order(order_args)
        self._clob.post_order(signed, OrderType.GTC)
    except Exception as e:
        logger.error(f"Exit order failed for trade {trade_id}: {e}")
        exit_price = pos.get("current_price", pos["entry_price"])

    pnl = await self._pm.close_position(trade_id, exit_price)
    logger.info(f"Closed trade {trade_id}: PnL={pnl:+.4f}")
```

- [ ] **Step 4: Run tests to verify passing**

```bash
pytest tests/test_order_executor.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add core/order_executor.py tests/test_order_executor.py
git commit -m "feat: order executor exit_position for time-stop and reversion closes"
```

---

## Task 10: Scalping Strategy

**Files:**
- Create: `strategies/base_strategy.py`
- Create: `strategies/scalping.py`
- Create: `tests/test_scalping.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_scalping.py
import time
import pytest
from core.event_bus import OrderbookEvent
from strategies.scalping import ScalpingStrategy

def make_event(bid: float, ask: float, token_id: str = "tok1") -> OrderbookEvent:
    return OrderbookEvent(
        market_id="m1",
        token_id=token_id,
        bids=[(bid, 100.0)],
        asks=[(ask, 100.0)],
        timestamp=time.time(),
    )

def rising_events(n: int = 12) -> list[OrderbookEvent]:
    events = []
    for i in range(n):
        mid = 0.42 + i * 0.005
        events.append(make_event(mid - 0.005, mid + 0.005))
    return events

def falling_events(n: int = 12) -> list[OrderbookEvent]:
    events = []
    for i in range(n):
        mid = 0.62 - i * 0.005
        events.append(make_event(mid - 0.005, mid + 0.005))
    return events

@pytest.mark.asyncio
async def test_no_signal_when_spread_too_tight(config):
    strategy = ScalpingStrategy(config)
    for e in rising_events():
        await strategy.on_orderbook_update(e)
    # 0.5% spread — below 2% threshold
    signal = await strategy.on_orderbook_update(make_event(0.498, 0.502))
    assert signal is None

@pytest.mark.asyncio
async def test_buy_signal_on_wide_spread_and_rising(config):
    strategy = ScalpingStrategy(config)
    for e in rising_events():
        await strategy.on_orderbook_update(e)
    # 6% spread on rising market
    signal = await strategy.on_orderbook_update(make_event(0.47, 0.53))
    assert signal is not None
    assert signal.side == "BUY"
    assert signal.strategy == "scalping"

@pytest.mark.asyncio
async def test_sell_signal_on_wide_spread_and_falling(config):
    strategy = ScalpingStrategy(config)
    for e in falling_events():
        await strategy.on_orderbook_update(e)
    signal = await strategy.on_orderbook_update(make_event(0.37, 0.43))
    assert signal is not None
    assert signal.side == "SELL"

@pytest.mark.asyncio
async def test_no_signal_with_flat_momentum(config):
    strategy = ScalpingStrategy(config)
    flat = make_event(0.47, 0.53)
    for _ in range(12):
        await strategy.on_orderbook_update(flat)
    signal = await strategy.on_orderbook_update(make_event(0.47, 0.53))
    assert signal is None
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_scalping.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create strategies/base_strategy.py**

```python
from abc import ABC, abstractmethod
from core.event_bus import OrderbookEvent, SignalEvent


class BaseStrategy(ABC):
    name: str

    @abstractmethod
    async def on_orderbook_update(
        self, event: OrderbookEvent
    ) -> list[SignalEvent] | None:
        ...
```

- [ ] **Step 4: Create strategies/scalping.py**

```python
from collections import deque
from config import Config
from core.event_bus import OrderbookEvent, SignalEvent
from strategies.base_strategy import BaseStrategy

MOMENTUM_WINDOW = 10
MOMENTUM_THRESHOLD = 0.003  # 0.3% net change to confirm direction


class ScalpingStrategy(BaseStrategy):
    name = "scalping"

    def __init__(self, config: Config):
        self._config = config
        self._mid_history: dict[str, deque] = {}

    async def on_orderbook_update(
        self, event: OrderbookEvent
    ) -> list[SignalEvent] | None:
        if not event.bids or not event.asks:
            return None

        best_bid = event.bids[0][0]
        best_ask = event.asks[0][0]
        mid = (best_bid + best_ask) / 2
        spread_pct = (best_ask - best_bid) / mid * 100

        if spread_pct < self._config.min_spread_pct:
            return None

        history = self._mid_history.setdefault(
            event.token_id, deque(maxlen=MOMENTUM_WINDOW)
        )
        history.append(mid)

        if len(history) < MOMENTUM_WINDOW:
            return None

        net_move = history[-1] - history[0]
        if abs(net_move) < MOMENTUM_THRESHOLD:
            return None

        side = "BUY" if net_move > 0 else "SELL"
        implied_prob = best_ask if side == "BUY" else (1.0 - best_bid)
        estimated_prob = implied_prob + (self._config.min_spread_pct / 200)

        return [SignalEvent(
            strategy=self.name,
            market_id=event.market_id,
            token_id=event.token_id,
            side=side,
            estimated_prob=estimated_prob,
            implied_prob=implied_prob,
            edge=estimated_prob - implied_prob,
        )]
```

- [ ] **Step 5: Run to verify passing**

```bash
pytest tests/test_scalping.py -v
```

Expected: 4 tests pass.

- [ ] **Step 6: Commit**

```bash
git add strategies/base_strategy.py strategies/scalping.py tests/test_scalping.py
git commit -m "feat: scalping strategy with spread and momentum filter"
```

---

## Task 11: Arbitrage Strategy

**Files:**
- Create: `strategies/arbitrage.py`
- Create: `tests/test_arbitrage.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_arbitrage.py
import time
import pytest
from core.event_bus import OrderbookEvent
from strategies.arbitrage import ArbitrageStrategy

MARKET_MAP = {
    "m1": {
        "yes_token_id": "yes1",
        "no_token_id": "no1",
        "event_id": "evt1",
    }
}

def yes_event(ask: float) -> OrderbookEvent:
    return OrderbookEvent("m1", "yes1", [(ask - 0.02, 100)], [(ask, 100)], time.time())

def no_event(ask: float) -> OrderbookEvent:
    return OrderbookEvent("m1", "no1", [(ask - 0.02, 100)], [(ask, 100)], time.time())

@pytest.mark.asyncio
async def test_arb_signal_when_both_asks_sum_below_one(config):
    arb = ArbitrageStrategy(config, MARKET_MAP)
    await arb.on_orderbook_update(yes_event(0.47))
    signals = await arb.on_orderbook_update(no_event(0.47))
    # YES ask 0.47 + NO ask 0.47 = 0.94 < 1.0 - 1.5% fee = 0.985
    assert signals is not None
    assert len(signals) == 2
    sides = {s.token_id: s.side for s in signals}
    assert sides["yes1"] == "BUY"
    assert sides["no1"] == "BUY"

@pytest.mark.asyncio
async def test_no_signal_when_sum_above_threshold(config):
    arb = ArbitrageStrategy(config, MARKET_MAP)
    await arb.on_orderbook_update(yes_event(0.51))
    signals = await arb.on_orderbook_update(no_event(0.51))
    # 0.51 + 0.51 = 1.02 > 0.985, no arb
    assert signals is None

@pytest.mark.asyncio
async def test_no_signal_on_first_leg_only(config):
    arb = ArbitrageStrategy(config, MARKET_MAP)
    signals = await arb.on_orderbook_update(yes_event(0.47))
    assert signals is None

@pytest.mark.asyncio
async def test_signal_edge_calculated_correctly(config):
    arb = ArbitrageStrategy(config, MARKET_MAP)
    await arb.on_orderbook_update(yes_event(0.47))
    signals = await arb.on_orderbook_update(no_event(0.47))
    assert signals is not None
    total_cost = sum(s.implied_prob for s in signals)
    assert total_cost == pytest.approx(0.94, rel=1e-3)
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_arbitrage.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create strategies/arbitrage.py**

```python
from config import Config
from core.event_bus import OrderbookEvent, SignalEvent
from strategies.base_strategy import BaseStrategy

POLYMARKET_FEE_PCT = 0.02  # 2% taker fee


class ArbitrageStrategy(BaseStrategy):
    name = "arbitrage"

    def __init__(self, config: Config, market_map: dict):
        self._config = config
        # market_map: condition_id → {yes_token_id, no_token_id, event_id}
        self._market_map = market_map
        # token_id → latest best ask price
        self._latest_ask: dict[str, float] = {}
        # Build reverse lookup: token_id → condition_id + role
        self._token_to_market: dict[str, tuple[str, str]] = {}
        for cond_id, info in market_map.items():
            self._token_to_market[info["yes_token_id"]] = (cond_id, "yes")
            self._token_to_market[info["no_token_id"]] = (cond_id, "no")

    async def on_orderbook_update(
        self, event: OrderbookEvent
    ) -> list[SignalEvent] | None:
        if not event.asks:
            return None

        token_id = event.token_id
        best_ask = event.asks[0][0]
        self._latest_ask[token_id] = best_ask

        if token_id not in self._token_to_market:
            return None

        cond_id, _ = self._token_to_market[token_id]
        info = self._market_map[cond_id]
        yes_id = info["yes_token_id"]
        no_id = info["no_token_id"]

        if yes_id not in self._latest_ask or no_id not in self._latest_ask:
            return None

        yes_ask = self._latest_ask[yes_id]
        no_ask = self._latest_ask[no_id]
        total_cost = yes_ask + no_ask
        threshold = 1.0 - (self._config.min_arb_edge_pct / 100)

        if total_cost >= threshold:
            return None

        # Profit per $1 of combined investment = 1.0 - total_cost
        edge = 1.0 - total_cost

        return [
            SignalEvent(
                strategy=self.name,
                market_id=event.market_id,
                token_id=yes_id,
                side="BUY",
                estimated_prob=0.5 + edge / 2,
                implied_prob=yes_ask,
                edge=edge / 2,
            ),
            SignalEvent(
                strategy=self.name,
                market_id=event.market_id,
                token_id=no_id,
                side="BUY",
                estimated_prob=0.5 + edge / 2,
                implied_prob=no_ask,
                edge=edge / 2,
            ),
        ]
```

- [ ] **Step 4: Run to verify passing**

```bash
pytest tests/test_arbitrage.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add strategies/arbitrage.py tests/test_arbitrage.py
git commit -m "feat: arbitrage strategy detects complement pair mispricings"
```

---

## Task 12: Logging Setup

**Files:**
- Create: `logging/logger.py`

- [ ] **Step 1: Create logging/logger.py**

```python
import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")


def setup_logger(name: str, log_file: str) -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    handler = RotatingFileHandler(
        os.path.join(LOG_DIR, log_file),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)
    return logger
```

- [ ] **Step 2: Commit**

```bash
git add logging/logger.py
git commit -m "feat: rotating file logger per strategy"
```

---

## Task 13: Dashboard Routes

**Files:**
- Create: `dashboard/server.py`
- Create: `dashboard/routes.py`
- Create: `tests/test_routes.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_routes.py
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from db.database import insert_trade, update_trade

@pytest.fixture
def app(db, config):
    from dashboard.server import create_app
    return create_app(db, config)

@pytest.mark.asyncio
async def test_performance_endpoint_returns_summary(app, db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/performance")
    assert response.status_code == 200
    data = response.json()
    assert "total_pnl" in data
    assert "scalping" in data
    assert "arbitrage" in data

@pytest.mark.asyncio
async def test_trades_endpoint_returns_list(app, db):
    await insert_trade(db, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/trades?limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_trades_endpoint_filters_by_strategy(app, db):
    await insert_trade(db, 'scalping', 'm1', 'tok1', 'BUY', 10.0, 0.50)
    await insert_trade(db, 'arbitrage', 'm2', 'tok2', 'BUY', 5.0, 0.47)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/trades?strategy=scalping&limit=10")
    trades = response.json()
    assert all(t["strategy"] == "scalping" for t in trades)

@pytest.mark.asyncio
async def test_positions_endpoint_returns_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/positions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_routes.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create dashboard/server.py**

```python
import aiosqlite
import threading
import uvicorn
from config import Config
from dashboard.routes import create_router

_positions: list[dict] = []  # shared reference updated by main loop


def create_app(db: aiosqlite.Connection, config: Config):
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    import os

    app = FastAPI(title="Polymarket Bot")
    router = create_router(db, config, positions_ref=_positions)
    app.include_router(router)

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app


def run_dashboard(db: aiosqlite.Connection, config: Config) -> None:
    import asyncio
    app = create_app(db, config)
    uvicorn.run(app, host="0.0.0.0", port=config.dashboard_port, log_level="warning")
```

- [ ] **Step 4: Create dashboard/routes.py**

```python
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
            "scalping": {
                "pnl": round(scalping["pnl"], 4),
                "wins": scalping["wins"],
                "total": scalping["total"],
            },
            "arbitrage": {
                "pnl": round(arbitrage["pnl"], 4),
                "wins": arbitrage["wins"],
                "total": arbitrage["total"],
            },
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
```

- [ ] **Step 5: Run to verify passing**

```bash
pytest tests/test_routes.py -v
```

Expected: 4 tests pass.

- [ ] **Step 6: Commit**

```bash
git add dashboard/server.py dashboard/routes.py tests/test_routes.py
git commit -m "feat: FastAPI dashboard with performance, trades, and positions endpoints"
```

---

## Task 14: Dashboard Static Files

**Files:**
- Create: `dashboard/static/index.html`
- Create: `dashboard/static/charts.js`

- [ ] **Step 1: Create dashboard/static/index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Polymarket Bot Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" />
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    body { background: #0d1117; color: #e6edf3; }
    .card { background: #161b22; border: 1px solid #30363d; }
    .pnl-positive { color: #3fb950; }
    .pnl-negative { color: #f85149; }
    .live-dot { display: inline-block; width: 8px; height: 8px;
                background: #3fb950; border-radius: 50%;
                animation: pulse 1.5s infinite; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
    table { font-size: 0.85rem; }
  </style>
</head>
<body>
  <div class="container-fluid p-4">
    <div class="d-flex align-items-center mb-4 gap-2">
      <h4 class="mb-0">Polymarket Bot Dashboard</h4>
      <span class="live-dot"></span>
      <span class="text-muted small">Live</span>
    </div>

    <!-- Stats row -->
    <div class="row g-3 mb-4">
      <div class="col-md-4">
        <div class="card p-3">
          <div class="text-muted small">Total P&amp;L</div>
          <div id="total-pnl" class="fs-3 fw-bold">$0.00</div>
          <div id="win-rate" class="text-muted small">Win rate: --%</div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card p-3">
          <div class="text-muted small">Scalping P&amp;L</div>
          <div id="scalping-pnl" class="fs-3 fw-bold">$0.00</div>
          <div id="scalping-trades" class="text-muted small">0 trades</div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card p-3">
          <div class="text-muted small">Arbitrage P&amp;L</div>
          <div id="arb-pnl" class="fs-3 fw-bold">$0.00</div>
          <div id="arb-trades" class="text-muted small">0 trades</div>
        </div>
      </div>
    </div>

    <!-- Chart -->
    <div class="card p-3 mb-4">
      <canvas id="pnl-chart" height="80"></canvas>
    </div>

    <!-- Tabs -->
    <ul class="nav nav-tabs mb-3" id="tabs">
      <li class="nav-item"><a class="nav-link active" href="#" data-tab="all">Overview</a></li>
      <li class="nav-item"><a class="nav-link" href="#" data-tab="scalping">Scalping</a></li>
      <li class="nav-item"><a class="nav-link" href="#" data-tab="arbitrage">Arbitrage</a></li>
    </ul>

    <!-- Positions -->
    <div class="card p-3 mb-4">
      <h6 class="mb-3">Open Positions</h6>
      <table class="table table-dark table-sm mb-0">
        <thead><tr><th>Strategy</th><th>Market</th><th>Side</th><th>Size</th><th>Entry</th><th>Current</th></tr></thead>
        <tbody id="positions-body"><tr><td colspan="6" class="text-muted">No open positions</td></tr></tbody>
      </table>
    </div>

    <!-- Trade history -->
    <div class="card p-3">
      <h6 class="mb-3">Recent Trades</h6>
      <table class="table table-dark table-sm mb-0">
        <thead><tr><th>Time</th><th>Strategy</th><th>Market</th><th>Side</th><th>Size</th><th>Entry</th><th>Exit</th><th>P&amp;L</th></tr></thead>
        <tbody id="trades-body"><tr><td colspan="8" class="text-muted">No trades yet</td></tr></tbody>
      </table>
    </div>
  </div>
  <script src="charts.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create dashboard/static/charts.js**

```javascript
let chart;
const pnlHistory = { labels: [], scalping: [], arbitrage: [], total: [] };
let activeTab = 'all';

function initChart() {
  const ctx = document.getElementById('pnl-chart').getContext('2d');
  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: pnlHistory.labels,
      datasets: [
        { label: 'Total', data: pnlHistory.total, borderColor: '#58a6ff', tension: 0.2, pointRadius: 0 },
        { label: 'Scalping', data: pnlHistory.scalping, borderColor: '#3fb950', tension: 0.2, pointRadius: 0 },
        { label: 'Arbitrage', data: pnlHistory.arbitrage, borderColor: '#d2a8ff', tension: 0.2, pointRadius: 0 },
      ]
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: '#e6edf3' } } },
      scales: {
        x: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } },
        y: { ticks: { color: '#8b949e', callback: v => '$' + v.toFixed(2) }, grid: { color: '#21262d' } }
      }
    }
  });
}

function formatPnl(val) {
  const cls = val >= 0 ? 'pnl-positive' : 'pnl-negative';
  return `<span class="${cls}">${val >= 0 ? '+' : ''}$${val.toFixed(4)}</span>`;
}

async function refreshPerformance() {
  const data = await fetch('/api/performance').then(r => r.json());
  document.getElementById('total-pnl').innerHTML = formatPnl(data.total_pnl);
  document.getElementById('win-rate').textContent = `Win rate: ${data.win_rate.toFixed(1)}%`;
  document.getElementById('scalping-pnl').innerHTML = formatPnl(data.scalping.pnl);
  document.getElementById('scalping-trades').textContent = `${data.scalping.total} trades`;
  document.getElementById('arb-pnl').innerHTML = formatPnl(data.arbitrage.pnl);
  document.getElementById('arb-trades').textContent = `${data.arbitrage.total} trades`;

  const now = new Date().toLocaleTimeString();
  pnlHistory.labels.push(now);
  pnlHistory.total.push(data.total_pnl);
  pnlHistory.scalping.push(data.scalping.pnl);
  pnlHistory.arbitrage.push(data.arbitrage.pnl);
  if (pnlHistory.labels.length > 120) {
    pnlHistory.labels.shift(); pnlHistory.total.shift();
    pnlHistory.scalping.shift(); pnlHistory.arbitrage.shift();
  }
  chart.update();
}

async function refreshTrades() {
  const strategy = activeTab === 'all' ? '' : `strategy=${activeTab}&`;
  const trades = await fetch(`/api/trades?${strategy}limit=50`).then(r => r.json());
  const body = document.getElementById('trades-body');
  if (!trades.length) {
    body.innerHTML = '<tr><td colspan="8" class="text-muted">No trades yet</td></tr>';
    return;
  }
  body.innerHTML = trades.map(t => `
    <tr>
      <td>${t.opened_at ? t.opened_at.slice(11, 19) : '--'}</td>
      <td><span class="badge bg-secondary">${t.strategy}</span></td>
      <td class="text-truncate" style="max-width:120px">${t.market_id}</td>
      <td>${t.side}</td>
      <td>${t.size.toFixed(2)}</td>
      <td>${t.entry_price.toFixed(3)}</td>
      <td>${t.exit_price != null ? t.exit_price.toFixed(3) : '--'}</td>
      <td>${t.realized_pnl != null ? formatPnl(t.realized_pnl) : '--'}</td>
    </tr>`).join('');
}

async function refreshPositions() {
  const positions = await fetch('/api/positions').then(r => r.json());
  const body = document.getElementById('positions-body');
  if (!positions.length) {
    body.innerHTML = '<tr><td colspan="6" class="text-muted">No open positions</td></tr>';
    return;
  }
  body.innerHTML = positions.map(p => `
    <tr>
      <td><span class="badge bg-secondary">${p.strategy}</span></td>
      <td class="text-truncate" style="max-width:120px">${p.market_id}</td>
      <td>${p.side}</td>
      <td>${p.size.toFixed(2)}</td>
      <td>${p.entry_price.toFixed(3)}</td>
      <td>${p.current_price != null ? p.current_price.toFixed(3) : '--'}</td>
    </tr>`).join('');
}

async function refresh() {
  await Promise.all([refreshPerformance(), refreshTrades(), refreshPositions()]);
}

document.querySelectorAll('[data-tab]').forEach(el => {
  el.addEventListener('click', e => {
    e.preventDefault();
    activeTab = el.dataset.tab;
    document.querySelectorAll('[data-tab]').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    refreshTrades();
  });
});

initChart();
refresh();
setInterval(refresh, 5000);
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/static/
git commit -m "feat: web dashboard with Chart.js P&L curves and trade tables"
```

---

## Task 15: Main Entrypoint

**Files:**
- Create: `main.py`

- [ ] **Step 1: Create main.py**

```python
import asyncio
import logging
import threading
from datetime import date

from config import load_config
from core.event_bus import EventBus, OrderbookEvent, SignalEvent
from core.kelly_sizer import compute_bet_size
from core.market_scanner import MarketScanner
from core.order_executor import OrderExecutor
from core.position_manager import PositionManager
from core.price_feed import PriceFeed
from core.risk_manager import RiskManager
from dashboard.server import run_dashboard
from db.database import (
    init_db, upsert_daily_stats, get_daily_stats,
    is_circuit_breaker_triggered,
)
from logging.logger import setup_logger
from strategies.arbitrage import ArbitrageStrategy
from strategies.scalping import ScalpingStrategy

SCAN_INTERVAL = 30  # seconds between market scans
LOOP_YIELD = 0.05   # seconds between event loop iterations


async def process_signals(signals: list[SignalEvent], executor: OrderExecutor) -> None:
    for signal in signals:
        await executor.execute_signal(signal)


async def strategy_loop(
    event_bus: EventBus,
    scalping: ScalpingStrategy,
    arbitrage: ArbitrageStrategy,
    executor: OrderExecutor,
) -> None:
    ob_queue: asyncio.Queue = asyncio.Queue()
    event_bus.subscribe(OrderbookEvent, ob_queue)

    while True:
        event: OrderbookEvent = await ob_queue.get()
        for strategy in (scalping, arbitrage):
            signals = await strategy.on_orderbook_update(event)
            if signals:
                await process_signals(signals, executor)


async def scanner_loop(
    clob_client,
    scanner: MarketScanner,
    price_feed: PriceFeed,
    arbitrage: ArbitrageStrategy,
    volume_threshold: float,
) -> None:
    while True:
        markets = await scanner.scan(clob_client, volume_threshold)
        token_ids = []
        market_map = {}
        for m in markets:
            token_ids += [m.token_yes_id, m.token_no_id]
            market_map[m.condition_id] = {
                "yes_token_id": m.token_yes_id,
                "no_token_id": m.token_no_id,
                "event_id": m.event_id,
            }
        arbitrage._market_map = market_map
        arbitrage._token_to_market = {}
        for cid, info in market_map.items():
            arbitrage._token_to_market[info["yes_token_id"]] = (cid, "yes")
            arbitrage._token_to_market[info["no_token_id"]] = (cid, "no")

        await price_feed.update_subscriptions(token_ids)
        await asyncio.sleep(SCAN_INTERVAL)


async def exit_monitor_loop(
    position_manager: PositionManager,
    executor: OrderExecutor,
    config,
) -> None:
    open_times: dict[int, float] = {}
    while True:
        await asyncio.sleep(1)
        positions = await position_manager.get_positions()
        now = asyncio.get_event_loop().time()
        active_ids = set()
        for pos in positions:
            tid = pos["trade_id"]
            active_ids.add(tid)
            open_times.setdefault(tid, now)
            elapsed = now - open_times[tid]
            if pos["strategy"] == "scalping" and elapsed >= config.max_hold_seconds:
                logger.info(f"Time stop for trade {tid} after {elapsed:.0f}s")
                await executor.exit_position(tid, pos)
                open_times.pop(tid, None)
        open_times = {k: v for k, v in open_times.items() if k in active_ids}


async def risk_monitor_loop(
    position_manager: PositionManager,
    risk_manager: RiskManager,
    db,
    config,
) -> None:
    today = date.today().isoformat()
    stats = await get_daily_stats(db, today)
    day_start_bankroll = stats["start_bankroll"] if stats else config.starting_bankroll
    peak_bankroll = stats["peak_bankroll"] if stats else config.starting_bankroll

    while True:
        bankroll = position_manager.bankroll
        peak_bankroll = max(peak_bankroll, bankroll)
        await upsert_daily_stats(
            db, today, day_start_bankroll, peak_bankroll
        )
        await risk_manager.check_daily_loss(bankroll, day_start_bankroll)
        await risk_manager.check_drawdown(bankroll, peak_bankroll)
        await asyncio.sleep(10)


async def main() -> None:
    config = load_config()

    setup_logger("scalping", "scalping.log")
    setup_logger("arbitrage", "arbitrage.log")
    setup_logger("system", "system.log")
    logger = logging.getLogger("system")

    db = await init_db("polymarket.db")

    today = date.today().isoformat()
    stats = await get_daily_stats(db, today)
    if not stats:
        await upsert_daily_stats(
            db, today,
            start_bankroll=config.starting_bankroll,
            peak_bankroll=config.starting_bankroll,
        )

    if await is_circuit_breaker_triggered(db):
        logger.warning("Circuit breaker is active. Reset it manually before starting.")
        return

    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import ApiCreds

    clob_client = ClobClient(
        host="https://clob.polymarket.com",
        key=config.wallet_private_key,
        chain_id=config.chain_id,
        creds=ApiCreds(config.api_key, config.api_secret, config.api_passphrase),
    )

    event_bus = EventBus()
    position_manager = PositionManager(
        starting_bankroll=config.starting_bankroll, db=db
    )
    risk_manager = RiskManager(config=config, db=db)
    scalping = ScalpingStrategy(config=config)
    arbitrage = ArbitrageStrategy(config=config, market_map={})
    order_executor = OrderExecutor(
        clob_client, position_manager, risk_manager, db, config
    )
    scanner = MarketScanner()
    price_feed = PriceFeed(event_bus=event_bus)

    dashboard_thread = threading.Thread(
        target=run_dashboard, args=(db, config), daemon=True
    )
    dashboard_thread.start()
    logger.info(f"Dashboard running on port {config.dashboard_port}")

    markets = await scanner.scan(clob_client, config.volume_threshold_usd)
    token_ids = [t for m in markets for t in (m.token_yes_id, m.token_no_id)]
    logger.info(f"Found {len(markets)} markets, {len(token_ids)} token feeds")

    await asyncio.gather(
        price_feed.start(token_ids),
        strategy_loop(event_bus, scalping, arbitrage, order_executor),
        scanner_loop(clob_client, scanner, price_feed, arbitrage, config.volume_threshold_usd),
        exit_monitor_loop(position_manager, order_executor, config),
        risk_monitor_loop(position_manager, risk_manager, db, config),
    )


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run full test suite to confirm nothing broken**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: main entrypoint wires all components and starts event loop"
```

---

## Task 16: Deployment Files

**Files:**
- Create: `deploy.sh`
- Create: `polymarket-bot.service`

- [ ] **Step 1: Create deploy.sh**

```bash
#!/usr/bin/env bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$REPO_DIR/venv"

echo "Pulling latest code..."
git -C "$REPO_DIR" pull

echo "Installing dependencies..."
if [ ! -d "$VENV" ]; then
  python3.11 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q -r "$REPO_DIR/requirements.txt"

echo "Restarting service..."
sudo systemctl restart polymarket-bot
sudo systemctl status polymarket-bot --no-pager
```

- [ ] **Step 2: Make deploy.sh executable**

```bash
chmod +x deploy.sh
```

- [ ] **Step 3: Create polymarket-bot.service**

```ini
[Unit]
Description=Polymarket HFT Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/polymarket
EnvironmentFile=/home/ubuntu/polymarket/.env
ExecStart=/home/ubuntu/polymarket/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

> **Note:** Replace `ubuntu` and `/home/ubuntu/polymarket` with your VPS username and actual path.

- [ ] **Step 4: Final full test run**

```bash
pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 5: Final commit**

```bash
git add deploy.sh polymarket-bot.service
git commit -m "feat: deployment scripts and systemd service unit"
```

---

## Setup Checklist (run once on VPS)

1. Copy repo to VPS: `scp -r /Users/isaackamahi/Desktop/Polymarket user@vps:~/polymarket`
2. SSH in and run `./deploy.sh` to install deps
3. Copy `.env.example` to `.env` and fill in all values
4. Obtain Polymarket CLOB API credentials: follow the [L2 auth flow](https://docs.polymarket.com/#authentication) — requires signing a message with your wallet
5. Install service: `sudo cp polymarket-bot.service /etc/systemd/system/ && sudo systemctl enable polymarket-bot`
6. Start: `sudo systemctl start polymarket-bot`
7. Watch logs: `journalctl -fu polymarket-bot`
8. Dashboard: open `http://YOUR_VPS_IP:8080` in a browser (ensure port 8080 is open in firewall)
