from http.client import HTTPException
from typing import Literal

import v20

from Constants import OANDA_DEMO_HOSTNAME, OANDA_LIVE_HOSTNAME, OANDA_DEMO_API_KEY, OANDA_LIVE_API_KEY, OANDA_DEMO_ACCOUNT_ID, OANDA_LIVE_ACCOUNT_ID
from Order import TakeProfitOrder, StopLossOrder, TrailingStopLossOrder

MAX_CANDLESTICKS: int = 5000


class OrderClient:
    def __init__(self, live: bool):
        self.live: bool = live
        self.api = v20.Context(
            hostname=OANDA_LIVE_HOSTNAME if live else OANDA_DEMO_HOSTNAME,
            token=OANDA_LIVE_API_KEY if live else OANDA_DEMO_API_KEY,
            datetime_format='UNIX'
        )

    def place_market_order(self, pair: str, units: int, time_in_force: Literal['FOK', 'GTC', 'GTD', 'GFD', 'MOO', 'LOO', 'IOC', 'DTC'], price_bound: float, take_profit_on_fill: TakeProfitOrder = None, stop_loss_on_fill: StopLossOrder = None, trailing_stop_loss_on_fill: TrailingStopLossOrder = None):
        response: v20.response = self.api.order.market(OANDA_LIVE_ACCOUNT_ID if self.live else OANDA_DEMO_ACCOUNT_ID,
                                                       instrument=pair,
                                                       units=units,
                                                       timeInForce=time_in_force,
                                                       priceBound=price_bound,
                                                       takeProfitOnFill=vars(take_profit_on_fill) if take_profit_on_fill else None,
                                                       stopLossOnFill=vars(stop_loss_on_fill) if stop_loss_on_fill else None,
                                                       trailingStopLossOnFill=vars(trailing_stop_loss_on_fill) if trailing_stop_loss_on_fill else None)
        if response.status != 201:
            raise HTTPException(
                "Could not place a market order for pair {}. status code: {}, error message: {}".format(pair, response.status, response.body.errorMessage))
        print(response.body)
