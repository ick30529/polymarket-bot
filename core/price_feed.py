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
                await ws.send(json.dumps({"type": "subscribe", "channel": "market", "market": token_id}))
            async for message in ws:
                await self._handle_message(json.loads(message))

    async def _handle_message(self, data: dict) -> None:
        token_id = data.get("asset_id") or data.get("token_id")
        bids_raw = data.get("bids", [])
        asks_raw = data.get("asks", [])
        if not token_id or (not bids_raw and not asks_raw):
            return
        bids = sorted([(float(b["price"]), float(b["size"])) for b in bids_raw], reverse=True)
        asks = sorted([(float(a["price"]), float(a["size"])) for a in asks_raw])
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
                await self._ws.send(json.dumps({"type": "subscribe", "channel": "market", "market": token_id}))

    def stop(self) -> None:
        self._running = False
