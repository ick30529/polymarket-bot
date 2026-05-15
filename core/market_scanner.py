import asyncio
import json
from dataclasses import dataclass

import aiohttp

GAMMA_API = "https://gamma-api.polymarket.com/markets"


@dataclass
class Market:
    condition_id: str
    event_id: str
    yes_token_id: str
    no_token_id: str
    volume: float


class MarketScanner:
    async def scan(self, clob_client, volume_threshold_usd: float) -> list[Market]:
        markets = []
        offset = 0
        limit = 100
        async with aiohttp.ClientSession() as session:
            while True:
                params = {
                    "active": "true",
                    "closed": "false",
                    "accepting_orders": "true",
                    "limit": limit,
                    "offset": offset,
                }
                async with session.get(GAMMA_API, params=params) as resp:
                    data = await resp.json()
                if not data:
                    break
                for item in data:
                    volume = float(item.get("volume24hr") or item.get("volume") or 0)
                    if volume < volume_threshold_usd:
                        continue
                    clob_ids = item.get("clobTokenIds") or []
                    if isinstance(clob_ids, str):
                        clob_ids = json.loads(clob_ids)
                    outcomes = item.get("outcomes") or []
                    if isinstance(outcomes, str):
                        outcomes = json.loads(outcomes)
                    if len(clob_ids) != 2 or len(outcomes) != 2:
                        continue
                    markets.append(Market(
                        condition_id=item.get("conditionId", ""),
                        event_id=item.get("groupItemTitle", ""),
                        yes_token_id=clob_ids[0],
                        no_token_id=clob_ids[1],
                        volume=volume,
                    ))
                if len(data) < limit:
                    break
                offset += limit
        return markets
