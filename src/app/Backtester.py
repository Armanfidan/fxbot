"""Historical orchestration, conservative fills and unleveraged FX accounting."""
import collections

import dataclasses
import itertools
import pathlib
import numpy as np
import pandas as pd

from src.model.Backtest import BacktestConfig, BacktestResult, ConversionData
from src.model.BacktestState import BacktestState
from src.model.Granularity import Granularity
from src.model.Indicator import Indicator
from src.model.Trade import Trade
from src.service.IndicatorEvaluator import IndicatorEvaluator
from src.util.CandlePlotter import CandlePlotter


def validate_candles(candles, granularity):
    """Validate without reordering, deduplicating or silently repairing market data."""
    required = ['time'] + [f'{side}_{part}' for side in ('bid', 'ask', 'mid') for part in 'ohlc']
    if candles.empty or not set(required) <= set(candles):
        raise ValueError('Require nonempty timestamped bid/ask/mid OHLC data')

    frame = candles.copy()
    frame['time'] = pd.to_datetime(frame.time, utc=True)

    if frame.time.isna().any() or not frame.time.is_monotonic_increasing or frame.time.duplicated().any():
        raise ValueError('Candle timestamps must be valid, unique and sorted')

    if (frame.time.diff().dropna() < granularity.value).any():
        raise ValueError('Execution/strategy candles cannot overlap')

    prices = frame[required[1:]].astype(float)
    if not np.isfinite(prices.to_numpy()).all() or (prices <= 0).any().any():
        raise ValueError('Prices must be positive and finite')
    frame[required[1:]] = prices

    for side in ('bid', 'ask', 'mid'):
        if ((frame[f'{side}_h'] < frame[[f'{side}_o', f'{side}_c', f'{side}_l']].max(axis=1)) |
            (frame[f'{side}_l'] > frame[[f'{side}_o', f'{side}_c', f'{side}_h']].min(axis=1))).any():
            raise ValueError('Invalid OHLC bounds')

    for part in 'ohlc':
        if ((frame[f'bid_{part}'] > frame[f'mid_{part}']) | (frame[f'mid_{part}'] > frame[f'ask_{part}'])).any():
            raise ValueError('Require bid <= mid <= ask')

    return frame


class Conversions:
    def __init__(self, account, datasets):
        self.account = account
        self.datasets = {}
        for pair, source in datasets.items():
            frame = validate_candles(source.candles, source.granularity)
            frame['available'] = frame.time + source.granularity.value
            self.datasets[pair] = frame.set_index('available')

    def convert(self, amount, currency, time):
        # Identity
        if currency == self.account or amount == 0:
            return float(amount)

        for pair, inverse in ((f'{currency}_{self.account}', False), (f'{self.account}_{currency}', True)):
            if pair not in self.datasets:
                continue

            frame = self.datasets[pair]
            index = frame.index.searchsorted(time, side='right') - 1
            if index < 0:
                continue

            row = frame.iloc[index]
            if inverse:
                rate = 1 / (row.ask_c if amount > 0 else row.bid_c)
            else:
                rate = row.bid_c if amount > 0 else row.ask_c

            return float(amount * rate)

        raise ValueError(f'No completed direct/inverse {currency}/{self.account} conversion at {time}')

    def acquisition_cost(self, amount, currency, time):
        """How much of the account currency is required to buy [amount] of the supplied currency."""
        return -self.convert(-amount, currency, time)


