from dataclasses import dataclass
from enum import Enum


class InjuryCategory(Enum):
    INJURY = 'injuries'
    FATALITY = 'fatalities'
    OTHER = 'others'


@dataclass
class Injury:
    severity: int
    category: InjuryCategory
    description: str


class InjuryType(Enum):
    NO_INJURY = Injury(severity=0,
                       category=InjuryCategory.OTHER,
                       description='Injury')
    INJURY = Injury(severity=50,
                    category=InjuryCategory.INJURY,
                    description='Injury')
    FATALITY = Injury(severity=100,
                      category=InjuryCategory.FATALITY,
                      description='Fatality')
    OTHER = Injury(severity=0,
                   category=InjuryCategory.OTHER,
                   description='Other')


@dataclass
class Person:
    vulnerability: int
    description: str


class PersonType(Enum):
    DRIVER = Person(vulnerability=0, description='Driver')
    OCCUPANT = Person(vulnerability=50, description='Occupant')
    PEDESTRIAN = Person(vulnerability=100, description='Pedestrian')


UNKNOWN = 'unknown'
