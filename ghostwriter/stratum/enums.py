# Standard Libraries
from enum import Enum


class Severity(Enum):
    CRIT = "Critical"
    HIGH = "High"
    MED = "Medium"
    LOW = "Low"
    BP = "Best Practice"


class DifficultyExploitColor(Enum):
    LOW = (Severity.LOW.value, "#FF0000")
    MED = (Severity.MED.value, "#ED9146")
    HIGH = (Severity.HIGH.value, "#16A43E")


class FindingStatusColor(Enum):
    OPEN = ("OPEN", "#FF0000")
    CLOSED = ("CLOSED", "#16A43E")
    ACCEPTED = ("ACCEPTED", "#0C5AB2")


def get_value_from_key(e, key):
    for item in e:
        if item.value[0].lower() == key.lower():
            return item.value[1]
    raise ValueError(f"{key} is not a valid {e.__name__} key")
