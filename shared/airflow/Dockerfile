FROM apache/airflow:3.2.2

USER airflow

COPY services/stock-data /opt/stock-data

RUN pip install --no-cache-dir \
    apache-airflow-providers-fab \
    /opt/stock-data