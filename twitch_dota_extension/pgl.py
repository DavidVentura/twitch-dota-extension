from dataclasses import dataclass
import logging
import httpx
import typing
import json

logger = logging.getLogger(__name__)

# https://dota2-data.pglesports.com/static/heroes.json
# https://dota2-data.pglesports.com/static/abilities.json
# https://dota2-data.pglesports.com/static/hero-abilities.json
# https://dota2-data.pglesports.com/static/aghanims.json
# https://dota2-data.pglesports.com/static/items.json
# https://dota2-data.pglesports.com/static/levels.json
# https://dota2-data.pglesports.com/static/talents.json
events = ["GameState", "HeroList", "PlayerStats", "Heroes", "Abilities", "Inventory"]


@dataclass
class PGLGameState:
    HeroList: list[dict]
    PlayerStats: list[dict]
    Heroes: list[dict]
    Abilities: list[dict]
    Inventory: list[dict]

    @staticmethod
    async def from_stream(domain: str, channel_id: int) -> typing.Union["PGLGameState", None]:
        timeout = httpx.Timeout(10.0, connect=2.0, read=6.0)
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    "GET", f"https://{domain}/base-data", params={"channel": channel_id}, timeout=timeout,
                ) as r:
                    return await pgl_state_from_aiter(r.aiter_lines())
            except httpx.ReadTimeout:
                print("eeek, timeout")


async def pgl_state_from_aiter(aiter: typing.AsyncIterator[str]) -> PGLGameState | None:
    cur_event = None
    d = {e: None for e in events if e != "GameState"}
    logger.info("Reading PGL data")
    async for line in aiter:
        if line.startswith("event:"):
            _, _, cur_event = line.partition(":")
            cur_event = cur_event.strip()
        elif line.startswith("data:"):
            if cur_event not in events:
                # not interested in data
                continue

            _, _, raw_data = line.partition(":")
            try:
                data = json.loads(raw_data)
            except json.decoder.JSONDecodeError as e:
                print(f'tried to decode illegal json: "{raw_data}": {e}')
                return None

            if data is None:
                continue
            if cur_event == "GameState":
                if data.get("state") in ["DRAFTING", "STRATEGY_TIME"]:
                    return None
            else:
                assert cur_event is not None
                d[cur_event] = data
                if not any((v is None for v in d.values())):
                    return PGLGameState(**d)
    logger.warning("Read entire response and did not build a valid GameState")
    return None
