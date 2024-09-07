import os
from datetime import datetime
from typing import Any, Dict, Tuple

import pandas as pd
import pytest
from pandas import DataFrame

from src.model.Granularity import Granularity
from src.model.candle.Candle import Candle
from src.service.signal_generators.MovingAverageCrossoverSignalGenerator import MovingAverageCrossoverSignalGenerator
from src.model.signal_generator_iterations.MovingAverageCrossoverIteration import MovingAverageCrossoverIteration
from src.util.Constants import CURRENT_PROJECT_ROOT

CANDLE_DATA_FILE = '{}/test/resources/candle_data.csv'.format(CURRENT_PROJECT_ROOT)


@pytest.fixture
def signal_generator_params():
    yield {
        'pair': "EUR_USD",
        'pip_location': -4,
        'granularity': Granularity.S5,
        'short_window': 16,
        'long_window': 64
    }


@pytest.fixture
def candle_data(signal_generator_params):
    historical_data: DataFrame = pd.read_csv(CANDLE_DATA_FILE)
    initial_data: DataFrame = historical_data.iloc[:signal_generator_params['long_window']]
    new_data: DataFrame = historical_data.iloc[signal_generator_params['long_window']:]
    yield initial_data, new_data


class TestMovingAverageCrossoverSignalGenerator:
    def test_should_not_generate_signal_when_queue_is_empty(self, signal_generator_params: Dict[str, Any]):
        signal_generator = MovingAverageCrossoverSignalGenerator(**signal_generator_params, initial_candles=None)
        signal = signal_generator.generate_signal()
        assert signal == 0

    def test_candles_queue_gets_populated_from_df(self, signal_generator_params: Dict[str, Any],
                                                  candle_data: Tuple[DataFrame, DataFrame]):
        initial_data, _ = candle_data
        signal_generator = MovingAverageCrossoverSignalGenerator(**signal_generator_params,
                                                                 initial_candles=initial_data)
        assert len(signal_generator.queue) == initial_data.shape[0]
        assert signal_generator.queue[-1].candle.time == initial_data.iloc[-1]['time']

    def test_should_generate_buy_signal(self, signal_generator_params):
        signal_generator = MovingAverageCrossoverSignalGenerator(**signal_generator_params, initial_candles=None)
        # Make sure that the candle queues are not empty
        signal_generator.short_candles_queue.append(Candle(datetime.now()))
        signal_generator.long_candles_queue.append(Candle(datetime.now()))
        # In the previous iteration, the long average was above the short average.
        signal_generator.queue.append(MovingAverageCrossoverIteration(Candle(datetime.now()), short_average=-1, long_average=0, signal=0))
        # Currently, short average has passed the long average. Should trigger a buy signal.
        signal_generator.current_short_average = 1
        signal_generator.current_long_average = 0
        assert signal_generator.generate_signal() == 1

    def test_should_generate_sell_signal(self, signal_generator_params):
        signal_generator = MovingAverageCrossoverSignalGenerator(**signal_generator_params, initial_candles=None)
        # Make sure that the candle queues are not empty
        signal_generator.short_candles_queue.append(Candle(datetime.now()))
        signal_generator.long_candles_queue.append(Candle(datetime.now()))
        # In the previous iteration, the long average was above the short average.
        signal_generator.queue.append(MovingAverageCrossoverIteration(Candle(datetime.now()), short_average=-1, long_average=0, signal=0))
        signal_generator.current_short_average = 1
        signal_generator.current_long_average = 0
        # Now the short is above the long. Should trigger a buy signal.
        signal_generator.generate_signal()
        # In the previous iteration, the long average got below the short average.
        signal_generator.queue.append(MovingAverageCrossoverIteration(Candle(datetime.now()), short_average=1, long_average=0, signal=0))
        # Currently, short average has gone below the long average. Should trigger a sell signal.
        signal_generator.current_short_average = -1
        signal_generator.current_long_average = 0
        assert signal_generator.generate_signal() == -1

    def test_first_signal_should_not_be_a_sell_signal(self, signal_generator_params):
        signal_generator = MovingAverageCrossoverSignalGenerator(**signal_generator_params, initial_candles=None)
        # Make sure that the candle queues are not empty
        signal_generator.short_candles_queue.append(Candle(datetime.now()))
        signal_generator.long_candles_queue.append(Candle(datetime.now()))
        # In the previous iteration, the long average was below the short average.
        signal_generator.queue.append(MovingAverageCrossoverIteration(Candle(datetime.now()), short_average=1, long_average=0, signal=0))
        # Currently, short average has gone below the long average. Should trigger a sell signal.
        signal_generator.current_short_average = -1
        signal_generator.current_long_average = 0
        assert signal_generator.generate_signal() == 0

    def test_should_not_generate_signal(self, signal_generator_params):
        signal_generator = MovingAverageCrossoverSignalGenerator(**signal_generator_params, initial_candles=None)
        # Make sure that the candle queues are not empty
        signal_generator.short_candles_queue.append(Candle(datetime.now()))
        signal_generator.long_candles_queue.append(Candle(datetime.now()))
        # In the previous iteration, the long average was above the short average.
        signal_generator.queue.append(MovingAverageCrossoverIteration(Candle(datetime.now()), short_average=-1, long_average=0, signal=0))
        # Currently, short average has passed the long average. Should trigger a buy signal.
        signal_generator.current_short_average = -1
        signal_generator.current_long_average = 0
        assert signal_generator.generate_signal() == 0

    def test_should_not_generate_signal_if_short_queue_is_empty(self, signal_generator_params):
        signal_generator = MovingAverageCrossoverSignalGenerator(**signal_generator_params, initial_candles=None)
        # Add an element to the long candles queue but leave the short candles queue empty.
        signal_generator.long_candles_queue.append(Candle(datetime.now()))
        # In the previous iteration, the long average was below the short average.
        signal_generator.queue.append(MovingAverageCrossoverIteration(Candle(datetime.now()), short_average=1, long_average=0, signal=0))
        # Currently, short average has gone below the long average. Should trigger a sell signal.
        signal_generator.current_short_average = -1
        signal_generator.current_long_average = 0
        assert signal_generator.generate_signal() == 0

    def test_should_not_generate_signal_if_long_queue_is_empty(self, signal_generator_params):
        signal_generator = MovingAverageCrossoverSignalGenerator(**signal_generator_params, initial_candles=None)
        # Add an element to the short candles queue but leave the long candles queue empty.
        signal_generator.short_candles_queue.append(Candle(datetime.now()))
        # In the previous iteration, the long average was below the short average.
        signal_generator.queue.append(MovingAverageCrossoverIteration(Candle(datetime.now()), short_average=1, long_average=0, signal=0))
        # Currently, short average has gone below the long average. Should trigger a sell signal.
        signal_generator.current_short_average = -1
        signal_generator.current_long_average = 0
        assert signal_generator.generate_signal() == 0

    def test_iterate_when_not_full(self, signal_generator_params: Dict[str, Any],
                                   candle_data: Tuple[DataFrame, DataFrame]):
        initial_data, _ = candle_data
        signal_generator = MovingAverageCrossoverSignalGenerator(**signal_generator_params, initial_candles=None)
        # Given that queues are empty and averages are zero
        assert len(signal_generator.long_candles_queue) == 0
        assert len(signal_generator.short_candles_queue) == 0
        assert signal_generator.current_long_average == 0
        assert signal_generator.current_short_average == 0
        # When the next candle is retrieved and the generator is iterated
        candle: Candle = Candle.from_dict(initial_data.iloc[0])
        signal_generator.iterate(candle)
        # Then the long candles queue and average should update.
        assert len(signal_generator.long_candles_queue) == 1
        assert signal_generator.long_candles_queue.pop() == candle
        assert signal_generator.current_long_average == candle.mid_c / signal_generator.long_window
        # Then the short candles queue and average should update.
        assert len(signal_generator.short_candles_queue) == 1
        assert signal_generator.short_candles_queue.pop() == candle
        assert signal_generator.current_short_average == candle.mid_c / signal_generator.short_window
        # Then the SignalGeneratorIteration queue should update.
        iteration = MovingAverageCrossoverIteration(candle=candle,
                                                    signal=0,
                                                    long_average=candle.mid_c / signal_generator.long_window,
                                                    short_average=candle.mid_c / signal_generator.short_window)
        assert len(signal_generator.queue) == 1
        assert signal_generator.queue.pop() == iteration

    def test_iterate_queue_when_full(self, signal_generator_params: Dict[str, Any],
                                     candle_data: Tuple[DataFrame, DataFrame]):
        initial_data, new_data = candle_data
        long_window = signal_generator_params['long_window']
        short_window = signal_generator_params['short_window']
        signal_generator = MovingAverageCrossoverSignalGenerator(**signal_generator_params, initial_candles=initial_data)
        # Given that both queues are full and averages are not zero
        assert len(signal_generator.long_candles_queue) == long_window
        assert len(signal_generator.short_candles_queue) == short_window
        prev_long_average: float = signal_generator.current_long_average
        prev_short_average: float = signal_generator.current_short_average
        assert prev_long_average != 0
        assert prev_short_average != 0
        assert len(signal_generator.queue) == long_window
        # When the next candle is retrieved and the generator is iterated
        candle: Candle = Candle.from_dict(new_data.iloc[0])
        signal_generator.iterate(candle)
        # Then both queues and averages should update.
        assert len(signal_generator.long_candles_queue) == long_window
        assert len(signal_generator.short_candles_queue) == short_window
        assert signal_generator.long_candles_queue.pop() == candle
        assert signal_generator.short_candles_queue.pop() == candle
        assert signal_generator.current_long_average == (prev_long_average
                                                         - (initial_data.iloc[0]['mid_c'] / long_window)
                                                         + (candle.mid_c / long_window))
        assert signal_generator.current_short_average == (prev_short_average
                                                          - (initial_data.iloc[long_window - short_window - 1]['mid_c'] / short_window)
                                                          + (candle.mid_c / short_window))
        iteration = MovingAverageCrossoverIteration(candle=candle,
                                                    signal=0,
                                                    long_average=signal_generator.current_long_average,
                                                    short_average=signal_generator.current_short_average)
        assert len(signal_generator.queue) == long_window + 1
        assert signal_generator.queue.pop() == iteration

    def test_all_signals_are_correctly_generated(self, signal_generator_params: Dict[str, Any],
                                           candle_data: Tuple[DataFrame, DataFrame]):
        initial_data, new_data = candle_data
        signal_generator = MovingAverageCrossoverSignalGenerator(**signal_generator_params, initial_candles=initial_data)
        num_buys: int = 0
        num_sells: int = 0
        for i in range(new_data.shape[0]):
            candle: Candle = Candle.from_dict(new_data.iloc[i])
            signal_generator.iterate(candle)
            signal: int = signal_generator.queue[-1].signal
            if signal == 1:
                num_buys += 1
            elif signal == -1:
                num_sells += 1
        assert num_buys == num_sells

    def test_generate_signals_for_backtesting(self, signal_generator_params: Dict[str, Any]):
        candle_data: DataFrame = pd.read_csv(CANDLE_DATA_FILE)
        signal_generator = MovingAverageCrossoverSignalGenerator(**signal_generator_params, initial_candles=None)
        assert not signal_generator.queue
        signal_generator.generate_signals_for_backtesting(candle_data, use_pips=True)
        assert len(signal_generator.queue) == candle_data.shape[0]
        assert signal_generator.queue[-1].candle.time == candle_data.iloc[-1]['time']
