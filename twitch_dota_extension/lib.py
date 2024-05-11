import enum
import json
from dataclasses import dataclass
from typing import Optional, Any

import dacite
import httpx
from twitch_dota_extension.pgl import PGLGameState

from twitch_dota_extension.tooltips import Hero, Ability, Item


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
    t: list[int]
    items: dict[str, HDItem]
    # base_ability_count: int

@dataclass
class TournamentHeroData(HeroData):
    p: str
    lvl: int
    aghs: list[int]

@dataclass
class TalentEntry:
    name: str
    picked: bool

@dataclass
class TalentTree:
    entries: list[tuple[TalentEntry, TalentEntry]]

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
class ProcessedHeroData:
    n: str
    name: str
    talent_tree: TalentTree
    abilities: list[Ability]
    inventory: Inventory

@dataclass
class TourProcessedHeroData(ProcessedHeroData):
    player: Optional[str] = None
    level: Optional[int] = None
    has_aghs: Optional[bool] = False
    has_shard: Optional[bool] = False


@dataclass
class Playing:
    selected_hero: str
    selected_hero_data: HeroData

    def process_data(self, heroes: dict[str, Hero], items) -> ProcessedHeroData:
        hero = heroes[self.selected_hero]
        talents = TalentTree.from_parts(hero.talents, self.selected_hero_data.t)
        inv = Inventory.from_parts(self.selected_hero_data.items, items)

        phd = ProcessedHeroData(hero.n, hero.name, talents, hero.abilities, inv)
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
    tour_domain: str

    @staticmethod
    def default() -> "APIConfig":
        return APIConfig("tooltips.layerth.dev", "tour-tooltips.layerth.dev")


@dataclass
class Spectating:
    heroes: list[str]
    hero_data: dict[str, HeroData]


@dataclass
class SpectatingTournament:
    hero_data: dict[str, TournamentHeroData]

    def process_data(self, heroes: dict[str, Hero], items) -> list[TourProcessedHeroData]:
        ret = []
        for hero_name, hero_state in self.hero_data.items():
            hero = heroes[hero_name]
            talents = TalentTree.from_parts(hero.talents, hero_state.t)
            inv = Inventory.from_parts(hero_state.items, items)

            phd = TourProcessedHeroData(hero.n, hero.name, talents, hero.abilities, inv,
                                    player=hero_state.p, level=hero_state.lvl,
                                    has_aghs=bool(hero_state.aghs[0]), has_shard=bool(hero_state.aghs[1]))
            ret.append(phd)
        return ret


@dataclass
class SpectatingPglTournament:
    data: PGLGameState

    def process_data(self, heroes: dict[str, Hero], hero_map: dict[str, str], items: dict[str, Any]) -> list[TourProcessedHeroData]:
        ret = []
        for hero_meta in self.data.HeroList:
            hero_name = hero_map[hero_meta['name']]
            idx = hero_meta['index']

            _herod = self.data.Heroes[idx]
            _pstatsd = self.data.PlayerStats[idx]
            _invd = self.data.Inventory[idx]

            t = [int(_herod[f'talent_{i}']) for i in range(1, 9)]

            hero = heroes[hero_name]
            talents = TalentTree.from_parts(hero.talents, t)
            inv = Inventory([items[name] for name in _invd['main'] if name != 'empty'], items[_invd['neutral']] if _invd['neutral'] != 'empty' else None)

            phd = TourProcessedHeroData(hero.n, hero.name, talents, hero.abilities, inv,
                                    player=_pstatsd['name'], level=_herod['level'],
                                    has_aghs=_herod['aghanims_scepter'], has_shard=_herod['aghanims_shard'])
            ret.append(phd)
        return ret

@dataclass
class InvalidResponse:
    r: dict[str, Any]


@dataclass
class APIError:
    error: str


class DataType(enum.Enum):
    Items = enum.auto()
    Heroes = enum.auto()


class API:
    def __init__(self, cdn_config: Optional[CDNConfig] = None, api_config: Optional[APIConfig] = None):
        self.cdn_config = cdn_config or CDNConfig.default()
        self.api_config = api_config or APIConfig.default()

    async def fetch_pgl_hero_mappings(self) -> dict[str, str]:
        url = 'https://dota2-data.pglesports.com/static/heroes.json'
        data = await self._fetch_json(url)
        return {k: v['data_name'] for k, v in data.items()}

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

    async def get_stream_status(self, channel_id: int) -> Playing | APIError | Spectating | SpectatingTournament  | SpectatingPglTournament| InvalidResponse:
        # TODO: parallel? though unlikely to be the 2nd/3rd
        # maybe return meta so client can cache type?
        NOT_AVAIL = "Channel not found. It might take a few minutes for the channel to appear."
        url = f"https://{self.api_config.domain}/data/pubsub/{channel_id}"
        data = await self._fetch_json(url)

        if data.get('error') == NOT_AVAIL:
            print("Attempting to fetch from tournament domain")
            url_tour = f"https://{self.api_config.tour_domain}/data/pubsub/{channel_id}"
            data = await self._fetch_json(url_tour)

        if data.get('error') == NOT_AVAIL:
            print("Attempting to fetch from PGL domain")
            pgs = await PGLGameState.from_stream(channel_id)
            if pgs is not None:
                return SpectatingPglTournament(pgs)

        r = API._from_json(data)
        return r

    @staticmethod
    def _from_json(data: dict) -> Playing | APIError | Spectating | SpectatingTournament | InvalidResponse:
        error = data.get("error")
        if error:
            return APIError(error)
        game = data.get("active_game", {})
        state = game.get("gsi_state", "unpopulated in API")

        if state == "playing":
            return dacite.from_dict(data_class=Playing, data=game)
        elif state == "spectating" and game.get('matchid'):  # Tournament
            return dacite.from_dict(data_class=SpectatingTournament, data=game)
        elif state == "spectating":
            return dacite.from_dict(data_class=Spectating, data=game)

        return InvalidResponse(r=data)
