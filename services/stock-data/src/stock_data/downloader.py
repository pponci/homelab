import datetime
import pathlib

import pandas as pd
import psycopg2 as pg
import yfinance as yf


def get_ticker_data(ticker: str, start: datetime.date, end: datetime.date) -> pd.DataFrame:
    """
    Download the relevant data for one ticker in the given period.
    """

    ticker_obj = yf.Ticker(ticker)

    data = ticker_obj.history(interval="1m", start=start, end=end, actions=False)

    data = data.reset_index(drop=False)

    return data


def save_data_csv(df: pd.DataFrame, dir: str, ticker: str) -> None:
    """
    Save the downloaded ticker data to csv for
    back up.
    """

    session_date = datetime.datetime.now().date()

    month_dir = pathlib.Path(dir) / session_date.strftime("%Y-%m")
    day_dir = month_dir / session_date.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)

    path = day_dir / f"{ticker}_{session_date}.csv"

    df.to_csv(path, index=False)


def convert_to_rows(df: pd.DataFrame, ticker: str) -> list[tuple]:
    """
    Convert data frame into rows for insertion
    into database.
    """

    rows = []

    for _, r in df.iterrows():
        rows.append(
            (
                ticker,
                r["Datetime"].to_pydatetime().replace(tzinfo=None),
                float(r["Open"]),
                float(r["High"]),
                float(r["Low"]),
                float(r["Close"]),
                int(r["Volume"]),
            )
        )

    return rows


def insert_rows(conn: pg.extensions.connection, rows: list[tuple]) -> None:
    """
    Insert given rows into database.
    """

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO raw_prices
                (ticker, ref_datetime, v_open, v_high, v_low, v_close, v_volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticker, ref_datetime) DO NOTHING;
            """,
            rows,
        )
