import os
from http.client import HTTPException

import pandas as pd
import v20

import utils
import instrument
import ma_result

pd.set_option('display.max_columns', None)

def is_trade(row):
    if row.DIFF >= 0 and row.DIFF_PREV < 0:
        return 1
    if row.DIFF <= 0 and row.DIFF_PREV > 0:
        return -1
    return 0 


def get_ma_col(ma):
    return f"MA_{ma}"


def evaluate_pair(i_pair, mashort, malong, price_data):

    price_data['DIFF'] = price_data[get_ma_col(mashort)] - price_data[get_ma_col(malong)]
    price_data['DIFF_PREV'] = price_data.DIFF.shift(1)
    price_data['IS_TRADE'] = price_data.apply(is_trade, axis=1)
    
    df_trades = price_data[price_data.IS_TRADE!=0].copy()
    df_trades["DELTA"] = (df_trades.mid_c.diff() / i_pair.pipLocation).shift(-1)
    df_trades["GAIN"] = df_trades["DELTA"] * df_trades["IS_TRADE"]

    #print(f"{i_pair.name} {mashort} {malong} trades:{df_trades.shape[0]} gain:{df_trades['GAIN'].sum():.0f}")

    return ma_result.MAResult(
        df_trades=df_trades,
        pairname=i_pair.name,
        params={'mashort' : mashort, 'malong' : malong}
    )

def flatten_candle(candle):
    """
    Flatten a candle dictionary.
    :param candle: The candle to flatten. Do not pass the Candlestick object - rather do vars(candle) before passing.
    :return: The flattened candle.
    """
    prices = ['mid', 'bid', 'ask']
    candle_dict = {}
    for price in prices:
        candle_dict.update({'{}_{}'.format(price, subprice): value for subprice, value in vars(candle[price]).items()})
    return {'time': candle['time'], 'volume': candle['volume']} | candle_dict


def get_price_data(pairname, granularity):
    # api = v20.Context(
    #     hostname='api-fxpractice.oanda.com',
    #     token='5aaa2c5c4d07318128360337e0bf741c-44568b8187714b837925c9bd519f0909'
    # )
    #
    # response: v20.response = api.instrument.candles(instrument=pairname, count=4000, granularity=granularity, price='MBA')
    # if response.status != 200:
    #     raise HTTPException("Cannot get candlesticks for currency pair {}, status code: {}".format(pairname, response.status))
    # candles: pd.DataFrame = pd.DataFrame([flatten_candle(vars(candle)) for candle in response.body['candles'] if candle.complete])
    # columns = [col for col in candles.columns if col not in ['time', 'volume']]
    # candles[columns] = candles[columns].apply(pd.to_numeric, errors='coerce')

    candles = pd.read_pickle('his_data/{}_{}.pkl'.format(pairname, granularity))
    candles.rename(columns={'mid.c': 'mid_c', 'bid.c': 'bid_c', 'ask.c': 'ask_c'}, inplace=True)
    return candles[['time', 'mid_c']]


def process_data(ma_short, ma_long, price_data):
    ma_list = set(ma_short + ma_long)
    
    for ma in ma_list:  
        price_data[get_ma_col(ma)] = price_data.mid_c.rolling(window=ma).mean()
    
    return price_data

def process_results(results):
    results_list = [r.result_ob() for r in results]
    final_df = pd.DataFrame.from_dict(results_list)

    final_df.to_pickle('ma_test_res.pkl')
    print(final_df.shape, final_df.num_trades.sum())


def get_test_pairs(pair_str):
    existing_pairs = instrument.Instrument.get_instruments_dict().keys()
    pairs = pair_str.split(",")
    
    test_list = []
    for p1 in pairs:
        for p2 in pairs:
            p = f"{p1}_{p2}"
            if p in existing_pairs:
                test_list.append(p)
    
    print(test_list)
    return test_list

def run():
    currencies = "GBP,EUR,USD,CAD,JPY,NZD,CHF"
    granularity = "H1"
    ma_short = [4, 8, 16, 24, 32, 64]
    ma_long = [8, 16, 32, 64, 96, 128, 256]
    test_pairs = get_test_pairs(currencies)    

    results = []
    for pairname in test_pairs:
        print("running..", pairname)
        i_pair = instrument.Instrument.get_instruments_dict()[pairname]

        try:
            price_data = get_price_data(pairname, granularity)
        except FileNotFoundError:
            continue
        price_data = process_data(ma_short, ma_long, price_data)

        for _malong in ma_long:
            for _mashort in ma_short:
                if _mashort >= _malong:
                    continue
                results.append(evaluate_pair(i_pair, _mashort, _malong, price_data.copy()))

    process_results(results)



if __name__ == "__main__":
    run()