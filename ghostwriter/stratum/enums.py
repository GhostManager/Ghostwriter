# Standard Libraries
from enum import Enum


class Severity(Enum):
    CRIT = "Critical"
    HIGH = "High"
    MED = "Medium"
    LOW = "Low"
    BP = "Best Practice"


class DifficultyExploitColor(Enum):
    LOW = (Severity.LOW.value, "#F0582B")
    MED = (Severity.MED.value, "#F6941F")
    HIGH = (Severity.HIGH.value, "#8BC53F")


class FindingStatusColor(Enum):
    OPEN = ("OPEN", "#F0582B")
    CLOSED = ("CLOSED", "#8BC53F")
    ACCEPTED = ("ACCEPTED", "#4E81BD")


def get_value_from_key(e, key):
    for item in e:
        if item.value[0].lower() == key.lower():
            return item.value[1]
    raise ValueError(f"{key} is not a valid {e.__name__} key")
