import datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest as pt
import stock_data.gap_filler as gp


def make_conn() -> tuple[MagicMock, MagicMock]:
    """
    Return (conn, cur) where `cur` is what
    `with conn.cursor() as cur:` binds to.
    """
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value

    return conn, cur


# function : get_reference_minutes()


def test_get_reference_minutes_returns_ref_datetime_column() -> None:
    """
    Result is a one-column DataFrame named `ref_datetime`.
    """

    conn, cur = make_conn()
    cur.fetchall.return_value = [
        (datetime.datetime(2026, 1, 2, 9, 30),),
        (datetime.datetime(2026, 1, 2, 9, 31),),
    ]

    result = gp.get_reference_minutes(conn=conn, last_date=datetime.date(2026, 1, 2))

    assert list(result.columns) == ["ref_datetime"]
    assert len(result) == 2


def test_get_reference_minutes_extracts_first_column() -> None:
    """
    The datetime is taken from the first column of each row.
    """

    conn, cur = make_conn()
    expected = [
        datetime.datetime(2026, 1, 2, 9, 30),
        datetime.datetime(2026, 1, 2, 9, 31),
    ]
    cur.fetchall.return_value = [(ts,) for ts in expected]

    result = gp.get_reference_minutes(conn=conn, last_date=datetime.date(2026, 1, 2))

    assert result["ref_datetime"].tolist() == expected


def test_get_reference_minutes_empty_result_still_has_column() -> None:
    """
    Empty result gives an empty DataFrame with the column present.
    """

    conn, cur = make_conn()
    cur.fetchall.return_value = []

    result = gp.get_reference_minutes(conn=conn, last_date=datetime.date(2026, 1, 2))

    assert result.empty
    assert list(result.columns) == ["ref_datetime"]


def test_get_reference_minutes_query_contains_last_date() -> None:
    """
    The f-string interpolation of last_date makes it into the SQL.
    """

    conn, cur = make_conn()
    cur.fetchall.return_value = []

    gp.get_reference_minutes(conn=conn, last_date=datetime.date(2026, 1, 2))

    sql = cur.execute.call_args.args[0]
    assert "2026-01-02" in sql
    assert "raw_prices" in sql


# function : get_last_date_ticker()


def test_get_last_date_ticker_returns_date_per_ticker() -> None:
    """
    Each ticker with rows maps to its latest ref_datetime as a date.
    """

    conn, cur = make_conn()
    cur.fetchone.side_effect = [
        (datetime.datetime(2026, 1, 2, 15, 59),),
        (datetime.datetime(2026, 1, 3, 15, 58),),
    ]

    result = gp.get_last_date_ticker(conn=conn, tickers=["AAPL", "MSFT"])

    assert result == {
        "AAPL": datetime.date(2026, 1, 2),
        "MSFT": datetime.date(2026, 1, 3),
    }


def test_get_last_date_ticker_uses_sentinel_for_missing_ticker() -> None:
    """
    Tickers absent from `prices` get the 1900-01-01 sentinel.
    """

    conn, cur = make_conn()
    cur.fetchone.side_effect = [None]

    result = gp.get_last_date_ticker(conn=conn, tickers=["NEWCO"])

    assert result == {"NEWCO": datetime.date(1900, 1, 1)}


def test_get_last_date_ticker_mixes_present_and_missing() -> None:
    """
    Present and missing tickers coexist in the returned dict.
    """

    conn, cur = make_conn()
    cur.fetchone.side_effect = [
        (datetime.datetime(2026, 1, 2, 15, 59),),
        None,
        (datetime.datetime(2026, 1, 4, 12, 0),),
    ]

    result = gp.get_last_date_ticker(conn=conn, tickers=["AAPL", "NEWCO", "MSFT"])

    assert result["AAPL"] == datetime.date(2026, 1, 2)
    assert result["NEWCO"] == datetime.date(1900, 1, 1)
    assert result["MSFT"] == datetime.date(2026, 1, 4)


