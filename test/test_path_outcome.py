from dataclasses import FrozenInstanceError

import pytest

from src.app.InsideBarBacktester import _path_outcome
from src.model.PathOutcome import PathOutcome


def candle(open_price, high, low, close):
    return {f'{side}_{part}': value
            for side in ('bid', 'ask')
            for part, value in zip('ohlc', (open_price, high, low, close))}


@pytest.mark.parametrize('row,existing,expected,ambiguous', [
    (candle(100, 104, 99, 103), None, PathOutcome(), False),
    (candle(106, 110, 100, 108), None,
     PathOutcome(entry_price=106, position_open_at_candle_open=True), False),
    (candle(90, 100, 85, 95), 105,
     PathOutcome(entry_price=105, exit_price=90, exit_reason='stop_loss',
                 position_open_at_candle_open=True, exit_at_candle_open=True), False),
    (candle(100, 120, 90, 110), None,
     PathOutcome(entry_price=105, exit_price=95, exit_reason='stop_loss'), True),
    (candle(106, 120, 100, 110), None,
     PathOutcome(entry_price=106, exit_price=115, exit_reason='take_profit',
                 position_open_at_candle_open=True), False),
])
def test_path_outcome_exposes_prices_reason_and_candle_timing(row, existing, expected, ambiguous):
    outcome, actual_ambiguity = _path_outcome(row, 1, 105, 95, 115, existing)
    assert isinstance(outcome, PathOutcome)
    assert outcome == expected
    assert actual_ambiguity is ambiguous


def test_custom_scorer_receives_named_outcome_fields():
    seen = []

    def prefer_target(outcome: PathOutcome):
        seen.append(outcome)
        return (0.0 if outcome.exit_reason == 'take_profit' else 1.0, 0)

    outcome, ambiguous = _path_outcome(
        candle(100, 120, 90, 110), 1, 105, 95, 115, outcome_score=prefer_target,
    )
    assert seen and all(isinstance(candidate, PathOutcome) for candidate in seen)
    assert outcome.entry_price == 105
    assert outcome.exit_reason == 'take_profit'
    assert ambiguous


def test_outcomes_are_immutable_and_hashable_for_ambiguity_detection():
    first = PathOutcome(entry_price=105)
    same = PathOutcome(entry_price=105)
    different = PathOutcome(entry_price=105, position_open_at_candle_open=True)
    assert len({first, same, different}) == 2
    with pytest.raises(FrozenInstanceError):
        first.entry_price = 100