class Backtester:
    """Runs simulations sequentially; each run replaces this instance's account state."""
    indicator: Indicator | None = None

    def __init__(self, use_downloaded_currency_pairs=True,
                 data_range_for_plotting=None, config=None):
        self._state: BacktestState | None = None
        if self.indicator is None:
            raise NotImplementedError("Use a concrete strategy backtester")
        self._default_config = config or BacktestConfig(indicator=self.indicator)
        self._validate_config(self._default_config)
        self._config = self._default_config
        self.data_range_for_plotting = data_range_for_plotting
        self.plot_data = {}
        self.results = []
        self.data_client = None
        self.instruments = None
        self.use_downloaded_currency_pairs = use_downloaded_currency_pairs

    @property
    def config(self) -> BacktestConfig:
        """Configuration for the current or most recent run; defaults before the first run."""
        return self._config

    @property
    def state(self) -> BacktestState:
        """Account state for the current or most recently initialised run."""
        if self._state is None:
            raise RuntimeError('Backtest state is not initialised; call run_data() first')
        return self._state

    def run_data(self, pair, strategy_candles, execution_candles=None, conversion_data=None, config=None):
        """Run one independently funded simulation with opening-timestamped UTC candles."""
        config = config or self._default_config
        self._validate_config(config)
        self._config = config
        if len(pair.split('_')) != 2:
            raise ValueError('Pair must be BASE_QUOTE')

        strategy, execution = self._prepare_candles(strategy_candles, execution_candles)
        signals = self._generate_signals(pair, strategy)

        events = collections.deque(signals.loc[signals.signal != 0].to_dict('records'))
        if events and events[0]['available_time'] < execution.time.iloc[0]:
            raise ValueError('Execution history starts after the first actionable signal')

        # Initialise state
        datasets = dict(conversion_data or {})
        datasets.setdefault(pair, ConversionData(execution, self.config.execution_granularity))
        conversions = Conversions(self.config.account_currency, datasets)
        self._state = BacktestState(
            pair=pair,
            balance=self.config.initial_balance,
            last_rollover=execution.time.iloc[0] - pd.Timedelta(microseconds=1),
        )
        last_mark = None
        self._record_equity(execution.time.iloc[0], 0, conversions)

        # Iterate execution candles
        for row in execution.to_dict('records'):
            start = row['time']
            end = start + self.config.execution_granularity.value
            # Positions survive gaps; financing uses the last observable mark.
            gap_mark = last_mark if last_mark is not None else row['bid_o']
            self._accrue_financing(start, gap_mark, conversions)

            while events and events[0]['available_time'] <= start:
                self._accept_signal(events.popleft())

            self._process_candle(row, conversions)

            mark = row['bid_c' if self.state.position is None or self.state.position.signal == 1 else 'ask_c']
            if self.state.last_rollover < end:
                self._accrue_candle_financing(row, conversions)
            self._record_equity(end, mark, conversions)
            last_mark = mark

        self._finish_run(execution.iloc[-1], events, conversions)
        result = self._build_result(signals)
        self.results.append(result)

        self.plot_data[(pair, *self._result_key(self.config))] = signals
        return result

    def _validate_config(self, config):
        if config.indicator != self.indicator:
            raise ValueError(f'{type(self).__name__} requires {self.indicator.name}')

    def _create_signal_generator(self, pair):
        raise NotImplementedError

    def _accept_signal(self, event):
        raise NotImplementedError

    def _process_candle(self, row, conversions):
        raise NotImplementedError

    def _experiment_configs(self, ma_windows):
        raise NotImplementedError

    def _default_execution_granularity(self, trade_granularity):
        raise NotImplementedError

    def _result_key(self, config):
        raise NotImplementedError

    def _plot_result(self, plotter, result, props):
        raise NotImplementedError

    def _prepare_candles(self, strategy_candles, execution_candles):
        """Validate prices and ensure execution intervals respect signal availability."""
        strategy = validate_candles(strategy_candles, self.config.strategy_granularity)

        if execution_candles is None:
            if self.config.execution_granularity != self.config.strategy_granularity:
                raise ValueError('Separate execution candles required for finer simulation')
            execution_candles = strategy

        execution = validate_candles(execution_candles, self.config.execution_granularity)

        if (
            (execution.time.iloc[-1] + self.config.execution_granularity.value)
            < (strategy.time.iloc[-1] + self.config.strategy_granularity.value)
        ):
            raise ValueError('Execution history ends before strategy history completes')

        # Make sure strategy and execution candle boundaries align
        boundaries = pd.Index(strategy.time + self.config.strategy_granularity.value)
        opens = pd.DatetimeIndex(execution.time)
        for boundary in boundaries:
            index = opens.searchsorted(boundary, side='right') - 1
            if index >= 0 and opens[index] < boundary < opens[index] + self.config.execution_granularity.value:
                raise ValueError('Strategy completion cuts through an execution candle')

        return strategy, execution

    def _generate_signals(self, pair: str, strategy: pd.DataFrame) -> pd.DataFrame:
        """Replay the incremental strategy and timestamp when each signal becomes usable."""
        generator = self._create_signal_generator(pair)

        generator.generate_signals_for_backtesting(strategy)
        signals = generator.generate_signals_dataframe()
        signals['available_time'] = signals.time + self.config.strategy_granularity.value
        return signals

    def _record_equity(self, time: pd.Timestamp, mark: float, conversions: Conversions) -> None:
        """Append a valuation snapshot without changing the account or position."""
        position = self.state.position
        unrealised = conversions.convert(position.quote_pnl(mark), self.state.quote_currency, time) if position else 0.0
        self.state.equity.append({
            'time': time,
            'balance': self.state.balance,
            'unrealised_pnl': unrealised,
            'equity': self.state.balance + unrealised,
            'reserved_notional': position.reserved_notional if position else 0.0,
            'position_units': position.signal * position.units if position else 0,
        })

    @staticmethod
    def _next_rollover(after: pd.Timestamp) -> pd.Timestamp:
        """Cutoff is at 22:00 UTC. Return today's cutoff, or tomorrow's cutoff if today's one has already passed."""
        cutoff = after.normalize() + pd.Timedelta(hours=22)
        return cutoff + pd.Timedelta(days=1) if cutoff <= after else cutoff

    def _accrue_financing(
        self,
        until: pd.Timestamp,
        mark: float,
        conversions: Conversions,
    ) -> None:
        """Apply each unprocessed rollover once, including rollovers inside data gaps."""
        cutoff = self._next_rollover(self.state.last_rollover)
        position = self.state.position

        while cutoff <= until:
            if (position is not None) and (position.entry_time < cutoff):
                rates = (self.config.costs.financing_rates or {}).get(self.state.pair, {})
                rate = rates.get('long' if position.signal == 1 else 'short', 0.0)

                amount = position.reserved_notional * rate
                position.financing += amount
                self.state.balance += amount
                self.state.financing.append({
                    'time': cutoff, 'trade_id': position.trade_id, 'amount': amount, 'rate': rate,
                })
                if amount:
                    self._record_equity(cutoff, mark, conversions)

            cutoff += pd.Timedelta(days=1)
        self.state.last_rollover = until

    def _accrue_candle_financing(self, row: dict, conversions: Conversions) -> None:
        """Use the opening mark for interior rollovers; the closing mark is known only at the end."""
        end = row['time'] + self.config.execution_granularity.value
        side = 'bid' if self.state.position is None or self.state.position.signal == 1 else 'ask'

        cutoff = self._next_rollover(self.state.last_rollover)
        while cutoff < end:
            self._accrue_financing(cutoff, row[f'{side}_o'], conversions)
            cutoff += pd.Timedelta(days=1)

        self._accrue_financing(end, row[f'{side}_c'], conversions)

    def _enter_position(
        self,
        order: dict,
        raw_price: float,
        time: pd.Timestamp,
        conversions: Conversions,
        ambiguous: bool = False,
    ) -> bool:
        """Reserve capital and record an entry, or record a capital rejection without a fill."""
        if self.state.position is not None:
            raise ValueError('Cannot enter while a position is already open')

        direction = int(order['signal'])
        slippage = (self.config.costs.slippage_pips or 0) * 10 ** self.config.pip_location
        commission = self.config.costs.commission_per_fill or 0.0
        price = raw_price + direction * slippage

        if price <= 0:
            raise ValueError('Slippage produced a nonpositive price')

        notional = conversions.acquisition_cost(self.config.units, self.state.base_currency, time)
        liquidation = raw_price - direction * max(0.0, order.get('spread', 0.0))
        immediate_loss = max(0.0, -conversions.convert(
            direction * self.config.units * (liquidation - price), self.state.quote_currency, time,
        ))

        required = notional + commission + immediate_loss
        if required > self.state.balance + 1e-9:
            order['status'] = 'rejected'
            self.state.rejected_orders.append({
                'time': time, 'order_id': order['order_id'], 'reason': 'insufficient_capital',
                'required': required, 'available': self.state.balance,
            })
            return False

        self.state.position = Trade(
            trade_id=self.state.next_trade_id,
            pair=self.state.pair,
            signal=direction,
            units=self.config.units,
            signal_time=order['available_time'],
            entry_time=time,
            entry_price=price,
            reserved_notional=notional,
            stop_loss=order.get('stop_loss'),
            take_profit=order.get('take_profit'),
            commission=commission,
            ambiguous=ambiguous,
        )

        self.state.next_trade_id += 1
        self.state.balance -= commission
        order['status'] = 'filled'

        self.state.fills.append({
            'time': time, 'order_id': order['order_id'], 'trade_id': self.state.position.trade_id,
            'action': 'entry', 'direction': direction, 'units': self.config.units,
            'price': price, 'commission': commission, 'reason': 'signal',
        })
        self._record_equity(time, liquidation, conversions)
        return True

    def _exit_position(
        self,
        raw_price: float,
        time: pd.Timestamp,
        reason: str,
        conversions: Conversions,
        order_id: int | None = None,
    ) -> None:
        """Realise P&L, charge exit commission and release the position's reserved capital."""
        position = self.state.position
        if position is None:
            raise ValueError('Cannot exit without an open position')

        slippage = (self.config.costs.slippage_pips or 0) * 10 ** self.config.pip_location
        commission = self.config.costs.commission_per_fill or 0.0
        price = raw_price if reason == 'take_profit' else raw_price - position.signal * slippage

        if price <= 0:
            raise ValueError('Slippage produced a nonpositive price')
        position.exit_price, position.exit_time, position.exit_reason = price, time, reason
        position.gross_pnl = conversions.convert(position.quote_pnl(price), self.state.quote_currency, time)
        position.commission += commission

        self.state.balance += position.gross_pnl - commission
        self.state.fills.append({
            'time': time, 'order_id': order_id, 'trade_id': position.trade_id,
            'action': 'exit', 'direction': -position.signal, 'units': position.units,
            'price': price, 'commission': commission, 'reason': reason,
        })
        self.state.trades.append(position.record())
        self.state.position = None
        self._record_equity(time, 0, conversions)

    def _finish_run(
        self,
        final_row: dict,
        remaining_events: dict,
        conversions: Conversions,
    ) -> None:
        """Liquidate any remaining position and expire orders with no execution opportunity."""
        final_time = final_row['time'] + self.config.execution_granularity.value

        if self.state.position:
            price = final_row['bid_c' if self.state.position.signal == 1 else 'ask_c']
            self._exit_position(price, final_time, 'final_liquidation', conversions)
            self._record_equity(final_time, 0, conversions)

        if self.state.pending_order:
            self.state.pending_order['status'] = 'expired'
            self.state.pending_order = None

        for event in remaining_events:
            self.state.orders.append(dict(event, order_id=len(self.state.orders) + 1, status='expired'))

    def _build_result(self, signals: pd.DataFrame) -> BacktestResult:
        """Expose the completed ledgers and metrics through the existing result interface."""
        equity = pd.DataFrame(self.state.equity)
        trades = pd.DataFrame(self.state.trades)
        metrics = IndicatorEvaluator(self.state.pair, equity, trades, self.config.annual_risk_free_rate).metrics()

        return BacktestResult(
            pair=self.state.pair,
            configuration=self.config,
            signals=signals,
            orders=pd.DataFrame(self.state.orders),
            fills=pd.DataFrame(self.state.fills),
            trades=trades,
            equity=equity,
            rejected_orders=pd.DataFrame(self.state.rejected_orders),
            financing=pd.DataFrame(self.state.financing),
            metrics=metrics,
            ambiguous_candles=self.state.ambiguous_candles,
            omitted_costs=self.config.costs.omitted(self.state.pair),
        )

    def _retrieve_instruments(self):
        """Import the client and retrieve instruments only if they are not available.
        This removes the dependency on OANDA if instruments are provided."""
        from src.client.OandaDataClient import OandaDataClient
        from src.util.Constants import INSTRUMENTS_FILENAME
        if self.instruments is None:
            if self.use_downloaded_currency_pairs and pathlib.Path(INSTRUMENTS_FILENAME).exists():
                self.instruments = pd.read_pickle(INSTRUMENTS_FILENAME)
            else:
                self.data_client = self.data_client or OandaDataClient(live=False)
                self.instruments = self.data_client.get_instruments_and_save_to_file()
        return self.instruments

    def get_price_data_for_pair(self, pair, granularity, from_time, to_time, use_only_downloaded_price_data=False):
        from src.util.Utilities import get_downloaded_price_data_for_pair
        data = get_downloaded_price_data_for_pair(pair, granularity, from_time, to_time)
        if not data.empty:
            data = data.copy()
            data['time'] = pd.to_datetime(data.time, utc=True)
            start, end = pd.to_datetime(from_time, utc=True), pd.to_datetime(to_time, utc=True)
            data = data.loc[(data.time >= start) & (data.time + granularity.value <= end)]
            if not data.empty:
                return data.reset_index(drop=True)
        if use_only_downloaded_price_data:
            raise IOError(f'No cached data for {pair} at {granularity.name}')
        from src.client.OandaDataClient import OandaDataClient
        self.data_client = self.data_client or OandaDataClient(live=False)
        return self.data_client.create_data_for_pair(pair, granularity, pd.to_datetime(from_time, utc=True), pd.to_datetime(to_time, utc=True))

    def run(
        self,
        currencies,
        trade_granularity=Granularity.H4,
        from_time=None,
        to_time=None,
        simulation_granularity=None,
        use_only_downloaded_price_data=False,
        ma_windows=None,
        file_type='csv',
        output_directory='test_results',
        conversion_data=None
    ):
        if from_time is None or to_time is None:
            raise ValueError('Explicit from_time and to_time required')

        defaults = self._default_config
        instruments = self._retrieve_instruments()
        supported = set(instruments.name)
        results = []
        experiments = self._experiment_configs(ma_windows)
        execution_granularity = simulation_granularity or self._default_execution_granularity(trade_granularity)

        for base, quote in itertools.product(currencies, repeat=2):
            pair = f'{base}_{quote}'
            if base == quote or pair not in supported:
                continue

            strategy = self.get_price_data_for_pair(pair, trade_granularity, from_time, to_time, use_only_downloaded_price_data)
            execution = (
                strategy if execution_granularity == trade_granularity
                else self.get_price_data_for_pair(pair, execution_granularity, from_time, to_time, use_only_downloaded_price_data)
            )

            conversions = dict(conversion_data or {})
            for currency in {base, quote} - {defaults.account_currency}:
                direct, inverse = f'{currency}_{defaults.account_currency}', f'{defaults.account_currency}_{currency}'
                conversion_pair = direct if direct in supported else inverse
                if direct in conversions or inverse in conversions or conversion_pair == pair:
                    continue
                if conversion_pair not in supported:
                    raise ValueError(f'No conversion instrument for {currency}')

                # Include a completed observation before the first potential entry.
                data = self.get_price_data_for_pair(conversion_pair, execution_granularity, from_time, to_time, use_only_downloaded_price_data)
                conversions[conversion_pair] = ConversionData(data, execution_granularity)

            for experiment in experiments:
                config = dataclasses.replace(
                    experiment,
                    strategy_granularity=trade_granularity,
                    execution_granularity=execution_granularity,
                    pip_location=int(instruments.loc[instruments.name == pair, 'pipLocation'].iloc[0])
                )
                result = self.run_data(pair, strategy, execution, conversions, config)
                suffix = '_'.join(map(str, self._result_key(config)))
                folder = pathlib.Path(output_directory) / f'{pair}_{self.indicator.name}_{suffix}'
                result.export(folder)

                if file_type in ('pkl', 'pickle'):
                    pd.to_pickle(result, folder / 'result.pkl')
                results.append(result)

        return results

    def plot_results_for_selected_data(self):
        props = self.data_range_for_plotting
        for result in self.results:
            if props and result.pair not in (getattr(props, 'currency_pairs', None) or []):
                continue
            plotter = CandlePlotter(result.signals, props.from_time if props else None, props.to_time if props else None)
            self._plot_result(plotter, result, props)
