from datetime import timedelta
from enum import Enum


class Granularity(Enum):
    S5 = timedelta(seconds=5)
    S10 = timedelta(seconds=10)
    S15 = timedelta(seconds=15)
    S30 = timedelta(seconds=30)
    M1 = timedelta(minutes=1)
    M2 = timedelta(minutes=2)
    M3 = timedelta(minutes=3)
    M4 = timedelta(minutes=4)
    M5 = timedelta(minutes=5)
    M10 = timedelta(minutes=10)
    M15 = timedelta(minutes=15)
    M30 = timedelta(minutes=30)
    H1 = timedelta(hours=1)
    H2 = timedelta(hours=2)
    H3 = timedelta(hours=3)
    H4 = timedelta(hours=4)
    H6 = timedelta(hours=6)
    H8 = timedelta(hours=8)
    H12 = timedelta(hours=12)
    D = timedelta(days=1)
    W = timedelta(weeks=1)
    M = timedelta(days=30)
