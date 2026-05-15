import asyncio
from dataclasses import dataclass


@dataclass
class Market:
    condition_id: str
    event_id: str
    yes_token_id: str
    no_token_id: str
    volume: float


class MarketScanner:
    async def scan(self, clob_client, volume_threshold_usd: float) -> list[Market]:
        response = await asyncio.to_thread(clob_client.get_markets)
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
                yes_token_id=yes_token["token_id"],
                no_token_id=no_token["token_id"],
                volume=volume,
            ))
        return markets
