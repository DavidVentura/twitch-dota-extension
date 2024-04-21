from dataclasses import dataclass
from typing import Optional

# https://dotatooltips.b-cdn.net/items/{item}_png.png
# https://dotatooltips.b-cdn.net/heroes/{hero}_png.png
# https://cdn.steamstatic.com/apps/dota2/images/heroes/faceless_void_vert.jpg
# https://courier.spectral.gg/images/dota/spellicons/faceless_void_time_walk.png

@dataclass
class Property:
    name: str
    value: list[str] | str

    @staticmethod
    def from_dict(d: dict) -> "Property":
        value = d["value"]
        if isinstance(d["value"], str):
            value = [v.strip() for v in value.split("|")]
            d["value"] = value
        return Property(name=d["name"], value=value)


@dataclass
class Tooltip:
    description: Optional[str]
    lore: Optional[str]
    scepter_description: Optional[str]

    @staticmethod
    def from_dict(d: dict) -> "Tooltip":
        return Tooltip(
            scepter_description=d.get("scepter_description"),
            description=d.get("Description"),
            lore=d.get("Lore"),
        )


@dataclass
class Ability:
    name: str
    n: str
    tooltip: Tooltip
    has_scepter_upgrade: bool
    has_shard_upgrade: bool
    properties: list[Property]

    @staticmethod
    def from_dict(d: dict) -> "Ability":
        return Ability(
            name=d["name"],
            n=d["n"],
            tooltip=Tooltip.from_dict(d["tooltips"]),
            has_scepter_upgrade=d.get("HasScepterUpgrade") == "1",
            has_shard_upgrade=d.get("HasShardUpgrade") == "1",
            properties=[Property.from_dict(p) for p in d["properties"]],
        )


@dataclass
class Hero:
    n: str
    name: str
    abilities: list[Ability]
    talents: list[str]

    @staticmethod
    def from_dict(d: dict) -> "Hero":
        return Hero(
            n=d["n"],
            name=d["Name"],
            abilities=[Ability.from_dict(a) for a in d["abilities"]],
            talents=flatten_talents(d["talents"]),
        )


def flatten_talents(d: dict) -> list:
    ret = []
    for v in d.values():
        ret.append(v["name"])
    return ret


@dataclass
class Item:
    n: str
    name: str
    active: Optional[str]
    cooldown: Optional[str]
    manacost: Optional[str]
    use: Optional[str]

    @staticmethod
    def from_dict(d: dict) -> "Item":
        return Item(
            n=d["n"],
            name=d["name"],
            active=d.get("active"),
            cooldown=d.get("AbilityCooldown"),
            manacost=d.get("AbilityManaCost"),
            use=d.get("use"),
        )
