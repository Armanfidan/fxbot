from dataclasses import dataclass
from typing import Literal


@dataclass
class TakeProfitOrder:
    price: float
    timeInForce: Literal['GTC', 'GTD', 'GFD'] = 'GTC'
    gtdTime: str = None  # Specify if time in force is GTD.


@dataclass
class StopLossOrder:
    price: float = None
    distance: float = None  # Distance from the current price. Specify instead of price.
    timeInForce: Literal['GTC', 'GTD', 'GFD'] = 'GTC'
    gtdTime: str = None  # Specify if time in force is GTD.
    

@dataclass
class TrailingStopLossOrder:
    distance: float  # Distance from the current price.
    timeInForce: Literal['GTC', 'GTD', 'GFD'] = 'GTC'
    gtdTime: str = None  # Specify if time in force is GTD.
