"""Contains static data from the project files that is not really important and doesn't change often."""
from enum import Enum


class SpaceType(Enum):
    """Supported space types according to Specs from XSD."""

    BUILDING = "Building"
    BUILDING_PART = "BuildingPart"
    FLOOR = "Floor"
    ROOM = "Room"
    DISTRIBUTION_BOARD = "DistributionBoard"
    STAIRWAY = "Stairway"
    CORRIDOR = "Corridor"
    AREA = "Area"
    GROUND = "Ground"
    SEGMENT = "Segment"


MEDIUM_TYPES: dict[str, str] = {
    "MT-0": "Twisted Pair (TP)",
    "MT-1": "Powerline (PL)",
    "MT-2": "KNX RF (RF)",
    "MT-5": "KNXnet/IP (IP)",
}
