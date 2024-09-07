import os
from typing import Any, Dict, Tuple

import pandas as pd
import pytest
from pandas import DataFrame

from src.util.Constants import CURRENT_PROJECT_ROOT

SIGNAL_DATA_FILE = '{}/test/resources/signals.csv'.format(CURRENT_PROJECT_ROOT)


@pytest.fixture
def candles_and_signals():
    yield pd.read_csv(SIGNAL_DATA_FILE)


class TestIndicatorEvaluator:
    def test_calculates_roi_correctly(self, signals: Tuple[DataFrame, DataFrame]):
        pass

    def test_compares_to_index_correctly(self, signals: Tuple[DataFrame, DataFrame]):
        pass

    def test_calculates_standard_deviation_correctly(self, signals: Tuple[DataFrame, DataFrame]):
        pass

    def test_calculates_sharpe_ratio_correctly(self, signals: Tuple[DataFrame, DataFrame]):
        pass

    def test_calculates_max_drawdown_correctly(self, signals: Tuple[DataFrame, DataFrame]):
        pass

    def test_calculates_profit_to_drawdown_ratio_correctly(self, signals: Tuple[DataFrame, DataFrame]):
        pass

    def test_calculates_trade_durations_correctly(self, signals: Tuple[DataFrame, DataFrame]):
        pass

    def test_calculates_total_time_in_market_correctly(self, signals: Tuple[DataFrame, DataFrame]):
        pass

    def test_calculates_secondary_metrics_correctly(self, signals: Tuple[DataFrame, DataFrame]):
        pass
