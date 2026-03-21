"""
监控 Ondo Global Market 的新资产
"""
import sys
import os
import json
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from modules.util import log, send_telegram, send_esp32

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
    return {"assets": [], "first_post": None}


def save_current_data(assets_symbols, first_post=None):
    """保存资产符号列表和first_post到文件"""
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        data = {
            "assets": assets_symbols,
            "first_post": first_post
        }
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
        log(f"Saved {len(assets_symbols)} asset symbols to data file")
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

    current_symbols = [asset.get("symbol") for asset in current_assets if asset.get("symbol")]

    previous_data = load_previous_data()
    previous_symbols = previous_data.get("assets", [])

    if len(previous_symbols) == 0:
        previous_symbols = current_symbols

    # feed 1 for ONDO GM
    first_post_id = previous_data.get("first_post")

    if first_post_id:
        result = send_esp32(f"Total: {len(current_symbols)}", post_id=first_post_id)
        log(f"Updated existing ESP32 post with ID: {first_post_id}")
    else:
        result = send_esp32(f"Total: {len(current_symbols)}", feed_id="1")
        if result:
            first_post_id = result
            log(f"Created new ESP32 post with ID: {result}")
        else:
            log(f"Failed to get post ID from send_esp32, result: {result}")

    if len(current_symbols) > len(previous_symbols):
        old_symbols_set = set(previous_symbols)
        new_assets = [
            asset for asset in current_assets
            if asset.get("symbol") and asset.get("symbol") not in old_symbols_set
        ]

        if new_assets:
            log(f"Found {len(new_assets)} new assets")
            for asset in new_assets:
                message = format_asset_message(asset)
                symbol = asset.get("symbol", "N/A")
                name = asset.get("underlyingMarket", {}).get("name", "")
                send_esp32(f"{symbol} {name}", feed_id="1")
                send_telegram(message)
        else:
            log("Asset count increased but no new symbols found (possible data change)")
    else:
        log("No new assets detected")

    save_current_data(current_symbols, first_post_id)


if __name__ == "__main__":
    main()
