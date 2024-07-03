from datetime import datetime
from typing import Literal, List

from pandas import DataFrame, Series
from plotly import graph_objects as go


def add_signal_trace(fig: go.Figure, candles: DataFrame, signal_type: Literal['buy', 'sell']):
    buy: bool = signal_type == 'buy'
    fig.add_trace(go.Scatter(mode='markers',
                             x=candles[candles['signal'] == (1 if buy else -1)]['time'],
                             y=candles[candles['signal'] == (1 if buy else -1)]['mid_c'],
                             marker=dict(symbol='arrow-{}'.format('up' if buy else 'down'),
                                         size=20,
                                         color='#579773' if buy else '#eb5242',
                                         line_color='#95cfae' if buy else '#e67c70',
                                         line_width=2),
                             name=str(signal_type).title() + ' Order'))


def plot_candles_for_ma_crossover(historical_data: DataFrame, from_date: datetime, to_date: datetime, ma_short: int, ma_long: int, title: str) -> None:
    candles = historical_data[(from_date < historical_data['time']) & (historical_data['time'] < to_date)]
    fig = plot_candles(candles, title)
    for col in ["MA_{}".format(ma) for ma in (ma_short, ma_long)]:
        fig.add_trace(go.Scatter(x=candles['time'],
                                 y=candles[col],
                                 line=dict(width=2, shape='spline'),
                                 name=col, zorder=100))
    add_signal_trace(fig, candles, 'buy')
    add_signal_trace(fig, candles, 'sell')
    fig.show()


def add_entry_and_exit_traces(fig: go.Figure, candles: DataFrame):
    entry_colours: List[str] = ['#043ef9', '#eb5334', '#34eb37']  # For entry stop, stop loss and take profit, respectively.
    entry_times: Series = candles[candles['entry_time'].notna()]['entry_time']
    fig.add_trace(go.Scatter(mode='markers',
                             x=entry_times,
                             y=candles[candles['time'].isin(entry_times)]['mid_c'],
                             marker=dict(color=entry_colours[0], size=12),
                             name='Entry'))

    exit_times_and_gains: DataFrame = candles[candles['exit_time'].notna()][['exit_time', 'gain']]
    exit_times = exit_times_and_gains[exit_times_and_gains['gain'] > 0]['exit_time']
    stop_loss_times = exit_times_and_gains[exit_times_and_gains['gain'] <= 0]['exit_time']
    fig.add_trace(go.Scatter(mode='markers',
                             x=exit_times,
                             y=candles[candles['time'].isin(exit_times)]['mid_c'],
                             marker=dict(color=entry_colours[2], size=12),
                             name='Exit'))
    fig.add_trace(go.Scatter(mode='markers',
                             x=stop_loss_times,
                             y=candles[candles['time'].isin(stop_loss_times)]['mid_c'],
                             marker=dict(color=entry_colours[1], size=12),
                             name='Stop Loss'))


def plot_candles_for_inside_bar_momentum(historical_data: DataFrame, from_date: datetime, to_date: datetime, title: str):
    candles = historical_data[(from_date < historical_data['time']) & (historical_data['time'] < to_date)]
    fig = plot_candles(candles, title)

    add_signal_trace(fig, candles, 'buy')
    add_signal_trace(fig, candles, 'sell')
    add_entry_and_exit_traces(fig, candles)
    fig.show()


def plot_candles(candles, title):
    fig = go.Figure(layout_title_text=title)
    fig.add_trace(go.Candlestick(
        x=candles['time'],
        open=candles['mid_o'],
        high=candles['mid_h'],
        low=candles['mid_l'],
        close=candles['mid_c'],
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
