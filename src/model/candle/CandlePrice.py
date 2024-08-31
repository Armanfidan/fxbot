from enum import Enum


class CandlePrice(Enum):
    OPEN: str = "o"
    HIGH: str = "h"
    LOW: str = "l"
    CLOSE: str = "c"
