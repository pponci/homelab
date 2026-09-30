import datetime
from typing import TypeAlias, TypedDict

import psycopg2.extensions

Ticker: TypeAlias = str


Row: TypeAlias = tuple[Ticker, datetime.datetime, float, float, float, float, int]


DbConnection: TypeAlias = psycopg2.extensions.connection


class IntervalContext(TypedDict):
    data_interval_end: datetime.datetime


class GapFillInput(TypedDict):
    ticker: Ticker
    last_date: datetime.date
