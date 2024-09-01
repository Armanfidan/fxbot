from collections import deque
from typing import Literal, override

from pandas import DataFrame

from Granularity import Granularity
from candle.Candle import Candle
from signal_generators.SignalGenerator import SignalGenerator
from strategy_iterations.MovingAverageCrossoverIteration import MovingAverageCrossoverIteration
from strategy_iterations.StrategyIteration import StrategyIteration


class MovingAverageCrossoverSignalGenerator(SignalGenerator):
    def __init__(self, pair: str, pip_location: float, granularity: Granularity, short_window: int, long_window: int, historical_data: DataFrame = None):
        super().__init__(pair, pip_location, granularity, historical_data)
        self.short_window = short_window
        self.long_window = long_window
        self.queue: deque[MovingAverageCrossoverIteration] | None = None
        self.long_candles_queue: deque[Candle] = deque(maxlen=self.long_window)
        self.short_candles_queue: deque[Candle] = deque(maxlen=self.short_window)
        self.set_candles_queue_from_df(self.long_window)
        self.current_long_average = 0
        self.current_short_average = 0

    # def _generate_moving_average_indicators(self, short_window: int, long_window: int) -> Tuple[str, str]:
    #     self.long_candles_queue[ma_names[0]] = self.candles_df[Price.MID_CLOSE.value].rolling(short_window).mean()
    #     self.candles_df[ma_names[1]] = self.candles_df[Price.MID_CLOSE.value].rolling(long_window).mean()
    #     self.candles_df.dropna(inplace=True)
    #     self.candles_df.reset_index(drop=True, inplace=True)
    #     return ma_names[0], ma_names[1]
    #
    # def _generate_ma_crossover_signals(self, short_window: int, long_window: int):
    #     ma_short, ma_long = self._generate_moving_average_indicators(short_window, long_window)
    #     self.long_candles_queue['holding'] = np.where(self.long_candles_queue[ma_short] > self.long_candles_queue[ma_long], 1, -1)
    #     self.long_candles_queue['signal'] = np.where(self.long_candles_queue['holding'] != self.long_candles_queue['holding'].shift(1),
    #                                                  self.long_candles_queue['holding'], 0)
    #     self.signals = self.long_candles_queue[self.long_candles_queue['signal'] != 0][
    #         ['time', Price.ASK_CLOSE.value, Price.MID_CLOSE.value, Price.BID_CLOSE.value, 'signal']]
    #
    # def _generate_ma_crossover_signal_detail_columns(self, use_pips: bool) -> DataFrame:
    #     if self.signals.empty:
    #         raise ValueError("Please generate signals before using this function.")
    #     if use_pips:
    #         self.signals['gain'] = (self.signals[Price.MID_CLOSE.value].diff() / 10 ** self.pip_location).shift(-1)
    #     else:
    #         self.signals['gain'] = self.signals[Price.MID_CLOSE.value].diff().shift(-1)
    #     self.signals['duration'] = self.signals['time'].diff().shift(-1).apply(lambda time: time.seconds / 60)
    #     return self.signals

    def generate_signal(self) -> int:
        """
        Generates a signal for the latest short and long total values.
        :return: A signal: 1 for buy, -1 for sell and 0 for nothing.
        """
        previous_difference = self.queue[-1].short_average - self.queue[-1].long_average
        current_difference = self.current_short_average - self.current_long_average
        if current_difference <= 0 < previous_difference:
            return -1
        if previous_difference < 0 <= current_difference:
            return 1
        return 0

    def iterate_queue(self, candle, window: Literal["long", "short"]):
        """
        Add new candle to the appropriate queue,
        add the closing price to the total price,
        remove the oldest closing price from the total price.
        :param candle: The latest candle
        :param window: Whether to iterate the long or short window queue.
        :return:
        """
        average: float = self.current_long_average if window == "long" else self.current_short_average
        window: int = self.long_window if window == "long" else self.short_window
        queue: deque = self.long_candles_queue if window == "long" else self.short_candles_queue
        if len(queue) >= self.long_window if window == "long" else self.short_window:
            average -= queue.popleft().mid_c / window
        average += candle.mid_c / window
        queue.append(candle)

    @override
    def iterate(self, candle: Candle) -> StrategyIteration:
        self.iterate_queue(candle, window="long")
        self.iterate_queue(candle, window="short")
        iteration: MovingAverageCrossoverIteration = MovingAverageCrossoverIteration(
            candle=candle,
            signal=self.generate_signal(),
            short_average=self.current_short_average,
            long_average=self.current_long_average
        )
        self.queue.append(iteration)
        return iteration
    # def generate_signals(self, use_pips: bool) -> DataFrame:
    #     self._generate_ma_crossover_signals(self.params['short_window'], self.params['long_window'])
    #     return self._generate_ma_crossover_signal_detail_columns(use_pips)
