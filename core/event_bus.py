import asyncio
from collections import defaultdict
from dataclasses import dataclass
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
