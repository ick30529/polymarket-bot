from abc import ABC, abstractmethod
from core.event_bus import OrderbookEvent, SignalEvent


class BaseStrategy(ABC):
    name: str

    @abstractmethod
    async def on_orderbook_update(self, event: OrderbookEvent) -> list[SignalEvent] | None:
        ...
