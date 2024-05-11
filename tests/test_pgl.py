import json
import pytest
from twitch_dota_extension.pgl import pgl_state_from_aiter
from twitch_dota_extension.lib import SpectatingPglTournament, API


# file => __aiter__
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


@pytest.mark.asyncio
async def test_parse_drafting():
    aiter = AiterF("data/pgl/pgl_drafting.txt")
    res = await pgl_state_from_aiter(aiter)
    assert res is None


@pytest.mark.asyncio
async def test_parse_playing():
    aiter = AiterF("data/pgl/pgl_playing.txt")
    res = await pgl_state_from_aiter(aiter)
    assert res is not None
    assert [h["name"] for h in res.HeroList] == [
        "enchantress",
        "zuus",
        "pangolier",
        "earthshaker",
        "drow_ranger",
        "mirana",
        "doom_bringer",
        "ember_spirit",
        "bounty_hunter",
        "luna",
    ]
    assert [h["name"] for h in res.PlayerStats] == [
        "Dy",
        "Xm",
        "Xxs",
        "XinQ",
        "Ame^^",
        "Insania",
        "33",
        "Nisha",
        "Boxi",
        "m1CKe",
    ]

    assert res.Inventory[0] == {
        "main": [
            "item_gem",
            "item_ward_sentry",
            "item_eternal_shroud",
            "item_power_treads",
            "item_magic_wand",
            "item_wraith_band",
        ],
        "backpack": ["empty", "empty", "empty"],
        "neutral": "item_enchanted_quiver",
        "special_items": {"cheese": 0, "refresher_shard": 0, "divine_rapier": 0},
    }

@pytest.mark.asyncio
async def test_process_playing():
    aiter = AiterF("data/pgl/pgl_playing.txt")
    parsed = await pgl_state_from_aiter(aiter)
    assert parsed is not None
    api = API()
    raw_heroes = json.load(open('data/pgl/heroes.json'))
    hero_map = api._map_pgl_hero_names(raw_heroes)

    heroes = api._process_heroes(json.load(open('data/full-heroes.json')))
    items = api._process_items(json.load(open('data/full-items.json')))

    res = SpectatingPglTournament(parsed).process_data(heroes, hero_map, items)
    assert res is not None
