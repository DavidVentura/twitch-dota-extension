import enum
import json
from dataclasses import dataclass
from typing import Optional, Any
from pathlib import Path

import dacite
import requests

from twitch_dota_layerth.tooltips import Hero

@dataclass
class Ability:
    name: str

@dataclass
class Item:
    name: str

@dataclass
class HeroData:
    name: str
    t: list[int]
    abilities: dict[str, Ability]
    items: dict[str, Item]
    base_ability_count: int

@dataclass
class Playing:
    selected_hero: str
    selected_hero_data: HeroData

@dataclass
class CDNConfig:
    domain: str

    @staticmethod
    def default() -> 'CDNConfig':
        return CDNConfig("dotatooltips.b-cdn.net")

@dataclass
class APIConfig:
    domain: str

    @staticmethod
    def default() -> 'APIConfig':
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

    def fetch_items(self, language: str = 'english') -> dict:
        items = self._fetch_data_file(DataType.Items, language)
        return {}

    def fetch_heroes(self, language: str = 'english') -> list[Hero]:
        heroes = self._fetch_data_file(DataType.Heroes, language)
        ret = []
        for k, v in heroes.items():
            if k == 'npc_dota_hero_target_dummy': continue
            ret.append(dacite.from_dict(data_class=Hero, data=v))
        return ret

    def _fetch_data_file(self, data_type: DataType, language: str = 'english') -> dict:
        match data_type:
            case DataType.Items:
                type_ = 'full-items'
            case DataType.Heroes:
                type_ = 'full-heroes'
            case default:
                raise ValueError(f'Unsupported value {default}')
        url = f'https://{self.cdn_config.domain}/data/{language}/{type_}.json'
        r = requests.get(url)
        r.raise_for_status()
        return json.loads(r.text)

    def get_stream_status(self, channel_id: int) -> Playing | APIError | Spectating:
        url = f'https://{self.api_config.domain}/data/pubsub/{channel_id}'
        r = requests.get(url)
        r.raise_for_status()
        data = json.loads(r.text)

        return API._from_json(data)

    @staticmethod
    def _from_json(data: dict) -> Playing | APIError | Spectating:
        assert not data['error'], "not implemented, error management"
        game = data['active_game']
        state = game['gsi_state']
        if state == 'playing':
            return dacite.from_dict(data_class=Playing, data=game)
        elif state == 'spectating':
            return dacite.from_dict(data_class=Spectating, data=game)

        raise ValueError(f"Unhandled state {state}")

api = API()
with Path('./data/playing-2.json').open() as fd:
#with Path('./data/spectating.json').open() as fd:
#with Path('./data/full-heroes.json').open() as fd:
    data = json.load(fd)

print(api.fetch_heroes())
print(api._from_json(data))
#from pprint import pprint
#for k, v in data.items():
#    print(k)
#    pprint(dacite.from_dict(data_class=Hero, data=v))
#    break

#d = api.get_stream_status(108268890)
#with Path('./data/playing-2.json').open('w') as fd:
#    json.dump(d, fd)
