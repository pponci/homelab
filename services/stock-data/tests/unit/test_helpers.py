import json
from pathlib import Path

import pytest as pt
from stock_data.helpers import get_tickers

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

    assert get_tickers() == tickers


def test_returns_empty_list_when_json_is_empty_list(
    tmp_path: Path, monkeypatch: pt.MonkeyPatch
) -> None:
    """
    Test function returns empty list when no file is empty.
    """

    file = tmp_path / "tickers.json"

    write_json(file, [])

    monkeypatch.setenv("TICKER_PATH", str(file))

    assert get_tickers() == []


def test_missing_env_var_raises_keyerror(monkeypatch: pt.MonkeyPatch) -> None:
    """
    Test missing enviroment variable raises
    key error.
    """

    monkeypatch.delenv("TICKER_PATH", raising=False)

    with pt.raises(KeyError):
        get_tickers()


def test_missing_file_raises_filenotfounderror(tmp_path: Path, monkeypatch: pt.MonkeyPatch) -> None:
    """
    Test missing file rside file not found error.
    """

    missing_file = tmp_path / "does_not_exist.json"

    monkeypatch.setenv("TICKER_PATH", str(missing_file))

    with pt.raises(FileNotFoundError):
        get_tickers()


def test_invalid_json_raises_jsondecodeerror(tmp_path: Path, monkeypatch: pt.MonkeyPatch) -> None:
    """
    Test invalid json raises json decode errror.
    """

    file = tmp_path / "bad.json"
    file.write_text("{not valid json", encoding="utf-8")

    monkeypatch.setenv("TICKER_PATH", str(file))

    with pt.raises(json.JSONDecodeError):
        get_tickers()
