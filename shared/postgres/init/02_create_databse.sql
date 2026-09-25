CREATE DATABASE stock_data OWNER stocks_user;

GRANT ALL PRIVILEGES ON DATABASE stock_data TO stocks_user;

\connect stock_data

GRANT ALL ON SCHEMA public TO stocks_user;