def test_get_last_date_ticker_empty_input_returns_empty_dict() -> None:
    """
    No tickers → no queries, empty dict.
    """

    conn, _ = make_conn()

    result = gp.get_last_date_ticker(conn=conn, tickers=[])

    assert result == {}
    conn.cursor.assert_not_called()


def test_get_last_date_ticker_queries_prices_table() -> None:
    """
    The query targets the derived `prices` table, not `raw_prices`.
    """

    conn, cur = make_conn()
    cur.fetchone.side_effect = [(datetime.datetime(2026, 1, 2),)]

    gp.get_last_date_ticker(conn=conn, tickers=["AAPL"])

    sql = cur.execute.call_args.args[0]
    assert "FROM" in sql
    assert "prices" in sql
    assert "raw_prices" not in sql
    assert "LIMIT 1" in sql


# function : get_existing_values()


def test_get_existing_values_returns_dataframe_with_db_columns() -> None:
    """
    Columns come from `cur.description`, order preserved.
    """

    conn, cur = make_conn()
    cur.description = [
        ("ticker",),
        ("ref_datetime",),
        ("v_open",),
        ("v_high",),
        ("v_low",),
        ("v_close",),
        ("v_volume",),
    ]
    cur.fetchall.return_value = [
        (
            "AAPL",
            datetime.datetime(2026, 1, 2, 9, 30),
            100.0,
            102.0,
            99.0,
            101.0,
            1000,
        ),
    ]

    result = gp.get_existing_values(conn=conn, last_date=datetime.date(2026, 1, 2), ticker="AAPL")

    assert list(result.columns) == [
        "ticker",
        "ref_datetime",
        "v_open",
        "v_high",
        "v_low",
        "v_close",
        "v_volume",
    ]
    assert len(result) == 1
    assert result.iloc[0]["ticker"] == "AAPL"
    assert result.iloc[0]["v_close"] == 101.0


def test_get_existing_values_empty_result_keeps_columns() -> None:
    """
    Empty result still carries the column names from `description`.
    """

    conn, cur = make_conn()
    cur.description = [
        ("ticker",),
        ("ref_datetime",),
        ("v_open",),
        ("v_high",),
        ("v_low",),
        ("v_close",),
        ("v_volume",),
    ]
    cur.fetchall.return_value = []

    result = gp.get_existing_values(conn=conn, last_date=datetime.date(2026, 1, 2), ticker="AAPL")

    assert result.empty
    assert "v_close" in result.columns


# function : get_last_close_from_prices()


def test_get_last_close_from_prices_returns_float() -> None:
    """
    A present row yields a Python float, not Decimal/None.
    """

    conn, cur = make_conn()
    cur.fetchone.return_value = (101.25,)

    result = gp.get_last_close_from_prices(
        conn=conn, ticker="AAPL", before=datetime.date(2026, 1, 2)
    )

    assert result == 101.25
    assert type(result) is float


def test_get_last_close_from_prices_returns_none_when_absent() -> None:
    """
    No prior row → None, so the caller can fall back to bfill.
    """

    conn, cur = make_conn()
    cur.fetchone.return_value = None

    result = gp.get_last_close_from_prices(
        conn=conn, ticker="AAPL", before=datetime.date(2026, 1, 2)
    )

    assert result is None


def test_get_last_close_from_prices_query_uses_strict_before() -> None:
    """
    The comparison must be `<`, not `<=`, so the current session doesn't self-seed.
    """

    conn, cur = make_conn()
    cur.fetchone.return_value = None

    gp.get_last_close_from_prices(conn=conn, ticker="AAPL", before=datetime.date(2026, 1, 2))

    sql = cur.execute.call_args.args[0]
    assert "<" in sql
    assert "2026-01-02" in sql
    assert "prices" in sql
    assert "ORDER BY" in sql
    assert "DESC" in sql
    assert "LIMIT 1" in sql


# function : fill_missing_values()


