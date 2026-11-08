from http.client import HTTPException
from typing import Literal

import v20

from src.util.Constants import OANDA_DEMO_HOSTNAME, OANDA_LIVE_HOSTNAME, get_oanda_credentials
from src.model.Order import TakeProfitOrder, StopLossOrder, TrailingStopLossOrder

MAX_CANDLESTICKS: int = 5000


class OandaOrderClient:
    def __init__(self, live: bool):
        self.live: bool = live
        token, self.account_id = get_oanda_credentials(live)
        self.api = v20.Context(
            hostname=OANDA_LIVE_HOSTNAME if live else OANDA_DEMO_HOSTNAME,
            token=token,
            datetime_format='UNIX'
        )

    def place_market_order(self, pair: str, units: int, time_in_force: Literal['FOK', 'GTC', 'GTD', 'GFD', 'MOO', 'LOO', 'IOC', 'DTC'], price_bound: float, take_profit_on_fill: TakeProfitOrder = None, stop_loss_on_fill: StopLossOrder = None, trailing_stop_loss_on_fill: TrailingStopLossOrder = None):
        response: v20.response = self.api.order.market(self.account_id,
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
