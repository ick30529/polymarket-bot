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
