"""
监控 Ondo Global Market 的新资产
"""
import sys
import os
import json
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from modules.util import log, send_telegram

DATA_FILE = "data/ondogm.json"

def fetch_assets():
    url = "https://app.ondo.finance/api/v2/assets"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; GitHub-Actions/1.0)",
        "Accept": "application/json",
    }

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            log(f"Successfully fetched {len(data.get('assets', []))} assets")
            return data
    except urllib.error.HTTPError as e:
        log(f"HTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except Exception as e:
        log(f"Error fetching data: {str(e)}")
        sys.exit(1)


def load_previous_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                log(f"Loaded previous data with {len(data.get('assets', []))} assets")
                return data
        except Exception as e:
            log(f"Error loading previous data: {str(e)}")
    return {"assets": []}


def save_current_data(data):
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
        log(f"Saved current data with {len(data.get('assets', []))} assets")
    except Exception as e:
        log(f"Error saving data: {str(e)}")


def format_asset_message(asset):
    symbol = asset.get("symbol", "N/A")
    underlying = asset.get("underlyingMarket", {})
    ticker = underlying.get("ticker", "N/A")
    name = underlying.get("name", "N/A")

    return f"""[ONDO GM] New Asset
Symbol: {symbol}
Name: {ticker} ({name})"""


def main():
    current_data = fetch_assets()
    current_assets = current_data.get("assets", [])
    last_updated_at = current_data.get('lastUpdatedAt')
    del current_data['lastUpdatedAt']

    previous_data = load_previous_data()
    previous_assets = previous_data.get("assets", [])
    if len(previous_assets) == 0:
        previous_data = current_data
        previous_assets = previous_data.get("assets", [])

    if len(current_assets) > len(previous_assets):
        old_symbols = {
            asset.get("symbol") for asset in previous_assets if asset.get("symbol")
        }
        new_assets = [
            asset
            for asset in current_assets
            if asset.get("symbol") and asset.get("symbol") not in old_symbols
        ]

        if new_assets:
            log(f"Found {len(new_assets)} new assets")
            for asset in new_assets:
                message = format_asset_message(asset)
                send_telegram(message)
        else:
            log("Asset count increased but no new symbols found (possible data change)")
    else:
        log("No new assets detected")

    save_current_data(current_data)


if __name__ == "__main__":
    main()
