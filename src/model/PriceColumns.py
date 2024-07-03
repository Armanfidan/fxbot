from PriceType import PriceType


class PriceColumns:
    def __init__(self, price_type: PriceType):
        self.type: str = price_type.value
        self.o: str = '{}_o'.format(price_type.value)
        self.h: str = '{}_h'.format(price_type.value)
        self.l: str = '{}_l'.format(price_type.value)
        self.c: str = '{}_c'.format(price_type.value)
