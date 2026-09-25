import datetime
from datetime import tzinfo
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest as pt
import stock_data.downloader as dw

# function : get_ticker_data()


@pt.fixture
def fake_history() -> pd.DataFrame:
    return pd.DataFrame(
        {"Close": [1.0, 2.0]},
        index=pd.date_range("2026-01-02 09:30", periods=2, freq="1min", name="Datetime"),
    )


@patch("stock_data.downloader.yf.Ticker")
def test_resets_index_into_datetime_column(
    mock_ticker_cls: MagicMock, fake_history: pd.DataFrame
) -> None:
    """
    Test that the function succesfully resets the index, and
    by doing so keeps the datetime as column.
    """

    mock_ticker_obj = MagicMock()
    mock_ticker_obj.history.return_value = fake_history
    mock_ticker_cls.return_value = mock_ticker_obj

    data = dw.get_ticker_data(
        ticker="AAPL", start=datetime.date(2026, 1, 2), end=datetime.date(2026, 1, 3)
    )

    assert "Datetime" in data.columns


@patch("stock_data.downloader.yf.Ticker")
def test_calls_history_with_expected_params(
    mock_ticker_cls: MagicMock, fake_history: pd.DataFrame
) -> None:
    """
    Test the call for the history is made with
    the correct parameters.
    """

    mock_ticker_obj = MagicMock()
    mock_ticker_obj.history.return_value = fake_history
    mock_ticker_cls.return_value = mock_ticker_obj

    start = datetime.date(2026, 1, 2)
    end = datetime.date(2026, 1, 3)

    dw.get_ticker_data(ticker="AAPL", start=start, end=end)

    mock_ticker_obj.history.assert_called_once_with(
        interval="1m", start=start, end=end, actions=False
    )


@patch("stock_data.downloader.yf.Ticker")
def test_calls_history_with_empty_history(mock_ticker_cls: MagicMock) -> None:
    """
    Test that the function handles correclty if a history is
    returned empty.
    """

    empty_history = pd.DataFrame(
        {"Close": []},
        index=pd.DatetimeIndex([], name="Datetime"),
    )

    mock_ticker_obj = MagicMock()
    mock_ticker_obj.history.return_value = empty_history
    mock_ticker_cls.return_value = mock_ticker_obj

    data = dw.get_ticker_data(
        ticker="AAPL", start=datetime.date(2026, 1, 2), end=datetime.date(2026, 1, 3)
    )

    assert data.empty
    assert "Datetime" in data.columns


# function : save_data_csv()


@pt.fixture
def fake_data() -> pd.DataFrame:

    df = pd.DataFrame(
        data={
            "Datetime": pd.to_datetime(
                [
                    "2026-01-01 09:30",
                    "2026-01-01 15:59",
                    "2026-01-02 09:30",
                    "2026-01-02 12:00",
                    "2026-01-03 09:30",
                    "2026-01-03 09:33",
                    "2026-01-03 10:30",
                ]
            ),
            "Close": [1.0, 2.0, 3.0, 4.0, 5.0, 1.0, 3.5],
        }
    )

    return df


