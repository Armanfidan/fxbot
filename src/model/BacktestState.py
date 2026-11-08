"""Mutable account and ledger state belonging to one backtest run."""
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from src.model.Trade import Trade


@dataclass(kw_only=True)
class BacktestState:
    """Owned by one Backtester instance and replaced with fresh state for each run.

    Configuration belongs to the Backtester; conversion data is passed to its
    accounting methods. Each ledger has its own list, including across repeated runs.
    """
    pair: str
    balance: float
    last_rollover: pd.Timestamp
    position: Trade | None = None
    pending_order: dict[str, Any] | None = None
    next_trade_id: int = 1
    ambiguous_candles: int = 0
    orders: list[dict[str, Any]] = field(default_factory=list)
    fills: list[dict[str, Any]] = field(default_factory=list)
    trades: list[dict[str, Any]] = field(default_factory=list)
    rejected_orders: list[dict[str, Any]] = field(default_factory=list)
    financing: list[dict[str, Any]] = field(default_factory=list)
    equity: list[dict[str, Any]] = field(default_factory=list)

    @property
    def base_currency(self) -> str:
        return self.pair.split('_')[0]

    @property
    def quote_currency(self) -> str:
        return self.pair.split('_')[1]
