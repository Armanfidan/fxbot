from pandas import DataFrame

from signal_generators.SignalGenerator import SignalGenerator
from strategy_iterations.StrategyIteration import StrategyIteration


ENTRY_PRICE_MUL = 0.1
STOP_LOSS_MUL = 0.4
TAKE_PROFIT_MUL = 0.8


class MovingAverageCrossoverSignalGenerator(SignalGenerator):

    def _generate_inside_bar_momentum_indicators(self):
        self.queue['range_prev'] = (self.queue[Price.MID_HIGH.value] - self.queue[Price.MID_LOW.value]).shift(1)
        self.queue['mid_h_prev'] = self.queue[Price.MID_HIGH.value].shift(1)
        self.queue['mid_l_prev'] = self.queue[Price.MID_LOW.value].shift(1)
        self.queue['direction_prev'] = self.queue.apply(lambda row: 1 if row[Price.MID_CLOSE.value] > row[Price.MID_OPEN.value] else -1, axis=1).shift(1)
        self.queue.dropna(inplace=True)
        self.queue.reset_index(drop=True, inplace=True)

    def _inside_bar_momentum_indicators(self, indicator: Literal['entry_stop', 'stop_loss', 'take_profit'], row: Dict[str, float]):
        if self.granularity not in [Granularity.H4, Granularity.H6, Granularity.H8, Granularity.H12, Granularity.D, Granularity.W, Granularity.M]:
            raise ValueError('Please enter a granularity larger than or equal to H4 to generate inside bar momentum indicators.')
        reference_price_column = 'mid_h_prev' if row['signal'] == 1 else 'mid_l_prev'
        if indicator == 'entry_stop':
            return row[reference_price_column] + row['signal'] * (row['range_prev'] * ENTRY_PRICE_MUL)
        if indicator == 'stop_loss':
            return row[reference_price_column] + -1 * row['signal'] * (row['range_prev'] * STOP_LOSS_MUL)
        if indicator == 'take_profit':
            return row[reference_price_column] + row['signal'] * (row['range_prev'] * TAKE_PROFIT_MUL)

    def _generate_inside_bar_momentum_signals(self):
        self._generate_inside_bar_momentum_indicators()
        self.queue['signal'] = self.queue.apply(lambda row: row['direction_prev'] if row['mid_h_prev'] > row[Price.MID_HIGH.value] and row['mid_l_prev'] < row[Price.MID_LOW.value] else 0, axis=1)
        self.queue['entry_stop'] = self.queue.apply(functools.partial(self._inside_bar_momentum_indicators, 'entry_stop'), axis=1)
        self.queue['stop_loss'] = self.queue.apply(functools.partial(self._inside_bar_momentum_indicators, 'stop_loss'), axis=1)
        self.queue['take_profit'] = self.queue.apply(functools.partial(self._inside_bar_momentum_indicators, 'take_profit'), axis=1)
        self.queue.drop(['mid_h_prev', 'mid_l_prev', 'direction_prev'], axis=1, inplace=True)
        self.signals = self.queue[self.queue['signal'] != 0]

    def generate_inside_bar_momentum_signal_detail_columns(self, use_pips: bool) -> DataFrame:
        if self.signals.empty or 'entry_time' not in self.queue.columns:
            raise ValueError("Please generate signals before using this function.")
        gain_literal = (self.queue['exit_price'] - self.queue['entry_price']) * self.queue['signal']
        self.queue['gain'] = gain_literal / (10 ** self.pip_location if use_pips else 1)
        self.queue['duration'] = (self.queue['exit_time'] - self.queue['entry_time']).apply(lambda time: time.seconds / 60)
        self.signals = self.queue[self.queue['signal'].notna()]
        return self.signals

    def iterate(self) -> StrategyIteration:
        pass

    def generate_signals(self, use_pips: bool) -> DataFrame:
        self._generate_inside_bar_momentum_signals()
        return self.signals

