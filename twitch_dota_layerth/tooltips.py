from dataclasses import dataclass
from typing import Optional

@dataclass
class Property:
    name: str
    value: list[str] | str

@dataclass
class Tooltip:
    Description: Optional[str]
    #Lore: str
    #AbilityBehavior: str
    #AbilityCooldown: str
    #AbilityManaCost: str
    notes: Optional[list[str]]
    attributes: Optional[list[str]]  # abilitycastrange, duration, etc
    properties: Optional[list[Property]]

@dataclass
class Ability:
    #n: str
    name: str
    tooltips: Tooltip
    properties: list[Property]
    #AbilityBehavior: str
    #SpellImmunityType: str
    #AbilityUnitDamageType: str
    #AbilityCooldown: str = ""
    #AbilityManaCost: str = ""
    #AbilityCastRange: str = ""
    #AbilityUnitTargetTeam: str = ""
    #AbilityUnitTargetType: str = ""
    #IsGrantedByScepter: str = ""
    #HasScepterUpgrade: str = ""
    #IsGrantedByShard: str = ""

@dataclass
class Talent:
    name: str
    #id: str

@dataclass
class Hero:
    n: str
    #HeroID: str
    Name: str
    #Role: str
    #Short: str
    #HeroGlowColor: str
    #ArmorPhysical: str
    #AttackDamageMin: str
    #AttackDamageMax: str
    #AttributePrimary: str
    #AttributeBaseStrength: str
    #AttributeStrengthGain: str
    #AttributeBaseIntelligence: str
    #AttributeIntelligenceGain: str
    #AttributeBaseAgility: str
    #AttributeAgilityGain: str
    #MovementSpeed: str
    abilities: list[Ability]
    talents: dict[str, Talent]
