# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

import datetime
import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import cast

import stock_data.downloader as dw
import stock_data.gap_filler as gp
import stock_data.helpers as h
import stock_data.models as m
from airflow.sdk import dag, get_current_context, task

MAX_CONCURRENT_TICKERS = 4


@contextmanager
def db_session() -> Generator[m.DbConnection]:
    """
    Open one connection for the lifetime
    of one task.
    """

    conn = h.db_connection()

    try:
        yield conn
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


@dag(
    dag_id="stock_data",
    start_date=datetime.datetime(2026, 1, 1),
    schedule="0 1 * * *",
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 3,
        "retry_delay": datetime.timedelta(minutes=2),
    },
    tags=["stock", "etl"],
)
def stock_data_dag() -> None:

    @task
    def get_tickers_task() -> list[m.Ticker]:
        return h.get_tickers()

    @task(max_active_tis_per_dagrun=MAX_CONCURRENT_TICKERS)
    def download_ticker(ticker: m.Ticker) -> None:
        ctx = cast(m.IntervalContext, get_current_context())
        end = ctx["data_interval_end"].date()
        start = end - datetime.timedelta(days=6)

        data = dw.get_ticker_data(ticker=ticker, start=start, end=end)
        dw.save_data_csv(df=data, dir=os.environ["SAVE_CSV_PATH"], ticker=ticker)

        rows = h.convert_to_rows(df=data, ticker=ticker)

        with db_session() as conn:
            h.insert_rows(conn=conn, rows=rows, table="raw_prices")

    @task
    def build_gap_fill_inputs(tickers: list[m.Ticker]) -> list[m.GapFillInput]:
        with db_session() as conn:
            last_dates = gp.get_last_date_ticker(conn=conn, tickers=tickers)

        return [
            {"ticker": ticker, "last_date": last_date} for ticker, last_date in last_dates.items()
        ]

    @task(max_active_tis_per_dagrun=MAX_CONCURRENT_TICKERS)
    def gap_fill_ticker(ticker: m.Ticker, last_date: datetime.date) -> None:
        with db_session() as conn:
            existing_data = gp.get_existing_values(conn=conn, last_date=last_date, ticker=ticker)

            if existing_data.empty:
                return

            max_raw_datetime = cast(
                datetime.datetime,
                existing_data["ref_datetime"].max(),
            ).date()

            reference_minutes = gp.get_reference_minutes(
                conn=conn, last_date=last_date, max_date=max_raw_datetime
            )

            seed = gp.get_last_close_from_prices(conn=conn, ticker=ticker, before=last_date)

            df = gp.fill_missing_values(
                datetimes=reference_minutes,
                existing_data=existing_data,
                ticker=ticker,
                seed_close=seed,
            )

            rows = h.convert_to_rows(df=df, ticker=ticker)

            h.insert_rows(conn=conn, rows=rows, table="prices")

    tickers = get_tickers_task()
    ingested = download_ticker.expand(ticker=tickers)

    gap_fill_inputs = build_gap_fill_inputs(tickers=tickers)  # type: ignore[arg-type]
    _ = ingested >> gap_fill_inputs

    gap_fill_ticker.expand_kwargs(gap_fill_inputs)


stock_data_dag()
