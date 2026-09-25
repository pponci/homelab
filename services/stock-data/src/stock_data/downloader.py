import datetime
import pathlib

import pandas as pd
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


def get_data_latest(df: pd.DataFrame, end: datetime.date) -> pd.DataFrame:
    """
    Get the data of the current day only.
    """

    target_date = end - datetime.timedelta(days=1)

    data = df[df["Datetime"].dt.date >= target_date]

    return data
