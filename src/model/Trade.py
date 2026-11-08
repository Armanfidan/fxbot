"""A single position's fills and account-currency accounting."""
from dataclasses import dataclass
import pandas as pd


@dataclass
class Trade:
    trade_id: int
    pair: str
    signal: int
    units: int
    signal_time: pd.Timestamp
    entry_time: pd.Timestamp
    entry_price: float
    reserved_notional: float
    stop_loss: float | None = None
    take_profit: float | None = None
    commission: float = 0.0
    financing: float = 0.0
    ambiguous: bool = False
    exit_time: pd.Timestamp | None = None
    exit_price: float | None = None
    exit_reason: str | None = None
    gross_pnl: float = 0.0

    @property
    def net_pnl(self):
        return self.gross_pnl - self.commission + self.financing

    def quote_pnl(self, price):
        return self.signal * self.units * (price - self.entry_price)

    def is_open(self):
        return self.exit_time is None

    def record(self):
        return vars(self) | {'net_pnl': self.net_pnl,
                             'duration_seconds': (self.exit_time - self.entry_time).total_seconds() if self.exit_time is not None else None}
