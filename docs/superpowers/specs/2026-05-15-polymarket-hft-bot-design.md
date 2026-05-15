# Polymarket HFT Scalping/Arbitrage Bot — Design Spec

**Date:** 2026-05-15  
**Status:** Approved  

---

## Overview

A high-frequency trading bot that runs two concurrent strategies — scalping and arbitrage — on Polymarket's CLOB (Central Limit Order Book) on Polygon. Both strategies share a single process and infrastructure but are fully isolated in terms of logging, performance tracking, and kill switches. Starting capital: $300 USDC. Deployed on an existing VPS.

---

## Architecture

Single Python 3.11+ process using `asyncio` for concurrency. A central event bus (asyncio queues) connects the market scanner and price feed to both strategy workers. A separate thread runs the FastAPI dashboard server.

```
Market Scanner ──▶ Event Bus ──┬──▶ Scalping Strategy ──┐
                               └──▶ Arbitrage Strategy ──┤
                                                         ▼
                                               Order Executor
                                           (Kelly Sizer + CLOB API)
                                                         │
                                               Position & Risk Manager
                                                         │
                                                    SQLite DB

FastAPI Dashboard Server (separate thread, port 8080)
```

**Key technology choices:**
- Language: Python 3.11+
- Polymarket SDK: `py-clob-client` (official) — handles auth, order signing, Polygon submission
- Storage: SQLite — zero ops overhead, sufficient at this scale
- Dashboard: FastAPI + Chart.js (single HTML file, no build step)
- Secrets: `.env` file loaded via `python-dotenv`

---

## Project Structure

```
polymarket/
├── .env                          # secrets + config (never committed)
├── .env.example                  # documented template
├── main.py                       # entrypoint — wires everything, starts event loop
├── config.py                     # loads + validates .env, exposes typed Config object
├── db/
│   ├── schema.sql                # CREATE TABLE statements
│   └── database.py               # SQLite connection pool + query helpers
├── core/
│   ├── market_scanner.py         # polls CLOB every 30s, filters by volume threshold
│   ├── price_feed.py             # WebSocket orderbook stream per active market
│   ├── event_bus.py              # asyncio Queue wrappers, typed event definitions
│   ├── kelly_sizer.py            # fractional Kelly position sizing (25% fraction)
│   ├── order_executor.py         # wraps py-clob-client, places/cancels/retries orders
│   ├── position_manager.py       # tracks open positions and unrealized P&L
│   └── risk_manager.py           # enforces hard limits, triggers circuit breakers
├── strategies/
│   ├── base_strategy.py          # abstract interface: on_orderbook_update(), on_fill()
│   ├── scalping.py               # bid-ask spread capture + momentum filter
│   └── arbitrage.py              # cross-market price discrepancy detection
├── logging/
│   ├── logger.py                 # configures named loggers with rotating file handlers
│   ├── logs/scalping.log         # scalping trades, signals, outcomes
│   ├── logs/arbitrage.log        # arbitrage trades, signals, outcomes
│   └── logs/system.log           # scanner, executor, risk manager events
├── dashboard/
│   ├── server.py                 # FastAPI app init + startup
│   ├── routes.py                 # GET /api/performance, /api/trades, /api/positions
│   └── static/
│       ├── index.html            # single-page dashboard, auto-refreshes every 5s
│       └── charts.js             # Chart.js P&L curves + trade table rendering
├── deploy.sh                     # pulls repo, installs deps, restarts systemd service
└── polymarket-bot.service        # systemd unit file for auto-restart on crash
```

---

## Component Responsibilities

| Component | Single responsibility |
|---|---|
| `market_scanner` | Finds tradeable markets above volume threshold — nothing else |
| `price_feed` | Streams orderbook data to event bus — no strategy logic |
| `event_bus` | Routes typed events between producers and consumers |
| `kelly_sizer` | Computes position size from edge and current bankroll |
| `order_executor` | Submits orders to CLOB, handles retries, reports fills |
| `position_manager` | Tracks open positions and running P&L |
| `risk_manager` | Blocks orders that violate limits, triggers circuit breakers |
| `scalping` | Generates scalping signals — no execution |
| `arbitrage` | Generates arbitrage signals — no execution |

---

## Data Flow

1. `market_scanner` polls Polymarket CLOB REST API every 30s
2. Markets with >$10,000 24h volume pass the filter
3. Each qualifying market gets a dedicated `price_feed` WebSocket subscription
4. Every orderbook update is published to the event bus as a typed event
5. Both strategy workers consume from the same bus — no duplicate API calls
6. Strategies emit `SignalEvent` objects (market, side, estimated edge)
7. `order_executor` receives signals, calls `kelly_sizer` to compute size, checks `risk_manager`, then submits to CLOB
8. Fills are written to SQLite and published back to the bus for position tracking

