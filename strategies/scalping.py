from collections import deque
from config import Config
from core.event_bus import OrderbookEvent, SignalEvent
from strategies.base_strategy import BaseStrategy

MOMENTUM_WINDOW = 10
MOMENTUM_THRESHOLD = 0.003


class ScalpingStrategy(BaseStrategy):
    name = "scalping"

    def __init__(self, config: Config):
        self._config = config
        self._mid_history: dict[str, deque] = {}

    async def on_orderbook_update(self, event: OrderbookEvent) -> list[SignalEvent] | None:
        if not event.bids or not event.asks:
            return None

        best_bid = event.bids[0][0]
        best_ask = event.asks[0][0]
        mid = (best_bid + best_ask) / 2
        spread_pct = (best_ask - best_bid) / mid * 100

        history = self._mid_history.setdefault(event.token_id, deque(maxlen=MOMENTUM_WINDOW))
        history.append(mid)

        if spread_pct < self._config.min_spread_pct:
            return None

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
