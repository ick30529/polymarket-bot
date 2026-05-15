from config import Config
from core.event_bus import OrderbookEvent, SignalEvent
from strategies.base_strategy import BaseStrategy


class ArbitrageStrategy(BaseStrategy):
    name = "arbitrage"

    def __init__(self, config: Config, market_map: dict):
        self._config = config
        self._market_map = market_map
        self._latest_ask: dict[str, float] = {}
        self._token_to_market: dict[str, tuple[str, str]] = {}
        self._rebuild_token_index()

    def _rebuild_token_index(self) -> None:
        self._token_to_market = {}
        for cond_id, info in self._market_map.items():
            self._token_to_market[info["yes_token_id"]] = (cond_id, "yes")
            self._token_to_market[info["no_token_id"]] = (cond_id, "no")

    async def on_orderbook_update(self, event: OrderbookEvent) -> list[SignalEvent] | None:
        if not event.asks:
            return None

        token_id = event.token_id
        self._latest_ask[token_id] = event.asks[0][0]

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

        edge = 1.0 - total_cost
        return [
            SignalEvent(strategy=self.name, market_id=event.market_id, token_id=yes_id,
                        side="BUY", estimated_prob=0.5 + edge/2, implied_prob=yes_ask, edge=edge/2),
            SignalEvent(strategy=self.name, market_id=event.market_id, token_id=no_id,
                        side="BUY", estimated_prob=0.5 + edge/2, implied_prob=no_ask, edge=edge/2),
        ]
