import json
import os

import pandas as pd
import psycopg2 as pg


def get_tickers() -> list[str]:
    """
    Loads the ticker list from the json in path
    from the env file.
    """

    path = os.environ["TICKER_PATH"]

    with open(path, "r") as f:
        tickers = json.load(f)

    return tickers


def db_connection() -> pg.extensions.connection:
    """
    Create connection with
    database.
    """

    conn = pg.connect(
        host=os.environ["DATABASE_HOST"],
        database=os.environ["DATABASE_NAME"],
        user=os.environ["DATABASE_USERNAME"],
        password=os.environ["DATABASE_PASSWORD"],
        port=os.environ["DATABASE_PORT"],
    )

    return conn


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
                r["ref_datetime"].to_pydatetime().replace(tzinfo=None),
                float(r["v_open"]),
                float(r["v_high"]),
                float(r["v_low"]),
                float(r["v_close"]),
                int(r["v_volume"]),
            )
        )

    return rows


def insert_rows(conn: pg.extensions.connection, rows: list[tuple], table: str) -> None:
    """
    Insert given rows into database.
    """

    with conn.cursor() as cur:
        cur.executemany(
            f"""
            INSERT INTO {table}
                (ticker, ref_datetime, v_open, v_high, v_low, v_close, v_volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticker, ref_datetime) DO NOTHING;
            """,
            rows,
        )
