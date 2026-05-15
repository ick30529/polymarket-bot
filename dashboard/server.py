import threading
import aiosqlite
import uvicorn
from config import Config
from dashboard.routes import create_router

_positions: list[dict] = []


def create_app(db: aiosqlite.Connection, config: Config, positions_ref: list[dict] | None = None):
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    import os

    app = FastAPI(title="Polymarket Bot")
    router = create_router(db, config, positions_ref=positions_ref or _positions)
    app.include_router(router)

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app


def run_dashboard(db: aiosqlite.Connection, config: Config) -> None:
    app = create_app(db, config)
    uvicorn.run(app, host="0.0.0.0", port=config.dashboard_port, log_level="warning")
