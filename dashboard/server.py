import uvicorn
from config import Config


def create_app(db_path: str, config: Config, positions_ref: list[dict]):
    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    import os
    from dashboard.routes import create_router_with_path

    app = FastAPI(title="Polymarket Bot")

    router = create_router_with_path(db_path, config, positions_ref=positions_ref)
    app.include_router(router)

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app


def run_dashboard(db_path: str, config: Config, positions_ref: list[dict]) -> None:
    app = create_app(db_path, config, positions_ref)
    uvicorn.run(app, host="0.0.0.0", port=config.dashboard_port, log_level="warning")