@pt.fixture
def reference_minutes() -> pd.DataFrame:
    """
    A 3-minute grid, as `get_reference_minutes` would return.
    """

    return pd.DataFrame(
        {
            "ref_datetime": pd.to_datetime(
                [
                    "2026-01-02 09:30",
                    "2026-01-02 09:31",
                    "2026-01-02 09:32",
                ]
            )
        }
    )


@pt.fixture
def existing_trades() -> pd.DataFrame:
    """
    Trades at 09:30 and 09:32; 09:31 is a gap.
    """

    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL"],
            "ref_datetime": pd.to_datetime(["2026-01-02 09:30", "2026-01-02 09:32"]),
            "v_open": [100.0, 102.0],
            "v_high": [101.0, 103.0],
            "v_low": [99.5, 101.5],
            "v_close": [100.5, 102.5],
            "v_volume": [1_000, 2_000],
        }
    )


def test_fill_merges_on_ref_datetime(
    reference_minutes: pd.DataFrame, existing_trades: pd.DataFrame
) -> None:
    """
    One output row per input grid row.
    """

    result = gp.fill_missing_values(
        datetimes=reference_minutes,
        existing_data=existing_trades,
        ticker="AAPL",
    )

    assert len(result) == len(reference_minutes)


def test_fill_preserves_real_trades(
    reference_minutes: pd.DataFrame, existing_trades: pd.DataFrame
) -> None:
    """
    Traded minutes keep their OHLCV untouched.
    """

    result = gp.fill_missing_values(
        datetimes=reference_minutes,
        existing_data=existing_trades,
        ticker="AAPL",
    )
    result = result.set_index("ref_datetime")

    assert result.loc["2026-01-02 09:30", "v_close"] == 100.5
    assert result.loc["2026-01-02 09:30", "v_volume"] == 1_000
    assert result.loc["2026-01-02 09:32", "v_close"] == 102.5


def test_fill_carries_close_forward_into_gaps(
    reference_minutes: pd.DataFrame, existing_trades: pd.DataFrame
) -> None:
    """
    The 09:31 gap gets the 09:30 close.
    """

    result = gp.fill_missing_values(
        datetimes=reference_minutes,
        existing_data=existing_trades,
        ticker="AAPL",
    )
    result = result.set_index("ref_datetime")

    assert result.loc["2026-01-02 09:31", "v_close"] == 100.5


def test_fill_zeroes_ohlv_in_gaps(
    reference_minutes: pd.DataFrame, existing_trades: pd.DataFrame
) -> None:
    """
    A filled minute has 0 open/high/low/volume.
    """

    result = gp.fill_missing_values(
        datetimes=reference_minutes,
        existing_data=existing_trades,
        ticker="AAPL",
    )
    gap = result[result["ref_datetime"] == pd.Timestamp("2026-01-02 09:31")].iloc[0]

    assert gap["v_open"] == 0
    assert gap["v_high"] == 0
    assert gap["v_low"] == 0
    assert gap["v_volume"] == 0


def test_fill_adds_ticker_column(
    reference_minutes: pd.DataFrame, existing_trades: pd.DataFrame
) -> None:
    """
    `ticker` is set from the argument, not the merged data.
    """

    result = gp.fill_missing_values(
        datetimes=reference_minutes,
        existing_data=existing_trades,
        ticker="MSFT",
    )

    assert (result["ticker"] == "MSFT").all()


def test_fill_output_column_order(
    reference_minutes: pd.DataFrame, existing_trades: pd.DataFrame
) -> None:
    """
    Column order matches the INSERT statement in downloader.py.
    """

    result = gp.fill_missing_values(
        datetimes=reference_minutes,
        existing_data=existing_trades,
        ticker="AAPL",
    )

    assert list(result.columns) == [
        "ticker",
        "ref_datetime",
        "v_open",
        "v_high",
        "v_low",
        "v_close",
        "v_volume",
    ]


