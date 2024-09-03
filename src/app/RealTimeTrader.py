import json
from datetime import datetime
from typing import Dict

import pika
from pandas import DataFrame

from src.client.OandaDataClient import OandaDataClient
from src.client.OandaOrderClient import OandaOrderClient
from src.service.signal_generators.SignalGenerator import SignalGenerator
from src.model.Granularity import Granularity
from src.model.Indicator import Indicator


class LiveTrader:
    def __init__(self, pair: str, indicator: Indicator, granularity: Granularity, live: bool, historical_data_start_time: datetime, order_units: int, indicator_params: Dict | None = None):
        print("Initializing LiveTrader for pair {}, indicator {} and granularity {}.".format(pair, indicator, granularity))
        print("Collecting initial data from {}.".format(historical_data_start_time.strftime("%Y-%m-%d %H:%M:%S")))
        print("############# CAUTION: TRADING LIVE. #############" if live else "Demo trading mode.")
        if indicator_params is None:
            indicator_params = {}
        self.indicator_params: Dict = indicator_params
        self.order_units: int = order_units
        self.pair: str = pair
        self.indicator: Indicator = indicator
        self.granularity: Granularity = granularity
        self.data_client: OandaDataClient = OandaDataClient(live=live)
        self.historical_data_start_time: datetime = historical_data_start_time
        self.candles: DataFrame = self._get_initial_price_data()
        pip_location: float = OandaDataClient.get_pip_location(pair)
        self.signal_generator: SignalGenerator = SignalGenerator(pair, pip_location, granularity, self.candles)
        self.signal_generator.generate_signals_for_backtesting(use_pips=True, **self.indicator_params)

        self.order_client: OandaOrderClient = OandaOrderClient(live=live)

    def _get_initial_price_data(self) -> DataFrame:
        return self.data_client.create_data_for_pair(self.pair, self.granularity, self.historical_data_start_time, datetime.now())

    def consume_candle(self, _, __, ___, body):
        print("Candle consumed: {}".format(body))
        candle_dict: Dict[str, float | datetime] = json.loads(body)
        candle_dict['volume'] = 1
        self.candles.loc[-1] = candle_dict
        self.candles = self.candles.iloc[1:]
        self.candles.reset_index(inplace=True)
        # TODO: Add support for limit orders and stop orders
        self.order_client.place_market_order(self.pair, self.order_units, 'FOK', 1)

    def iterate(self):
        pass

    def start(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel_name: str = '{}_LIVE_CANDLES'.format(self.pair)
        channel.basic_consume(queue=channel_name,
                              auto_ack=True,
                              on_message_callback=self.consume_candle)
        print('Listening for new candles on channel: {}'.format(channel_name))
        channel.start_consuming()
