"""Configuration and result models shared by the backtester and evaluator."""
from dataclasses import asdict, dataclass, field
from pathlib import Path
import json
import math
import pandas as pd
from src.model.Granularity import Granularity
from src.model.Indicator import Indicator


@dataclass(frozen=True)
class CostConfig:
    slippage_pips: float | None = None
    commission_per_fill: float | None = None
    financing_rates: dict[str, dict[str, float]] | None = None

    def __post_init__(self):
        for value in (self.slippage_pips, self.commission_per_fill):
            if value is not None and (not math.isfinite(value) or value < 0):
                raise ValueError('Slippage and commission must be finite and non-negative')

        if self.financing_rates is not None:
            for rates in self.financing_rates.values():
                if set(rates) != {'long', 'short'} or not all(math.isfinite(v) for v in rates.values()):
                    raise ValueError('Financing requires finite long and short rates')

    def omitted(self, pair):
        omitted = [name for name in ('slippage_pips', 'commission_per_fill') if getattr(self, name) is None]
        if self.financing_rates is None or pair not in self.financing_rates:
            omitted.append('financing_rates')
        return omitted


@dataclass(frozen=True)
class BacktestConfig:
    indicator: Indicator = Indicator.MA_CROSSOVER
    account_currency: str = 'GBP'
    initial_balance: float = 10000.0
    units: int = 1000
    strategy_granularity: Granularity = Granularity.H4
    execution_granularity: Granularity = Granularity.M5
    short_window: int = 16
    long_window: int = 64
    pip_location: int = -4
    annual_risk_free_rate: float = 0.0
    costs: CostConfig = field(default_factory=CostConfig)

    def __post_init__(self):
        if not math.isfinite(self.initial_balance) or self.initial_balance <= 0:
            raise ValueError('Initial balance must be positive')
        if not isinstance(self.units, int) or isinstance(self.units, bool) or self.units <= 0:
            raise ValueError('Units must be a positive integer')
        if not math.isfinite(self.annual_risk_free_rate) or self.annual_risk_free_rate <= -1:
            raise ValueError('Risk-free rate must exceed -1')
        if self.execution_granularity.value > self.strategy_granularity.value:
            raise ValueError('Execution candles cannot be coarser than strategy candles')
        if Granularity.M in (self.strategy_granularity, self.execution_granularity):
            raise ValueError('Calendar month candles are unsupported')
        if not isinstance(self.pip_location, int):
            raise ValueError('Pip location must be an integer exponent')
        if len(self.account_currency) != 3 or not self.account_currency.isupper():
            raise ValueError('Account currency must be a three-letter uppercase code')


@dataclass
class ConversionData:
    candles: pd.DataFrame
    granularity: Granularity


@dataclass
class BacktestResult:
    pair: str
    configuration: BacktestConfig
    signals: pd.DataFrame
    orders: pd.DataFrame
    fills: pd.DataFrame
    trades: pd.DataFrame
    equity: pd.DataFrame
    rejected_orders: pd.DataFrame
    financing: pd.DataFrame
    metrics: dict
    ambiguous_candles: int = 0
    omitted_costs: list[str] = field(default_factory=list)

    def export(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        for name in ('signals', 'orders', 'fills', 'trades', 'equity', 'rejected_orders', 'financing'):
            getattr(self, name).to_csv(directory / f'{name}.csv', index=False)
        config = asdict(self.configuration)
        for key in ('strategy_granularity', 'execution_granularity', 'indicator'):
            config[key] = getattr(self.configuration, key).name
        summary = {'pair': self.pair, 'funding': 'independent', 'configuration': config,
                   'metrics': self.metrics, 'ambiguous_candles': self.ambiguous_candles,
                   'omitted_costs': self.omitted_costs,
                   'cost_status': 'partial' if self.omitted_costs else 'fully_configured'}
        (directory / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False))
