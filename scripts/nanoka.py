"""
监控 nanoka.cc 游戏版本更新
"""

import sys
import os
import json
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from modules.util import log, send_telegram, send_esp32

DATA_FILE = "data/nanoka.json"
MANIFEST_URL = "https://static.nanoka.cc/manifest.json"


def fetch_manifest():
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; GitHub-Actions/1.0)",
        "Accept": "application/json",
    }
    req = urllib.request.Request(MANIFEST_URL, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            log("Successfully fetched manifest")
            return data
    except urllib.error.HTTPError as e:
        log(f"HTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except Exception as e:
        log(f"Error fetching manifest: {str(e)}")
        sys.exit(1)


def load_previous_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                log(f"Loaded previous data")
                return data
        except Exception as e:
            log(f"Error loading previous data: {str(e)}")
    return {"gi": {}, "hsr": {}, "zzz": {}, "ww": {}}


def save_current_data(data):
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
        log(f"Saved current data")
    except Exception as e:
        log(f"Error saving data: {str(e)}")


def extract_game_versions(manifest):
    versions = {}
    games = ["gi", "hsr", "zzz", "ww"]
    version_keys = ["latest", "live"]

    for game in games:
        game_data = manifest.get(game, {})
        game_versions = {}
        for key in version_keys:
            value = game_data.get(key) if isinstance(game_data, dict) else None
            if value:
                game_versions[key] = value
        versions[game] = game_versions
    return versions


def format_telegram_message(changes):
    lines = ["[Nanoka] Update"]
    for game, change in changes.items():
        for key, (old, new) in change.items():
            lines.append(f"{game.upper()} {key}: {old} -> {new}")
    return "\n".join(lines)

def format_esp32_message(changes):
    lines = []
    for game, change in changes.items():
        for key, (old, new) in change.items():
            lines.append(f"{game.upper()} {key}: {old} -> {new}")
    return ",".join(lines)


def main():
    current_manifest = fetch_manifest()
    current_versions = extract_game_versions(current_manifest)

    previous_data = load_previous_data()
    if not any(previous_data.values()):
        previous_versions = current_versions
    else:
        previous_versions = previous_data

    esp_parts = []
    for game, game_vers in current_versions.items():
        live = game_vers.get('live', 'none')
        latest = game_vers.get('latest', 'none')
        esp_parts.append(f"{game} {live} {latest}")

    esp_message = ", ".join(esp_parts)

    # key 2 for Nanoka
    first_post_id = previous_data.get("first_post") if isinstance(previous_data, dict) else None

    if first_post_id:
        result = send_esp32(esp_message, post_id=first_post_id)
        log(f"Updated existing ESP32 post with ID: {first_post_id}")
    else:
        result = send_esp32(esp_message, feed_id="2")
        if result:
            current_versions["first_post"] = result
            log(f"Created new ESP32 post with ID: {result}")
        else:
            log(f"Failed to get post ID from send_esp32, result: {result}")

    changes_detected = {}
    for game, current_game_vers in current_versions.items():
        if game == "first_post":
            continue
        previous_game_vers = previous_versions.get(game, {})
        for ver_key, current_val in current_game_vers.items():
            previous_val = previous_game_vers.get(ver_key)
            if previous_val and current_val != previous_val:
                if game not in changes_detected:
                    changes_detected[game] = {}
                changes_detected[game][ver_key] = (previous_val, current_val)

    if changes_detected:
        log(f"Detected changes: {changes_detected}")
        send_telegram(format_telegram_message(changes_detected))
        send_esp32(format_esp32_message(changes_detected), feed_id="2")
    else:
        log("No version changes detected.")

    save_current_data(current_versions)


if __name__ == "__main__":
    main()