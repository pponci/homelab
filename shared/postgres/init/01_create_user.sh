#!/bin/bash

set -euo pipefail

: "${STOCK_DATA_DB_PASSWORD:?STOCK_DATA_DB_PASSWORD is not set}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
    CREATE USER stocks_user WITH PASSWORD '${STOCK_DATA_DB_PASSWORD}';
EOSQL