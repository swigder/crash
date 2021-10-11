from dataclasses import dataclass
from enum import Enum


class CrashCategory(Enum):
    MOTOR_VEHICLE = 'car'
    BICYCLE = 'bike'
    PEDESTRIAN = 'ped'
    OTHER = 'other'


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
    NO_INJURY = Injury(severity=0, category=InjuryCategory.OTHER, description='Injury')
    INJURY = Injury(severity=50, category=InjuryCategory.INJURY, description='Injury')
    FATALITY = Injury(severity=100, category=InjuryCategory.FATALITY, description='Fatality')
    OTHER = Injury(severity=0, category=InjuryCategory.OTHER, description='Other')


@dataclass
class Person:
    vulnerability: int
    description: str
    category: CrashCategory


class PersonType(Enum):
    BICYCLIST = Person(vulnerability=75, description='Bicyclist', category=CrashCategory.BICYCLE)
    DRIVER = Person(vulnerability=0, description='Driver', category=CrashCategory.MOTOR_VEHICLE)
    OCCUPANT = Person(vulnerability=50, description='Occupant', category=CrashCategory.MOTOR_VEHICLE)
    PEDESTRIAN = Person(vulnerability=100, description='Pedestrian', category=CrashCategory.PEDESTRIAN)
    OTHER = Person(vulnerability=-5, description='Other', category=CrashCategory.OTHER)


UNKNOWN = 'unknown'
