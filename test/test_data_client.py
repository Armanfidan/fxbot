import pandas as pd
from src.client.OandaDataClient import OandaDataClient
from src.model.Granularity import Granularity as G


def test_pagination_is_inclusive_and_clips_incomplete_or_overfetched_bars(monkeypatch):
    client = OandaDataClient.__new__(OandaDataClient)
    calls = []
    start = pd.Timestamp('2024-01-01T00:00Z')
    def batch(pair, granularity, from_time, to_time):
        calls.append(from_time)
        if len(calls) == 1:
            return pd.DataFrame({'time':[start,start+pd.Timedelta(hours=4)]}), start+pd.Timedelta(hours=8)
        return pd.DataFrame({'time':[start+pd.Timedelta(hours=8),start+pd.Timedelta(hours=12)]}), start+pd.Timedelta(hours=16)
    monkeypatch.setattr(client,'get_max_candles_possible',batch)
    result = client.get_candles_for_pair('EUR_GBP',G.H4,start,start+pd.Timedelta(hours=13))
    assert calls == [start,start+pd.Timedelta(hours=8)]
    assert result.time.tolist() == [start,start+pd.Timedelta(hours=4),start+pd.Timedelta(hours=8)]


def test_cache_read_clips_old_overfetched_files(monkeypatch):
    from src.app.Backtester import Backtester
    from src.util import Utilities
    data = pd.DataFrame({'time':pd.date_range('2024-01-01',periods=4,freq='4h')})
    monkeypatch.setattr(Utilities,'get_downloaded_price_data_for_pair',lambda *args:data)
    result = Backtester().get_price_data_for_pair('EUR_GBP',G.H4,pd.Timestamp('2024-01-01T04:00Z'),pd.Timestamp('2024-01-01T13:00Z'),True)
    assert result.time.tolist() == [pd.Timestamp('2024-01-01T04:00Z'),pd.Timestamp('2024-01-01T08:00Z')]
