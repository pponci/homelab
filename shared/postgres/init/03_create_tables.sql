\connect stock_data

CREATE TABLE raw_prices (
    ticker         text        NOT NULL,
    ref_datetime   timestamp   NOT NULL,
    v_open         numeric     NOT NULL,
    v_high         numeric     NOT NULL,
    v_low          numeric     NOT NULL,
    v_close        numeric     NOT NULL,
    v_volume       bigint      NOT NULL,
 
    PRIMARY KEY (ticker, ref_datetime)
);

CREATE INDEX idx_raw_prices_ref_datetime ON raw_prices (ref_datetime);
CREATE INDEX idx_raw_prices_ticker ON raw_prices (ticker);


CREATE TABLE prices (
    ticker         text        NOT NULL,
    ref_datetime   timestamp   NOT NULL,
    v_open         numeric     NOT NULL,
    v_high         numeric     NOT NULL,
    v_low          numeric     NOT NULL,
    v_close        numeric     NOT NULL,
    v_volume       bigint      NOT NULL,
 
    PRIMARY KEY (ticker, ref_datetime)
);

CREATE INDEX idx_prices_ref_datetime ON prices (ref_datetime);
CREATE INDEX idx_prices_ticker ON prices (ticker);