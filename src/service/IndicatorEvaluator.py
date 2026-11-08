"""Performance from account equity, never from a signal-dependent price series."""
import math
import numpy as np
import pandas as pd

NUM_TRADING_DAYS_IN_A_YEAR = 252


class IndicatorEvaluator:
    def __init__(self, pair, equity, trades=None, annual_risk_free_rate=0.0):
        if not {'time', 'equity'} <= set(equity.columns) or len(equity) < 2:
            raise ValueError('Require equity history including initial baseline and final observation')

        self.pair = pair
        self.equity = equity.copy()
        self.equity['time'] = pd.to_datetime(self.equity['time'], utc=True)

        if not self.equity.time.is_monotonic_increasing:
            raise ValueError('Equity timestamps must be chronological')

        values = self.equity.equity.to_numpy(dtype=float)
        if not np.isfinite(values).all() or values[0] <= 0:
            raise ValueError('Require finite equity and positive initial balance')

        if not math.isfinite(annual_risk_free_rate) or annual_risk_free_rate <= -1:
            raise ValueError('Risk-free rate must be finite and exceed -1')

        self.trades = trades if trades is not None else pd.DataFrame()
        self.annual_risk_free_rate = annual_risk_free_rate

    @property
    def daily_returns(self):
        # Exclude the synthetic baseline from observed trading days.
        observed = self.equity.iloc[1:].set_index('time').equity
        closes = observed.groupby(observed.index.normalize()).last()
        previous = closes.shift(1)
        previous.iloc[0] = self.equity.equity.iloc[0]

        if (previous <= 0).any():
            return pd.Series(dtype=float)

        return closes / previous - 1

    @staticmethod
    def _divide(numerator, denominator):
        if denominator is None or denominator <= 1e-15 or not math.isfinite(denominator):
            return None

        value = numerator / denominator
        return float(value) if math.isfinite(value) else None

    def calculate_roi(self):
        return {'roi_indicator': float(self.equity.equity.iloc[-1] / self.equity.equity.iloc[0] - 1)}

    def calculate_standard_deviation_of_returns(self, returns_df=None, negative_only=False):

        if (returns := self.daily_returns).empty:
            return None
        if negative_only:
            return float(np.sqrt(np.mean(np.minimum(returns, 0) ** 2)))

        return float(returns.std(ddof=1)) if len(returns) >= 2 else None

    def calculate_mean_of_returns(self, returns_df=None):
        return float(self.daily_returns.mean()) if len(self.daily_returns) else None

    def _excess(self):
        rf = math.expm1(math.log1p(self.annual_risk_free_rate) / 252)
        return self.daily_returns - rf

    def calculate_sharpe_ratio(self, returns_df=None):
        excess = self._excess()
        if len(excess) < 2:
            return None
        return self._divide(excess.mean(), float(excess.std(ddof=1)))

    def calculate_annualised_sharpe_ratio(self, returns_df=None):
        ratio = self.calculate_sharpe_ratio()
        return None if ratio is None else math.sqrt(252) * ratio

    def calculate_sortino_ratio(self, returns_df=None):
        excess = self._excess()
        if len(excess) < 2:
            return None
        return self._divide(excess.mean(), float(np.sqrt(np.mean(np.minimum(excess, 0) ** 2))))

    def calculate_annualised_sortino_ratio(self, returns_df=None):
        ratio = self.calculate_sortino_ratio()
        return None if ratio is None else math.sqrt(252) * ratio

    def calculate_max_drawdown(self, returns_df=None):
        values = self.equity.equity
        return float((1 - values / values.cummax()).max())

    def calculate_cagr(self):
        years = (self.equity.time.iloc[-1] - self.equity.time.iloc[0]).total_seconds() / (365.25 * 86400)
        multiple = self.equity.equity.iloc[-1] / self.equity.equity.iloc[0]
        if years <= 0 or multiple <= 0:
            return None
        try:
            result = math.expm1(math.log(multiple) / years)
            return result if math.isfinite(result) else None
        except OverflowError:
            return None

    def calculate_calmar_ratio(self, returns_df=None):
        cagr = self.calculate_cagr()
        return None if cagr is None else self._divide(cagr, self.calculate_max_drawdown())

    def calculate_annualised_calmar_ratio(self, returns_df=None):
        return self.calculate_calmar_ratio()

    def calculate_profit_to_drawdown_ratio(self):
        values = self.equity.equity
        return self._divide(values.iloc[-1] - values.iloc[0], float((values.cummax() - values).max()))

    def calculate_trade_durations(self, returns_df=None):
        frame = self.trades if returns_df is None else returns_df
        if frame.empty:
            return pd.Series(dtype='timedelta64[ns]')

        return pd.to_datetime(frame.exit_time, utc=True) - pd.to_datetime(frame.entry_time, utc=True)

    def calculate_total_time_in_market(self):
        return self.calculate_trade_durations().sum() if not self.trades.empty else pd.Timedelta(0)

    def calculate_secondary_metrics(self):
        count = len(self.trades)
        return {
            'trade_count': count,
            'long_count': int((self.trades.signal == 1).sum()) if count else 0,
            'short_count': int((self.trades.signal == -1).sum()) if count else 0,
            'win_rate': float((self.trades.net_pnl > 0).mean()) if count else None
        }

    def metrics(self):
        values = self.equity.equity
        duration = self.calculate_total_time_in_market().total_seconds()
        elapsed = (self.equity.time.iloc[-1] - self.equity.time.iloc[0]).total_seconds()

        return {
            'initial_equity': float(values.iloc[0]), 'final_equity': float(values.iloc[-1]),
            'net_profit': float(values.iloc[-1] - values.iloc[0]),
            'total_return': self.calculate_roi()['roi_indicator'], 'cagr': self.calculate_cagr(),
            'sharpe': self.calculate_annualised_sharpe_ratio(),
            'sortino': self.calculate_annualised_sortino_ratio(),
            'max_drawdown': self.calculate_max_drawdown(),
            'max_drawdown_amount': float((values.cummax() - values).max()),
            'calmar': self.calculate_calmar_ratio(),
            'profit_to_drawdown': self.calculate_profit_to_drawdown_ratio(),
            'time_in_market_seconds': duration,
            'exposure_fraction': duration / elapsed if elapsed > 0 else None,
            'daily_observations': len(self.daily_returns),
            **self.calculate_secondary_metrics()
        }
