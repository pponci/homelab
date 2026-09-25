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

    cols = ["ref_datetime", "v_open", "v_high", "v_low", "v_close", "v_volume"]

    if data.empty:
        data = pd.DataFrame(columns=cols)

    data = data.reset_index(drop=False)

    data = data.rename(
        columns={
            "Datetime": "ref_datetime",
            "Open": "v_open",
            "High": "v_high",
            "Low": "v_low",
            "Close": "v_close",
            "Volume": "v_volume",
        }
    )

    return data[["ref_datetime", "v_open", "v_high", "v_low", "v_close", "v_volume"]]


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
