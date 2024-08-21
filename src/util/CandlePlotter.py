from datetime import datetime
from typing import Literal, List

from pandas import DataFrame, Series
from plotly import graph_objects as go

from CandleDefinitions import Price


class CandlePlotter:
    def __init__(self, candles: DataFrame, from_time: datetime = None, to_time: datetime = None):
        self.candles: DataFrame = candles
        if from_time:
            self.candles = self.candles[from_time < self.candles['time']]
        if to_time:
            self.candles = self.candles[self.candles['time'] < to_time]
        self.fig: go.Figure = go.Figure()

    def add_signal_trace(self, signal_type: Literal['buy', 'sell']):
        buy: bool = signal_type == 'buy'
        # noinspection SpellCheckingInspection
        self.fig.add_trace(go.Scatter(mode='markers',
                                      x=self.candles[self.candles['signal'] == (1 if buy else -1)]['time'],
                                      y=self.candles[self.candles['signal'] == (1 if buy else -1)][Price.ASK_CLOSE.value if buy else Price.BID_CLOSE.value],
                                      marker=dict(symbol='arrow-{}'.format('up' if buy else 'down'),
                                                  size=20,
                                                  color='#579773' if buy else '#eb5242',
                                                  line_color='#95cfae' if buy else '#e67c70',
                                                  line_width=2),
                                      name=str(signal_type).title() + ' Order'))

    def plot_candles_for_ma_crossover(self, ma_short: int, ma_long: int, title: str) -> None:
        self.fig = self.plot_candles(title)
        for col in ["MA_{}".format(ma) for ma in (ma_short, ma_long)]:
            self.fig.add_trace(go.Scatter(x=self.candles['time'], y=self.candles[col],
                                          line=dict(width=2, shape='spline'), name=col, zorder=100))
        self.add_signal_trace('buy')
        self.add_signal_trace('sell')
        self.fig.show()

    def add_entry_and_exit_traces(self):
        entry_colours: List[str] = ['#043ef9', '#eb5334', '#34eb37']  # For entry stop, stop loss and take profit, respectively.
        entry_times: Series = self.candles[self.candles['entry_time'].notna()]['entry_time']
        self.fig.add_trace(go.Scatter(mode='markers',
                                      x=entry_times,
                                      y=self.candles[self.candles['time'].isin(entry_times)][Price.MID_CLOSE.value],
                                      marker=dict(color=entry_colours[0], size=12),
                                      name='Entry'))

        exit_times_and_gains: DataFrame = self.candles[self.candles['exit_time'].notna()][['exit_time', 'gain']]
        exit_times = exit_times_and_gains[exit_times_and_gains['gain'] > 0]['exit_time']
        stop_loss_times = exit_times_and_gains[exit_times_and_gains['gain'] <= 0]['exit_time']
        self.fig.add_trace(go.Scatter(mode='markers',
                                      x=exit_times,
                                      y=self.candles[self.candles['time'].isin(exit_times)][Price.MID_CLOSE.value],
                                      marker=dict(color=entry_colours[2], size=12),
                                      name='Exit'))
        self.fig.add_trace(go.Scatter(mode='markers',
                                      x=stop_loss_times,
                                      y=self.candles[self.candles['time'].isin(stop_loss_times)][Price.MID_CLOSE.value],
                                      marker=dict(color=entry_colours[1], size=12),
                                      name='Stop Loss'))

    def plot_candles_for_inside_bar_momentum(self, title: str):
        self.fig = self.plot_candles(title)
        self.add_signal_trace('buy')
        self.add_signal_trace('sell')
        self.add_entry_and_exit_traces()
        self.fig.show()

    def plot_candles(self, title):
        fig = go.Figure(layout_title_text=title)
        fig.add_trace(go.Candlestick(
            x=self.candles['time'],
            open=self.candles[Price.MID_OPEN.value],
            high=self.candles[Price.MID_HIGH.value],
            low=self.candles[Price.MID_LOW.value],
            close=self.candles[Price.MID_CLOSE.value],
            name='Prices'))
        fig.update_layout(font=dict(size=10, color="#e1e1e1"),
                          paper_bgcolor="#1e1e1e",
                          plot_bgcolor="#1e1e1e")
        fig.update_xaxes(
            gridcolor="#1f292f",
            showgrid=True, fixedrange=False
        )
        fig.update_yaxes(
            gridcolor="#1f292f",
            showgrid=True, fixedrange=False
        )
        return fig