def test_fill_seed_primes_leading_gap() -> None:
    """
    A leading gap (no trade until later in the window) uses the seed close.
    """

    grid = pd.DataFrame(
        {
            "ref_datetime": pd.to_datetime(
                ["2026-01-02 09:30", "2026-01-02 09:31", "2026-01-02 09:32"]
            )
        }
    )
    trades = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "ref_datetime": pd.to_datetime(["2026-01-02 09:32"]),
            "v_open": [102.0],
            "v_high": [103.0],
            "v_low": [101.5],
            "v_close": [102.5],
            "v_volume": [2_000],
        }
    )

    result = gp.fill_missing_values(
        datetimes=grid,
        existing_data=trades,
        ticker="AAPL",
        seed_close=99.0,
    )
    result = result.set_index("ref_datetime")

    assert result.loc["2026-01-02 09:30", "v_close"] == 99.0
    assert result.loc["2026-01-02 09:31", "v_close"] == 99.0
    assert result.loc["2026-01-02 09:32", "v_close"] == 102.5


def test_fill_seed_ignored_when_first_minute_already_traded(
    reference_minutes: pd.DataFrame, existing_trades: pd.DataFrame
) -> None:
    """
    If the first row already has a trade, the seed is not applied.
    """

    result = gp.fill_missing_values(
        datetimes=reference_minutes,
        existing_data=existing_trades,
        ticker="AAPL",
        seed_close=99.0,
    )
    result = result.set_index("ref_datetime")

    assert result.loc["2026-01-02 09:30", "v_close"] == 100.5


def test_fill_without_seed_backfills_leading_gap() -> None:
    """
    No seed and no trade until later → leading rows take the first close.
    """

    grid = pd.DataFrame(
        {
            "ref_datetime": pd.to_datetime(
                ["2026-01-02 09:30", "2026-01-02 09:31", "2026-01-02 09:32"]
            )
        }
    )
    trades = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "ref_datetime": pd.to_datetime(["2026-01-02 09:32"]),
            "v_open": [102.0],
            "v_high": [103.0],
            "v_low": [101.5],
            "v_close": [102.5],
            "v_volume": [2_000],
        }
    )

    result = gp.fill_missing_values(
        datetimes=grid,
        existing_data=trades,
        ticker="AAPL",
        seed_close=None,
    )
    result = result.set_index("ref_datetime")

    assert result.loc["2026-01-02 09:30", "v_close"] == 102.5
    assert result.loc["2026-01-02 09:31", "v_close"] == 102.5
    assert result.loc["2026-01-02 09:32", "v_close"] == 102.5


def test_fill_without_seed_and_no_trades_leaves_close_nan() -> None:
    """
    No seed, no trades: OHLCV are zeroed, v_close stays NaN.
    Documents current behaviour — callers must skip these rows
    or the NOT NULL constraint on `prices.v_close` will reject them.
    """

    grid = pd.DataFrame({"ref_datetime": pd.to_datetime(["2026-01-02 09:30", "2026-01-02 09:31"])})
    empty = pd.DataFrame(
        columns=["ticker", "ref_datetime", "v_open", "v_high", "v_low", "v_close", "v_volume"]
    )

    result = gp.fill_missing_values(
        datetimes=grid,
        existing_data=empty,
        ticker="AAPL",
        seed_close=None,
    )

    assert result["v_close"].isna().all()
    assert (result["v_open"] == 0).all()
    assert (result["v_volume"] == 0).all()


def test_fill_gap_after_last_trade_is_carried_forward(
    reference_minutes: pd.DataFrame, existing_trades: pd.DataFrame
) -> None:
    """
    Once a close is established, subsequent gaps keep carrying it.
    """

    grid = pd.concat(
        [
            reference_minutes,
            pd.DataFrame({"ref_datetime": pd.to_datetime(["2026-01-02 09:33"])}),
        ],
        ignore_index=True,
    )

    result = gp.fill_missing_values(
        datetimes=grid,
        existing_data=existing_trades,
        ticker="AAPL",
    )
    result = result.set_index("ref_datetime")

    assert result.loc["2026-01-02 09:33", "v_close"] == 102.5
    assert result.loc["2026-01-02 09:33", "v_volume"] == 0
