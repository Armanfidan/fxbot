import os.path

import pandas as pd

import constants


class Instrument:
    def __init__(self, ob):
        self.name = ob['name']
        self.ins_type = ob['type']
        self.displayName = ob['displayName']
        self.pipLocation = pow(10, ob['pipLocation'])  # -4 -> 0.0001
        self.marginRate = ob['marginRate']

    def __repr__(self):
        return str(vars(self))

    @classmethod
    def get_instruments_df(cls):
        instruments: str = Constants.INSTRUMENTS_FILENAME
        if not os.path.isfile(instruments):
            raise IOError("Could not find instrument file '{}'.".format(instruments))
        return pd.read_pickle(instruments)

    @classmethod
    def get_instruments_list(cls):
        df = cls.get_instruments_df()
        return [Instrument(x) for x in df.to_dict(orient='records')]


if __name__ == "__main__":
    print(Instrument.get_instruments_list())
