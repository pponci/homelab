import datetime
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest as pt
import stock_data.helpers as h

# function : get_ticker()


def write_json(path: Path, data: list) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_returns_tickers_from_env_path(tmp_path: Path, monkeypatch: pt.MonkeyPatch) -> None:
    """
    Test function is able to read env file for path,
    and read correctly the tickers.
    """

    tickers = ["AAPL", "MSFT", "GOOG"]

    file = tmp_path / "tickers.json"

    write_json(file, tickers)

    monkeypatch.setenv("TICKER_PATH", str(file))

    assert h.get_tickers() == tickers


def test_returns_empty_list_when_json_is_empty_list(
    tmp_path: Path, monkeypatch: pt.MonkeyPatch
) -> None:
    """
    Test function returns empty list when no file is empty.
    """

    file = tmp_path / "tickers.json"

    write_json(file, [])

    monkeypatch.setenv("TICKER_PATH", str(file))

    assert h.get_tickers() == []


def test_missing_env_var_raises_keyerror(monkeypatch: pt.MonkeyPatch) -> None:
    """
    Test missing enviroment variable raises
    key error.
    """

    monkeypatch.delenv("TICKER_PATH", raising=False)

    with pt.raises(KeyError):
        h.get_tickers()


def test_missing_file_raises_filenotfounderror(tmp_path: Path, monkeypatch: pt.MonkeyPatch) -> None:
    """
    Test missing file rside file not found error.
    """

    missing_file = tmp_path / "does_not_exist.json"

    monkeypatch.setenv("TICKER_PATH", str(missing_file))

    with pt.raises(FileNotFoundError):
        h.get_tickers()


def test_invalid_json_raises_jsondecodeerror(tmp_path: Path, monkeypatch: pt.MonkeyPatch) -> None:
    """
    Test invalid json raises json decode errror.
    """

    file = tmp_path / "bad.json"
    file.write_text("{not valid json", encoding="utf-8")

    monkeypatch.setenv("TICKER_PATH", str(file))

    with pt.raises(json.JSONDecodeError):
        h.get_tickers()


# function : db_connection()


@pt.fixture
def db_env(monkeypatch: pt.MonkeyPatch) -> dict[str, str]:
    """
    Populate all env vars `db_connection` reads.
    """

    env = {
        "DATABASE_HOST": "localhost",
        "DATABASE_NAME": "stock_data",
        "DATABASE_USERNAME": "stocks_user",
        "DATABASE_PASSWORD": "hunter2",
        "DATABASE_PORT": "5433",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    return env


@patch("stock_data.helpers.pg.connect")
def test_db_connection_returns_connection(mock_connect: MagicMock, db_env: dict[str, str]) -> None:
    """
    Return value is whatever `pg.connect` returns.
    """

    sentinel = object()
    mock_connect.return_value = sentinel

    assert h.db_connection() is sentinel


@patch("stock_data.helpers.pg.connect")
def test_db_connection_passes_env_vars(mock_connect: MagicMock, db_env: dict[str, str]) -> None:
    """
    Connection kwargs are taken verbatim from env vars.
    """

    h.db_connection()

    mock_connect.assert_called_once_with(
        host=db_env["DATABASE_HOST"],
        database=db_env["DATABASE_NAME"],
        user=db_env["DATABASE_USERNAME"],
        password=db_env["DATABASE_PASSWORD"],
        port=db_env["DATABASE_PORT"],
    )


def test_db_connection_missing_env_var_raises_keyerror(
    monkeypatch: pt.MonkeyPatch, db_env: dict[str, str]
) -> None:
    """
    Missing env var surfaces as KeyError (before any network call).
    """

    monkeypatch.delenv("DATABASE_HOST", raising=False)

    with pt.raises(KeyError):
        h.db_connection()


# function : convert_to_rows()


@pt.fixture
def fake_ohlcv() -> pd.DataFrame:
    """
    Two rows of OHLCV data with a tz-aware Datetime index,
    matching what yfinance returns.
    """
    return pd.DataFrame(
        {
            "ref_datetime": pd.to_datetime(["2026-01-02 09:30", "2026-01-02 09:31"]).tz_localize(
                "America/New_York"
            ),
            "v_open": [100.0, 101.0],
            "v_high": [102.0, 103.5],
            "v_low": [99.0, 100.5],
            "v_close": [101.0, 102.0],
            "v_volume": [1_000, 2_000],
        }
    )


def test_convert_to_rows_returns_one_row_per_record(fake_ohlcv: pd.DataFrame) -> None:
    """
    Number of output rows equals number of DataFrame rows.
    """

    rows = h.convert_to_rows(df=fake_ohlcv, ticker="AAPL")

    assert len(rows) == len(fake_ohlcv)


def test_convert_to_rows_produces_expected_tuple(fake_ohlcv: pd.DataFrame) -> None:
    """
    First row has the expected shape and values, in the right order.
    """

    rows = h.convert_to_rows(df=fake_ohlcv, ticker="AAPL")

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

    rows = h.convert_to_rows(df=fake_ohlcv, ticker="AAPL")

    assert rows[0][1].tzinfo is None


def test_convert_to_rows_casts_to_python_scalars(fake_ohlcv: pd.DataFrame) -> None:
    """
    Values must be native Python types so psycopg2 can adapt them.
    """

    rows = h.convert_to_rows(df=fake_ohlcv, ticker="AAPL")
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

    rows = h.convert_to_rows(df=fake_ohlcv, ticker="MSFT")

    assert all(r[0] == "MSFT" for r in rows)


def test_convert_to_rows_empty_dataframe_returns_empty_list() -> None:
    """
    Empty input yields empty output (no crash on `iterrows`).
    """

    empty = pd.DataFrame(columns=["Datetime", "Open", "High", "Low", "Close", "Volume"])

    assert h.convert_to_rows(df=empty, ticker="AAPL") == []


# function : insert_rows()


def test_insert_rows_uses_context_managed_cursor() -> None:
    """
    Cursor is created and entered as a context manager.
    """

    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value

    h.insert_rows(
        conn=conn,
        rows=[("AAPL", datetime.datetime(2026, 1, 2), 1.0, 2.0, 0.5, 1.5, 100)],
        table="raw_prices",
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

    h.insert_rows(conn=conn, rows=rows, table="raw_prices")

    args, _ = cur.executemany.call_args
    assert args[1] == rows


def test_insert_rows_sql_targets_raw_prices_with_on_conflict() -> None:
    """
    SQL inserts into raw_prices with the conflict clause on the PK.
    """
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value

    h.insert_rows(conn=conn, rows=[], table="raw_prices")

    sql = cur.executemany.call_args.args[0]
    normalized = " ".join(sql.split())

    assert "INSERT INTO raw_prices" in normalized
    assert "ON CONFLICT (ticker, ref_datetime) DO NOTHING" in normalized
