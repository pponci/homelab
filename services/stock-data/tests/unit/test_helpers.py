import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest as pt
import stock_data.helpers as h

# function : get_ticker()


def write_json(path: Path, data: list) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_returns_tickers_from_env_path(tmp_path: Path, monkeypatch: pt.MonkeyPatch) -> None:
    """
    Test function is able to read env file for path,
    and read correctly the tickers.
    """

    tickers = ["AAPL", "MSFT", "GOOG"]

    file = tmp_path / "tickers.json"

    write_json(file, tickers)

    monkeypatch.setenv("TICKER_PATH", str(file))

    assert h.get_tickers() == tickers


def test_returns_empty_list_when_json_is_empty_list(
    tmp_path: Path, monkeypatch: pt.MonkeyPatch
) -> None:
    """
    Test function returns empty list when no file is empty.
    """

    file = tmp_path / "tickers.json"

    write_json(file, [])

    monkeypatch.setenv("TICKER_PATH", str(file))

    assert h.get_tickers() == []


def test_missing_env_var_raises_keyerror(monkeypatch: pt.MonkeyPatch) -> None:
    """
    Test missing enviroment variable raises
    key error.
    """

    monkeypatch.delenv("TICKER_PATH", raising=False)

    with pt.raises(KeyError):
        h.get_tickers()


def test_missing_file_raises_filenotfounderror(tmp_path: Path, monkeypatch: pt.MonkeyPatch) -> None:
    """
    Test missing file rside file not found error.
    """

    missing_file = tmp_path / "does_not_exist.json"

    monkeypatch.setenv("TICKER_PATH", str(missing_file))

    with pt.raises(FileNotFoundError):
        h.get_tickers()


def test_invalid_json_raises_jsondecodeerror(tmp_path: Path, monkeypatch: pt.MonkeyPatch) -> None:
    """
    Test invalid json raises json decode errror.
    """

    file = tmp_path / "bad.json"
    file.write_text("{not valid json", encoding="utf-8")

    monkeypatch.setenv("TICKER_PATH", str(file))

    with pt.raises(json.JSONDecodeError):
        h.get_tickers()


# function : db_connection()


@pt.fixture
def db_env(monkeypatch: pt.MonkeyPatch) -> dict[str, str]:
    """
    Populate all env vars `db_connection` reads.
    """

    env = {
        "DATABASE_HOST": "localhost",
        "DATABASE_NAME": "stock_data",
        "DATABASE_USERNAME": "stocks_user",
        "DATABASE_PASSWORD": "hunter2",
        "DATABASE_PORT": "5433",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    return env


@patch("stock_data.helpers.pg.connect")
def test_db_connection_returns_connection(mock_connect: MagicMock, db_env: dict[str, str]) -> None:
    """
    Return value is whatever `pg.connect` returns.
    """

    sentinel = object()
    mock_connect.return_value = sentinel

    assert h.db_connection() is sentinel


@patch("stock_data.helpers.pg.connect")
def test_db_connection_passes_env_vars(mock_connect: MagicMock, db_env: dict[str, str]) -> None:
    """
    Connection kwargs are taken verbatim from env vars.
    """

    h.db_connection()

    mock_connect.assert_called_once_with(
        host=db_env["DATABASE_HOST"],
        database=db_env["DATABASE_NAME"],
        user=db_env["DATABASE_USERNAME"],
        password=db_env["DATABASE_PASSWORD"],
        port=db_env["DATABASE_PORT"],
    )


def test_db_connection_missing_env_var_raises_keyerror(
    monkeypatch: pt.MonkeyPatch, db_env: dict[str, str]
) -> None:
    """
    Missing env var surfaces as KeyError (before any network call).
    """

    monkeypatch.delenv("DATABASE_HOST", raising=False)

    with pt.raises(KeyError):
        h.db_connection()
