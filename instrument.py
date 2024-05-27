import os.path
from typing import List, Dict

import pandas as pd
from v20.primitives import Instrument

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
        instruments: str = constants.INSTRUMENTS_FILENAME
        if not os.path.isfile(instruments):
            raise IOError("Could not find instrument file '{}'.".format(instruments))
        return pd.read_pickle(instruments)

    @classmethod
    def get_instruments_list(cls):
        df = cls.get_instruments_df()
        return [Instrument(x) for x in df.to_dict(orient='records')]

    @classmethod
    def get_instruments_dict(cls) -> Dict[str, Instrument]:
        instruments: List[Instrument] = cls.get_instruments_list()
        return {k: v for k, v in zip([inst.name for inst in instruments], instruments)}

    @classmethod
    def get_instrument_by_name(cls, pair_name: str) -> Instrument:
        instruments: Dict[str, Instrument] = cls.get_instruments_dict()
        return instruments[pair_name] if pair_name in instruments else None


if __name__ == "__main__":
    print(Instrument.get_instruments_list())
