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
        {
            "Open": [100.0, 101.0],
            "High": [102.0, 103.5],
            "Low": [99.0, 100.5],
            "Close": [101.0, 102.0],
            "Volume": [1_000, 2_000],
        },
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

    assert list(data.columns) == [
        "ref_datetime",
        "v_open",
        "v_high",
        "v_low",
        "v_close",
        "v_volume",
    ]


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
    assert list(data.columns) == [
        "ref_datetime",
        "v_open",
        "v_high",
        "v_low",
        "v_close",
        "v_volume",
    ]


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
