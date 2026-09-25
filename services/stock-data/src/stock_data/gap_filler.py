import datetime

import pandas as pd
import psycopg2 as pg


def get_reference_minutes(conn: pg.extensions.connection, last_date: datetime.date) -> pd.DataFrame:
    """
    Get every datetime value for all ticker for
    the specified dates..
    """

    sql_str = f"""
            SELECT DISTINCT
                ref_datetime
            FROM
                raw_prices
            WHERE
                ref_datetime::date >= '{last_date}'
            ORDER BY
                ref_datetime;
            """

    with conn.cursor() as cur:
        cur.execute(sql_str)

        rows = [row[0] for row in cur.fetchall()]

    return pd.DataFrame(data=rows, columns=["ref_datetime"])


def get_last_date_ticker(
    conn: pg.extensions.connection, tickers: list[str]
) -> dict[str, datetime.date]:
    """
    Get last available date from final table for
    all tickers.
    """

    last_dates = {}

    for ticker in tickers:
        sql_str = f"""
                SELECT
                    ref_datetime
                FROM
                    prices
                WHERE
                    ticker = '{ticker}'
                ORDER BY
                    ref_datetime DESC
                LIMIT 1
                """

        with conn.cursor() as cur:
            cur.execute(sql_str)
            row = cur.fetchone()

        if row is None:
            last_dates[ticker] = datetime.date(1900, 1, 1)

        else:
            last_dates[ticker] = row[0].date()

    return last_dates


def get_existing_values(
    conn: pg.extensions.connection, last_date: datetime.date, ticker: str
) -> pd.DataFrame:
    """
    Get exisiting data from last date for
    the specified ticker.
    """

    sql_str = f"""
            SELECT
                *
            FROM
                raw_prices
            WHERE
                ref_datetime::date >= '{last_date}'
                    AND
                ticker = '{ticker}'
            ORDER BY
                ticker,
                ref_datetime;
            """

    with conn.cursor() as cur:
        cur.execute(sql_str)

        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]

    return pd.DataFrame(data=rows, columns=columns)


def get_last_close_from_prices(
    conn: pg.extensions.connection,
    ticker: str,
    before: datetime.date,
) -> float | None:
    """
    Last close in prices for this ticker strictly before
    the before date. None if the ticker has never been inserted.
    """

    sql_str = f"""
        SELECT 
            v_close
        FROM 
            prices
        WHERE 
            ticker = '{ticker}'
                AND 
            ref_datetime::date < '{before}'
        ORDER BY 
            ref_datetime DESC
        LIMIT 1;
    """

    with conn.cursor() as cur:
        cur.execute(sql_str)
        row = cur.fetchone()

    if row:
        res = float(row[0])

    else:
        res = None

    return res


def fill_missing_values(
    datetimes: pd.DataFrame,
    existing_data: pd.DataFrame,
    ticker: str,
    seed_close: float | None = None,
) -> pd.DataFrame:
    """
    For minutes with no trade: carry the last *traded* close
    forward. OHLV are zeroed.

    `seed_close` is the last close available in `prices` for
    this ticker before the window. It primes the carry for
    leading minutes before the ticker's first trade.

    If `seed_close` is None (ticker not yet in `prices`) and
    there is no leading trade either, fall back to backfilling
    from the first trade in the window.
    """

    df = pd.merge(left=datetimes, right=existing_data, how="left", on="ref_datetime")

    if seed_close is not None:
        if pd.isna(df.loc[df.index[0], "v_close"]):
            df.loc[df.index[0], "v_close"] = seed_close

        df["v_close"] = df["v_close"].ffill()

    else:
        df["v_close"] = df["v_close"].ffill().bfill()

    for col in ("v_open", "v_high", "v_low", "v_volume"):
        df[col] = df[col].fillna(0)

    df["ticker"] = ticker

    return df[
        [
            "ticker",
            "ref_datetime",
            "v_open",
            "v_high",
            "v_low",
            "v_close",
            "v_volume",
        ]
    ]
