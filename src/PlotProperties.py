from datetime import datetime
from typing import List, Tuple


class PlotProperties:
    def __init__(self, currencies: List[str] = None, ma_pairs: List[Tuple[int, int]] = None, from_time: datetime = datetime.now(), to_time: datetime = datetime.now()):
        self.currencies: List[str] = currencies
        self.ma_pairs: List[Tuple[int, int]] = ma_pairs
        self.from_time: datetime = from_time
        self.to_time: datetime = to_time
        if currencies:
            self.currency_pairs: List[str] = self.generate_currency_pairs()

    def generate_currency_pairs(self) -> List[str]:
        currency_pairs: List[str] = []
        for c1 in self.currencies:
            for c2 in self.currencies:
                currency_pairs.append("{}_{}".format(c1, c2))
        return currency_pairs
