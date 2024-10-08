from __future__ import annotations

from datetime import datetime
from typing import Literal

from pandas import Series

from src.model.candle.Price import Price


class Trade:
    def __init__(self, trade_row: Series):
        # Currency pair.
        self.time: datetime = trade_row['time']
        self.signal: Literal[-1, 1] = trade_row['signal']
        self.entry_stop: float = trade_row['entry_stop']
        self.stop_loss: float = trade_row['stop_loss']
        self.take_profit: float = trade_row['take_profit']
        # Entry time and price. The closing price of the entering candle will be used as the entry price.
        self.entry_time: datetime | None = None
        self.entry_price: float | None = None
        # Exit time and price. The closing price of the exiting candle will be used as the exit price.
        self.exit_time: datetime | None = None
        self.exit_price: float | None = None
        # Whether the trade is still running/open.
        self.__trade_is_open: bool = False
        # self.gain: float = 0

    def is_open(self):
        return self.__trade_is_open

    def update(self, candle: Series):
        if self.exit_time is not None:
            return
        if self.__trade_is_open:
            self.check_exit(candle)
        else:
            self.check_entry(candle)

    def check_entry(self, candle: Series) -> bool:
        buy_stop_reached: bool = self.signal == 1 and candle[Price.ASK_CLOSE.value] >= self.entry_stop
        sell_stop_reached: bool = self.signal == -1 and candle[Price.BID_CLOSE.value] <= self.entry_stop
        if not (buy_stop_reached or sell_stop_reached):
            return False
        self.entry_time = candle['time']
        self.entry_price = candle[Price.ASK_CLOSE.value if self.signal == 1 else Price.BID_CLOSE.value]
        self.__trade_is_open = True
        return True

    def close_trade(self, candle: Series):
        self.exit_time = candle['time']
        self.exit_price = candle[Price.BID_CLOSE.value if self.signal == 1 else Price.ASK_CLOSE.value]
        self.__trade_is_open = False
        # self.gain = self.exit_price - self.entry_price

    def check_exit(self, candle: Series) -> bool:
        buy_stop_loss_reached: bool = self.signal == 1 and candle[Price.BID_CLOSE.value] <= self.stop_loss
        sell_stop_loss_reached: bool = self.signal == -1 and candle[Price.ASK_CLOSE.value] >= self.stop_loss
        buy_take_profit_reached: bool = self.signal == 1 and candle[Price.BID_CLOSE.value] >= self.take_profit
        sell_take_profit_reached: bool = self.signal == -1 and candle[Price.ASK_CLOSE.value] <= self.take_profit
        if not self.__trade_is_open:
            return False
        trade_exited: bool = buy_take_profit_reached or buy_stop_loss_reached or sell_take_profit_reached or sell_stop_loss_reached
        if trade_exited:
            self.close_trade(candle)
        return trade_exited
