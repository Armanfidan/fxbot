import json
from datetime import datetime
from typing import Dict

import pika
from pandas import DataFrame

from DataClient import DataClient
from Granularity import Granularity
from OrderClient import OrderClient
from SignalGenerator import SignalGenerator
from Strategy import Strategy


class LiveTrader:
    def __init__(self, pair: str, strategy: Strategy, granularity: Granularity, live: bool, historical_data_start_time: datetime, order_units: int, strategy_params: Dict | None = None):
        print("Initializing LiveTrader for pair {}, strategy {} and granularity {}.".format(pair, strategy, granularity))
        print("Collecting initial data from {}.".format(historical_data_start_time.strftime("%Y-%m-%d %H:%M:%S")))
        print("############# CAUTION: TRADING LIVE. #############" if live else "Demo trading mode.")
        if strategy_params is None:
            strategy_params = {}
        self.strategy_params: Dict = strategy_params
        self.order_units: int = order_units
        self.pair: str = pair
        self.strategy: Strategy = strategy
        self.granularity: Granularity = granularity
        self.data_client: DataClient = DataClient(live=live)
        self.historical_data_start_time: datetime = historical_data_start_time
        self.candles: DataFrame = self._get_initial_price_data()
        pip_location: float = DataClient.get_pip_location(pair)
        self.signal_generator: SignalGenerator = SignalGenerator(pair, pip_location, granularity, self.candles, strategy)
        self.signal_generator.generate_signals(use_pips=True, **self.strategy_params)

        self.order_client: OrderClient = OrderClient(live=live)

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
