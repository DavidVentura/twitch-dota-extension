from dataclasses import dataclass
import httpx
import typing
import json

events = ["GameState", "HeroList", "PlayerStats", "Heroes", "Abilities", "Inventory"]

@dataclass
class PGLGameState:
    HeroList: list[dict]
    PlayerStats: list[dict]
    Heroes: list[dict]
    Abilities: list[dict]
    Inventory: list[dict]

    @staticmethod
    async def from_stream(channel_id: int) -> typing.Union['PGLGameState', None]:
        url = 'https://dota2-twitch.pglesports.com/base-data'
        async with httpx.AsyncClient() as client:
            async with client.stream('GET', url, params={"channel": channel_id}) as r:
                return await pgl_state_from_aiter(r.aiter_lines())

async def pgl_state_from_aiter(aiter: typing.AsyncIterator[str]) -> PGLGameState | None :
    cur_event = None
    d = {e: None for e in events if e != 'GameState'}
    async for line in aiter:
        if line.startswith('event:'):
            _, _, cur_event = line.partition(':')
            cur_event = cur_event.strip()
        elif line.startswith('data:'):
            if cur_event not in events:
                # not interested in data
                continue

            _, _, data = line.partition(':')
            data = json.loads(data)
            if data is None:
                continue
            if cur_event == 'GameState':
                if data.get("state") in ["DRAFTING", "STRATEGY_TIME"]:
                    return None
            else:
                assert cur_event is not None
                d[cur_event] = data
                if not any((v is None for v in d.values())):
                    return PGLGameState(**d)
    assert False

class AiterF:
    def __init__(self, path):
        self.fd = open(path, "r")
        self.iter = []
        self.iter_idx = 0

    def __aiter__(self):
        self.iter = self.fd.readlines()
        self.iter_idx = 0
        return self

    async def __anext__(self):
        if self.iter_idx >= len(self.iter):
            raise StopAsyncIteration
        self.iter_idx += 1
        return self.iter[self.iter_idx - 1]


if __name__ == '__main__':
    aiter = AiterF("pgl.txt")

    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(pgl_state_from_aiter(aiter))
