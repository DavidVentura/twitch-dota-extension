from dataclasses import dataclass
from typing import Optional

# https://dotatooltips.b-cdn.net/items/{item}_png.png
# https://dotatooltips.b-cdn.net/heroes/{hero}_png.png
# https://cdn.steamstatic.com/apps/dota2/images/heroes/faceless_void_vert.jpg
# https://courier.spectral.gg/images/dota/spellicons/faceless_void_time_walk.png

@dataclass
class Node:
    tag: str
    val: str

def markup_to_nodes(s: str) -> list[Node]:
    ret = []
    cur = 0

    s = s.replace("[object Object]", "UNKNOWN")
    cur_tag = None
    cur_val = ""
    closing = ''
    while cur < len(s):
        char = s[cur]
        if char == '<':
            matched_open = True
            closing = '>'
        elif char == '[':
            matched_open = True
            closing = ']'
        else:
            matched_open = False

        if matched_open:
            tag, _, _ = s[cur+1:].partition(closing)
            if tag.endswith('/'): # <br/>
                if cur_val:
                    ret.append(Node(cur_tag or 'text', cur_val.strip()))
                ret.append(Node('newline', ''))
            elif tag.startswith('/'):
                assert cur_tag is not None
                ret.append(Node(cur_tag, cur_val.strip()))
                cur_val = ""
                cur_tag = None
            else:
                if cur_val:
                    # text nodes between tags
                    ret.append(Node('text', cur_val.strip()))
                assert cur_tag is None, s
                cur_tag = tag
                cur_val = ""
            cur = cur + len(tag) + 2
            continue
        if char == '\\' and s[cur:cur+2] == '\\n':
            cur += 2
            if cur_val:
                ret.append(Node(cur_tag or 'text', cur_val.strip()))
            ret.append(Node('newline', ''))
            cur_val = ""
            cur_tag = None
            continue
        cur_val += char
        cur += 1

    if cur_val:
        ret.append(Node(cur_tag or 'text', cur_val.strip()))

    return ret

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
    granted_by_scepter: bool
    granted_by_shard: bool
    innate: bool
    properties: list[Property]

    @staticmethod
    def from_dict(d: dict) -> "Ability":
        return Ability(
            name=d["name"],
            n=d["n"],
            tooltip=Tooltip.from_dict(d["tooltips"]),
            has_scepter_upgrade=d.get("HasScepterUpgrade") == "1",
            has_shard_upgrade=d.get("HasShardUpgrade") == "1",
            granted_by_scepter=d.get("IsGrantedByScepter") == "1",
            granted_by_shard=d.get("IsGrantedByShard") == "1",
            innate=d.get("Innate") == "1",
            properties=[Property.from_dict(p) for p in d["properties"]],
        )


@dataclass
class Facet:
    facet_id: int
    icon: str
    color: str
    n: str
    title: str
    description: str

    @staticmethod
    def from_dict(fid: int, d: dict) -> "Facet":
        return Facet(facet_id=int(fid),
                     icon=d["Icon"],
                     color=d["Color"],
                     n=d["n"],
                     title=d["tooltip"].get("title", "NO TITLE"),
                     description=d["tooltip"].get("description", "NO DESC")
                     )

@dataclass
class Hero:
    n: str
    name: str
    abilities: list[Ability]
    talents: list[str]
    facets: list[Facet]

    @staticmethod
    def from_dict(d: dict) -> "Hero":
        return Hero(
            n=d["n"],
            name=d["Name"],
            abilities=[Ability.from_dict(a) for a in d["abilities"]],
            talents=flatten_talents(d["talents"]),
            facets=[Facet.from_dict(fid, f) for fid, f in d["facets"].items()],
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
    cooldown: Optional[str]
    manacost: Optional[str]
    cost: Optional[str]
    description: list[Node]
    active: list[Node]
    use: list[Node]
    passive: list[Node]
    properties: dict[str, str]

    @staticmethod
    def from_dict(d: dict) -> "Item":
        return Item(
            n=d["n"],
            name=d["name"],
            active=markup_to_nodes(d.get("active", "")),
            use=markup_to_nodes(d.get("use", "")),
            passive=markup_to_nodes(d.get("passive", "")),
            description=markup_to_nodes(d.get("tooltips", {}).get("Description", "")),
            cooldown=d.get("AbilityCooldown"),
            manacost=d.get("AbilityManaCost"),
            cost=d.get("ItemCost"),
            properties={prop['name']: prop['value'] for prop in d.get('properties', [])},
        )
