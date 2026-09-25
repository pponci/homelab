import json
import os

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
