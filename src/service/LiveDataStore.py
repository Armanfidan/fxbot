from datetime import datetime
from time import sleep
from typing import Dict

import pika

from Candle import Candle
from CandleGenerator import CandleGenerator
from Granularity import Granularity
from Price import Price
from client.DataClient import DataClient


class LiveDataStore:
    def __init__(self, pair: str, candlestick_granularity: Granularity, price_granularity: Granularity):
        print("Initialising LiveDataStore for pair {}, candlestick granularity {} and price granularity {}".format(pair, candlestick_granularity.name, price_granularity.name))
        self.pair: str = pair
        self.candlestick_granularity: Granularity = candlestick_granularity
        self.price_granularity: Granularity = price_granularity

        self.data_client: DataClient = DataClient(live=True)
        self.candle_generator: CandleGenerator = CandleGenerator(pair, candlestick_granularity)

        self.connection: pika.BlockingConnection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel: pika.adapters.blocking_connection.BlockingChannel = self.connection.channel()
        self.channel_name: str = '{}_LIVE_CANDLES'.format(self.pair)
        self.channel.queue_declare(queue=self.channel_name)
        print("Created queue {}".format(self.channel_name))

    def get_channel_name(self) -> str:
        return self.channel_name

    def publish_candle(self):
        price: Price = Price.from_dict(self.data_client.get_price(self.pair))
        candle: Candle = self.candle_generator.generate(price)
        if candle:
            self.channel.basic_publish(exchange='', routing_key=self.channel_name, body=str(candle))
            print("{}: Candle published, timestamp: {}".format(self.pair, candle.time.strftime("%Y-%m-%d %H:%M:%S")))
        else:
            print("No candle yet. Price: {}".format(price))

    def start(self):
        try:
            while True:
                sleep(self.price_granularity.value.total_seconds())
                self.publish_candle()
        except KeyboardInterrupt:
            self.connection.close()
            print("Stopped LiveDataStore.")
            exit(1)
