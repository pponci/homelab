# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

import datetime
import os
from typing import cast

import stock_data.downloader as dw
import stock_data.helpers as h
import stock_data.models as m
from airflow.sdk import dag, get_current_context, task


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

    @task(max_active_tis_per_dagrun=4)
    def download_ticker(ticker: m.Ticker) -> None:
        ctx = cast(m.IntervalContext, get_current_context())
        end = ctx["data_interval_end"].date()
        start = end - datetime.timedelta(days=6)

        data = dw.get_ticker_data(ticker=ticker, start=start, end=end)
        dw.save_data_csv(df=data, dir=os.environ["SAVE_CSV_PATH"], ticker=ticker)

        rows = h.convert_to_rows(df=data, ticker=ticker)

        conn = h.db_connection()

        try:
            h.insert_rows(conn=conn, rows=rows, table="raw_prices")
            conn.commit()
        finally:
            conn.close()

    tickers = get_tickers_task()
    download_ticker.expand(ticker=tickers)


stock_data_dag()