---

## Strategy Logic

### Scalping
- **Signal condition:** Bid-ask spread > 2% on a qualifying market
- **Entry:** Post limit order just inside the spread (maker side — avoids taker fees)
- **Exit:** Price reverts to mid-point, OR 60-second time stop
- **Momentum filter:** Only scalp in direction of recent price movement (last 10 orderbook snapshots)
- **Log file:** `logs/scalping.log`

### Arbitrage
- **Signal condition:** Related market pairs where YES + NO prices deviate >1.5% from $1.00 after fees
- **Pair types checked:**
  - Binary complement pairs: YES + NO on the same market should sum to ~$1.00; deviation is the arb
  - Multi-outcome groups: mutually exclusive outcomes on the same event (e.g., "Candidate A wins", "Candidate B wins", "Neither wins") should sum to ~$1.00; bot detects these by matching on `event_id` from the CLOB API
- **Entry:** Simultaneous limit orders on both legs
- **Cancellation rule:** If only one leg fills within 5 seconds, cancel the unfilled leg immediately
- **Log file:** `logs/arbitrage.log`

---

## Position Sizing — Fractional Kelly

```
edge     = estimated_probability - implied_probability
full_f   = edge / odds
bet_size = bankroll × (full_f × 0.25)   # 25% fractional Kelly
```

- Minimum bet: $2.00
- Maximum bet: 10% of current bankroll (~$30 at start)
- 25% fraction used to reduce variance at $300 capital level

---

## Risk Management

| Limit | Value | Action on breach |
|---|---|---|
| Max open positions | 5 | Block new orders |
| Max single position | 10% of bankroll | Kelly output capped |
| Daily loss limit | 15% of day-start bankroll | Pause bot, log alert |
| Peak drawdown circuit breaker | 30% from portfolio peak | Full stop — manual restart required |

The circuit breaker state is persisted to SQLite so a process restart does not bypass it.

---

## Logging

- Each strategy has a named Python logger writing to its own rotating log file
- Rotation: 10MB max per file, 5 backups retained
- Log entry format: `timestamp | level | strategy | market_id | signal | size | price | outcome`
- All executed trades are also written to SQLite for dashboard queries
- `system.log` captures scanner, executor, and risk manager events

---

## Web Dashboard (port 8080)

Served by FastAPI, auto-refreshes every 5 seconds via polling `/api/performance`.

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  Polymarket Bot Dashboard          [Live ● ]        │
├──────────────┬──────────────┬───────────────────────┤
│ Total P&L    │ Scalping P&L │ Arbitrage P&L         │
├──────────────┴──────────────┴───────────────────────┤
│ [P&L Curve — both strategies overlaid, Chart.js]    │
├─────────────────────────────────────────────────────┤
│ Open Positions (N/5)   Win Rate   Sharpe Ratio      │
├─────────────────────────────────────────────────────┤
│ Recent Trades: Time | Strategy | Market | Side | P&L│
├─────────────────────────────────────────────────────┤
│ Tabs: Overview | Scalping Detail | Arbitrage Detail  │
└─────────────────────────────────────────────────────┘
```

**API endpoints:**
- `GET /api/performance` — total + per-strategy P&L, win rate, Sharpe ratio
- `GET /api/trades?strategy=scalping|arbitrage&limit=N` — paginated trade history
- `GET /api/positions` — current open positions with unrealized P&L

No authentication on the dashboard — access control handled by VPS firewall or SSH tunnel.

---

## Deployment

**Files provided:**
- `deploy.sh` — pulls latest code, installs dependencies via `pip`, restarts systemd service
- `polymarket-bot.service` — systemd unit with `Restart=always` and environment file reference
- `.env.example` — all required keys documented with descriptions

**Start command:**
```bash
python main.py
```

**Required `.env` keys:**
```
POLYMARKET_API_KEY=
POLYMARKET_API_SECRET=
POLYMARKET_WALLET_PRIVATE_KEY=
POLYMARKET_CHAIN_ID=137           # Polygon mainnet
VOLUME_THRESHOLD_USD=10000
DASHBOARD_PORT=8080
MIN_SPREAD_PCT=2.0
MIN_ARB_EDGE_PCT=1.5
MAX_HOLD_SECONDS=60
KELLY_FRACTION=0.25
MAX_POSITIONS=5
DAILY_LOSS_LIMIT_PCT=15
DRAWDOWN_LIMIT_PCT=30
```

---

## Out of Scope

- Provisioning or configuring the VPS
- Dashboard authentication (handled at network/firewall level)
- Telegram/push alerts (can be added later)
- Backtesting engine (can be added later)
