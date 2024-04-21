import enum
import json
import dataclasses
from dataclasses import dataclass
from typing import Optional, Any
from pathlib import Path

import dacite
import httpx

from twitch_dota_layerth.tooltips import Hero, Ability, Item


@dataclass
class HDAbility:
    name: str


@dataclass
class HDItem:
    name: str


@dataclass
class Inventory:
    items: list[Item]
    neutral_slot: Optional[Item]

    @staticmethod
    def from_parts(items: dict[str, HDItem], itemdef: dict[str, Item]) -> 'Inventory':
        items_ = []
        for slot in ["slot0", "slot1", "slot2", "slot3", "slot4", "slot5"]:
            if items[slot].name != 'empty':
                items_.append(itemdef[items[slot].name])
        neutral = itemdef[items["neutral0"].name] if items["neutral0"].name != 'empty' else None
        return Inventory(items_, neutral)

@dataclass
class HeroData:
    name: str
    t: list[int]
    items: dict[str, HDItem]
    # base_ability_count: int

@dataclass
class TalentEntry:
    name: str
    picked: bool

@dataclass
class TalentTree:
    entries: list[tuple[TalentEntry]]

    @staticmethod
    def from_parts(talents: list[str], picks: list[int]) -> 'TalentTree':
        entries: list[TalentEntry] = []
        for talent, picked in zip(talents, picks):
            entries.append(TalentEntry(name=talent, picked=bool(picked)))
        # TODO: these are backwards in the API!!
        # it returns 0, 1, 2, 3, .. where 0, 2, 4, 6 are RIGHT and 1,3,5,7 are LEFT
        list_of_groups = list(zip(*(iter(entries),) * 2))
        return TalentTree(entries=list_of_groups)

@dataclass
class ProcessdHeroData:
    n: str
    name: str
    talent_tree: TalentTree
    abilities: list[Ability]
    inventory: Inventory


@dataclass
class Playing:
    selected_hero: str
    selected_hero_data: HeroData

    def process_data(self, heroes, items) -> 'ProcessdHeroData':
        hero = heroes[self.selected_hero]
        talents = TalentTree.from_parts(hero.talents, self.selected_hero_data.t)
        inv = Inventory.from_parts(self.selected_hero_data.items, items)

        phd = ProcessdHeroData(hero.n, hero.name, talents, hero.abilities, inv)
        return phd


@dataclass
class CDNConfig:
    domain: str

    @staticmethod
    def default() -> "CDNConfig":
        return CDNConfig("dotatooltips.b-cdn.net")


@dataclass
class APIConfig:
    domain: str

    @staticmethod
    def default() -> "APIConfig":
        return APIConfig("tooltips.layerth.dev")


@dataclass
class Spectating:
    heroes: list[str]
    hero_data: dict[str, Any]


@dataclass
class APIError:
    pass


class DataType(enum.Enum):
    Items = enum.auto()
    Heroes = enum.auto()


class API:
    def __init__(self, cdn_config: Optional[CDNConfig] = None, api_config: Optional[APIConfig] = None):
        self.cdn_config = cdn_config or CDNConfig.default()
        self.api_config = api_config or APIConfig.default()

    async def _fetch_json(self, url) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            r.raise_for_status()
        return json.loads(r.text)

    async def fetch_items(self, language: str = "english") -> dict[str, Item]:
        items = await self._fetch_data_file(DataType.Items, language)
        ret = {}
        for k, v in items.items():
            if 'name' not in v:
                continue
            i = Item.from_dict(v)
            ret[k] = i
        return ret

    async def fetch_heroes(self, language: str = "english") -> dict[str, Hero]:
        heroes = await self._fetch_data_file(DataType.Heroes, language)
        ret = {}
        for k, v in heroes.items():
            if k == "npc_dota_hero_target_dummy":
                continue
            h = Hero.from_dict(v)
            ret[k] = h
        return ret

    async def _fetch_data_file(self, data_type: DataType, language: str = "english") -> dict:
        match data_type:
            case DataType.Items:
                type_ = "full-items"
            case DataType.Heroes:
                type_ = "full-heroes"
            case default:
                raise ValueError(f"Unsupported value {default}")
        url = f"https://{self.cdn_config.domain}/data/{language}/{type_}.json"
        return await self._fetch_json(url)

    async def get_stream_status(self, channel_id: int) -> Playing | APIError | Spectating:
        url = f"https://{self.api_config.domain}/data/pubsub/{channel_id}"
        data = await self._fetch_json(url)

        return API._from_json(data)

    @staticmethod
    def _from_json(data: dict) -> Playing | APIError | Spectating:
        assert not data["error"], "not implemented, error management"
        game = data["active_game"]
        state = game["gsi_state"]
        if state == "playing":
            return dacite.from_dict(data_class=Playing, data=game)
        elif state == "spectating":
            return dacite.from_dict(data_class=Spectating, data=game)

        raise ValueError(f"Unhandled state {state}")



class EnhancedJSONEncoder(json.JSONEncoder):
        def default(self, o):
            if dataclasses.is_dataclass(o):
                return dataclasses.asdict(o)
            return super().default(o)


if __name__ == "__main__":
    api = API()
    with Path("./data/playing-2.json").open() as fd:
        # with Path('./data/spectating.json').open() as fd:
        # with Path('./data/full-heroes.json').open() as fd:
        data = json.load(fd)

    heroes = api.fetch_heroes()
    items = api.fetch_items()
    game_state = api._from_json(data)
    match game_state:
        case Playing():
            phd = game_state.process_data(heroes, items)

            print(json.dumps(phd, cls=EnhancedJSONEncoder))
