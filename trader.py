from datetime import datetime
from http.client import HTTPException
from typing import Tuple, List

import v20
import pandas as pd
from pandas import DataFrame

import constants
from order import TakeProfitOrder, StopLossOrder, TrailingStopLossOrder

MAX_CANDLESTICKS: int = 5000


class Trader:
    def __init__(self):
        self.api = v20.Context(
            hostname=constants.OANDA_HOSTNAME,
            token=constants.OANDA_API_KEY,
            datetime_format='UNIX'
        )

    def place_market_order(self, pair: str, units: int, time_in_force: str, price_bound: float, take_profit_on_fill: TakeProfitOrder = None, stop_loss_on_fill: StopLossOrder = None, trailing_stop_loss_on_fill: TrailingStopLossOrder = None) -> Tuple[DataFrame, datetime]:

        response: v20.response = self.api.order.market(constants.OANDA_ACCOUNT_ID,
                                                       instrument=pair,
                                                       units=units,
                                                       timeInForce=time_in_force,
                                                       priceBound=price_bound,
                                                       takeProfitOnFill=vars(take_profit_on_fill),
                                                       stopLossOnFill=vars(stop_loss_on_fill),
                                                       trailingStopLossOnFill=vars(trailing_stop_loss_on_fill))
        if response.status != 200:
            raise HTTPException(
                "Could not place a market order for pair {}. status code: {}, error message: {}".format(pair, response.status, response.body.errorMessage))
        print(response.body)
