import sys
from enum import Enum


class ArtistTiers(Enum):
    TIER_1 = 50000
    TIER_2 = 500000
    TIER_3 = 1000000
    TIER_4 = 5000000
    TIER_5 = 8000000
    TIER_6 = sys.maxsize
