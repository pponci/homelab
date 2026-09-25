import json
import os


def get_tickers() -> list[str]:
    """
    Loads the ticker list from the json in path
    from the env file.
    """

    path = os.environ["TICKER_PATH"]

    with open(path, "r") as f:
        tickers = json.load(f)

    return tickers
