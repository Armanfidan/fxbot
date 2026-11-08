"""The result of following one possible bid/ask path through a candle."""
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, kw_only=True)
class PathOutcome:
    """Prices precede any new fill's slippage and commission adjustments.

    entry_price is None if no entry occurs; for an existing position it retains
    that position's original entry price. exit_price and exit_reason are None
    if the position does not exit during this candle.

    position_open_at_candle_open includes both positions carried into the candle
    and new entries triggered by its opening quote. exit_at_candle_open means
    an exit occurs at the opening timestamp, not that the position stays open.
    """
    entry_price: float | None = None
    exit_price: float | None = None
    exit_reason: Literal['stop_loss', 'take_profit'] | None = None
    position_open_at_candle_open: bool = False
    exit_at_candle_open: bool = False