def make_frozen_datetime(fixed_date: datetime.date) -> type[datetime.datetime]:
    real_datetime = datetime.datetime

    class FrozenDateTime(real_datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> datetime.datetime:
            return real_datetime.combine(fixed_date, real_datetime.min.time())

    return FrozenDateTime


def test_creates_expected_directory_structure(tmp_path: Path) -> None:
    """
    Test the function creates the expected directory
    structure.
    """

    df = pd.DataFrame()
    fixed_date = datetime.date(2026, 3, 15)

    with patch("stock_data.downloader.datetime.datetime", make_frozen_datetime(fixed_date)):
        dw.save_data_csv(df=df, dir=str(tmp_path), ticker="AAPL")

    expected_dir = tmp_path / "2026-03" / "2026-03-15"

    assert expected_dir.is_dir()


def test_creates_expected_filename(tmp_path: Path) -> None:
    """
    Test the function creates the right file name.
    """

    df = pd.DataFrame()
    fixed_date = datetime.date(2026, 3, 15)

    with patch("stock_data.downloader.datetime.datetime", make_frozen_datetime(fixed_date)):
        dw.save_data_csv(df=df, dir=str(tmp_path), ticker="AAPL")

    expected_file = tmp_path / "2026-03" / "2026-03-15" / "AAPL_2026-03-15.csv"

    assert expected_file.is_file()


def test_saved_df_content_matches(tmp_path: Path, fake_data: pd.DataFrame) -> None:
    """
    Test the function saves the correct data.
    """

    fixed_date = datetime.date(2026, 3, 15)

    with patch("stock_data.downloader.datetime.datetime", make_frozen_datetime(fixed_date)):
        dw.save_data_csv(df=fake_data, dir=str(tmp_path), ticker="AAPL")

    file_path = tmp_path / "2026-03" / "2026-03-15" / "AAPL_2026-03-15.csv"
    read_data = pd.read_csv(file_path, parse_dates=["Datetime"])

    assert fake_data.equals(read_data)


# function : convert_to_rows()


@pt.fixture
def fake_ohlcv() -> pd.DataFrame:
    """
    Two rows of OHLCV data with a tz-aware Datetime index,
    matching what yfinance returns.
    """
    return pd.DataFrame(
        {
            "Datetime": pd.to_datetime(["2026-01-02 09:30", "2026-01-02 09:31"]).tz_localize(
                "America/New_York"
            ),
            "Open": [100.0, 101.0],
            "High": [102.0, 103.5],
            "Low": [99.0, 100.5],
            "Close": [101.0, 102.0],
            "Volume": [1_000, 2_000],
        }
    )


def test_convert_to_rows_returns_one_row_per_record(fake_ohlcv: pd.DataFrame) -> None:
    """
    Number of output rows equals number of DataFrame rows.
    """

    rows = dw.convert_to_rows(df=fake_ohlcv, ticker="AAPL")

    assert len(rows) == len(fake_ohlcv)


def test_convert_to_rows_produces_expected_tuple(fake_ohlcv: pd.DataFrame) -> None:
    """
    First row has the expected shape and values, in the right order.
    """

    rows = dw.convert_to_rows(df=fake_ohlcv, ticker="AAPL")

    assert rows[0] == (
        "AAPL",
        datetime.datetime(2026, 1, 2, 9, 30),
        100.0,
        102.0,
        99.0,
        101.0,
        1_000,
    )


def test_convert_to_rows_strips_timezone(fake_ohlcv: pd.DataFrame) -> None:
    """
    tzinfo must be removed so it can be inserted into a `timestamp` column.
    """

    rows = dw.convert_to_rows(df=fake_ohlcv, ticker="AAPL")

    assert rows[0][1].tzinfo is None


def test_convert_to_rows_casts_to_python_scalars(fake_ohlcv: pd.DataFrame) -> None:
    """
    Values must be native Python types so psycopg2 can adapt them.
    """

    rows = dw.convert_to_rows(df=fake_ohlcv, ticker="AAPL")
    _, dt, open, high, low, close, volume = rows[0]

    assert type(dt) is datetime.datetime
    assert type(open) is float
    assert type(high) is float
    assert type(low) is float
    assert type(close) is float
    assert type(volume) is int


def test_convert_to_rows_uses_ticker_argument(fake_ohlcv: pd.DataFrame) -> None:
    """
    Ticker is taken from the argument, not from the DataFrame.
    """

    rows = dw.convert_to_rows(df=fake_ohlcv, ticker="MSFT")

    assert all(r[0] == "MSFT" for r in rows)


def test_convert_to_rows_empty_dataframe_returns_empty_list() -> None:
    """
    Empty input yields empty output (no crash on `iterrows`).
    """

    empty = pd.DataFrame(columns=["Datetime", "Open", "High", "Low", "Close", "Volume"])

    assert dw.convert_to_rows(df=empty, ticker="AAPL") == []


# function : insert_rows()


def test_insert_rows_uses_context_managed_cursor() -> None:
    """
    Cursor is created and entered as a context manager.
    """

    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value

    dw.insert_rows(
        conn=conn, rows=[("AAPL", datetime.datetime(2026, 1, 2), 1.0, 2.0, 0.5, 1.5, 100)]
    )

    conn.cursor.assert_called_once()
    cur.executemany.assert_called_once()


def test_insert_rows_passes_rows_to_executemany() -> None:
    """
    The `rows` list is forwarded unchanged to `executemany`.
    """

    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value

    rows = [
        ("AAPL", datetime.datetime(2026, 1, 2, 9, 30), 100.0, 102.0, 99.0, 101.0, 1_000),
        ("AAPL", datetime.datetime(2026, 1, 2, 9, 31), 101.0, 103.5, 100.5, 102.0, 2_000),
    ]

    dw.insert_rows(conn=conn, rows=rows)

    args, _ = cur.executemany.call_args
    assert args[1] == rows


def test_insert_rows_sql_targets_raw_prices_with_on_conflict() -> None:
    """
    SQL inserts into raw_prices with the conflict clause on the PK.
    """
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value

    dw.insert_rows(conn=conn, rows=[])

    sql = cur.executemany.call_args.args[0]
    normalized = " ".join(sql.split())

    assert "INSERT INTO raw_prices" in normalized
    assert "ON CONFLICT (ticker, ref_datetime) DO NOTHING" in normalized
