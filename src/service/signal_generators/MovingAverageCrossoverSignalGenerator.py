from collections import deque
from typing import Literal, override, List

from pandas import DataFrame

from Granularity import Granularity
from candle.Candle import Candle
from signal_generators.SignalGenerator import SignalGenerator
from strategy_iterations.MovingAverageCrossoverIteration import MovingAverageCrossoverIteration


class MovingAverageCrossoverSignalGenerator(SignalGenerator):
    """
    A generator to generate signals for the Moving Average Crossover strategy. Works for backtesting or iterative generation
    for live trading.
    """
    def __init__(self, pair: str, pip_location: float, granularity: Granularity, short_window: int, long_window: int, initial_candles: DataFrame = None):
        super().__init__(pair, pip_location, granularity, initial_candles)
        # Set windows and averages
        self.short_window = short_window
        self.long_window = long_window
        self.current_long_average, self.current_short_average = 0, 0
        # Set queue
        self.queue: List[MovingAverageCrossoverIteration] = []
        # Set queues
        self.long_candles_queue: deque[Candle] = deque(maxlen=self.long_window)
        self.short_candles_queue: deque[Candle] = deque(maxlen=self.short_window)
        # Initialise queue if initial data was provided
        if isinstance(initial_candles, DataFrame):
            self.iterate_from_dataframe(initial_candles)

    def generate_signal(self) -> int:
        """
        Generates a signal for the latest short and long total values.
        :return: A signal: 1 for buy, -1 for sell and 0 for nothing.
        """
        if not self.short_candles_queue or self.long_candles_queue:
            return 0
        previous_difference = self.queue[-1].short_average - self.queue[-1].long_average
        current_difference = self.current_short_average - self.current_long_average
        if current_difference <= 0 < previous_difference:
            return -1
        if previous_difference < 0 <= current_difference:
            return 1
        return 0

    def _iterate_queue(self, candle, window_type: Literal["long", "short"]):
        """
        - Add new candle to the appropriate queue,
        - Add the closing price to the total price,
        - Remove the oldest closing price from the total price.
        :param candle: The latest candle
        :param window_type: Whether to iterate the long or short window queue.
        """
        # Defining variables based on window
        window: int = vars(self)[window_type + '_window']
        candles_queue: deque[Candle] = vars(self)[window_type + '_candles_queue']
        # Updating the averages
        if window_type == "long":
            if len(candles_queue) >= window:
                self.current_long_average -= candles_queue.popleft().mid_c / window
            self.current_long_average += candle.mid_c / window
        else:
            if len(candles_queue) >= window:
                self.current_short_average -= candles_queue.popleft().mid_c / window
            self.current_short_average += candle.mid_c / window
        candles_queue.append(candle)

    @override
    def iterate(self, candle: Candle) -> None:
        self._iterate_queue(candle, window_type="long")
        self._iterate_queue(candle, window_type="short")
        iteration: MovingAverageCrossoverIteration = MovingAverageCrossoverIteration(
            candle=candle,
            signal=self.generate_signal(),
            short_average=self.current_short_average,
            long_average=self.current_long_average
        )
        self.queue.append(iteration)
