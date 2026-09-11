import argparse
import base64
import json
import sys
from pathlib import Path

import requests

ANKI_CONNECT_URL = "http://127.0.0.1:8765"
MODEL_NAME = "Basic"

def invoke(action, **params):
    payload = {"action": action, "version": 6, "params": params}
    resp = requests.post(ANKI_CONNECT_URL, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if data.get("error") is not None:
        raise RuntimeError(f"AnkiConnected error on '{action}': {data['error']} ")
    return data["result"]

def ensure_deck_exists(deck_name: str):
    existing_decks = invoke("deckNames")
    if deck_name not in existing_decks:
        raise RuntimeError(f"The deck {deck_name} does not exist, aborting adding process")

def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()

def add_card_from_root_folder(folder: Path, deck_name: str, tag: str) -> bool:
    audio_path = next(folder.glob("*.mp3"), None)
    english_path = folder / "english.txt"
    portuguese_path = folder / "portuguese.txt"

    if not audio_path:
        print(f"  [skip] {folder.name}: no audio.mp3 found")
        return False

    english_text = read_text(english_path)
    portuguese_text = read_text(portuguese_path)

    if not english_text or not portuguese_text:
        print(f"  [skip] {folder.name}: no english.txt or portuguese.txt content")
        return False

    media_file_name = f"{audio_path}".split('/')[-1]

    audio_bytes = audio_path.read_bytes()
    invoke("storeMediaFile", filename = media_file_name, data=base64.b64encode(audio_bytes).decode("ascii"))


    back_html = f"<strong>{english_text}</strong>"
    back_html += f"<br><br>{portuguese_text}"

    note = {
        "deckName": deck_name,
        "modelName": MODEL_NAME,
        "fields": {
            "Front": f"[sound:{media_file_name}]",
            "Back": back_html, 
        },
        "options": {
            "allowDuplicate": False,
            "duplicateScope": "deck",
        },
        "tags": [tag] if tag else [],
    }

    try:
        invoke("addNote", note=note)
        print(f"  [ok] {folder.name}: added to '{deck_name}'")
        return True
    except RuntimeError as e:
        # addNote raises if it's a duplicate or fields are invalid — report
        # and keep going rather than aborting the whole batch.
        print(f"  [fail] {folder.name}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Add scraped audio cards to Anki via AnkiConnect.")
    parser.add_argument("--cards-dir", required=True, help="Path to the folder containing one subfolder per card")
    parser.add_argument("--deck", required=True, help="Target Anki deck name (use '::' for subdecks)")
    parser.add_argument("--tag", default="", help="Optional tag to add to every imported note")
    args = parser.parse_args()

    cards_dir = Path(args.cards_dir)

    if not cards_dir.is_dir():
        print(f"ERROR: {cards_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    try:
        version = invoke("version")
        print(f"Connected to AnkiConnect (API version {version}).")
    except requests.exceptions.ConnectionError:
        print(
            "ERROR: could not reach AnkiConnect at "
            f"{ANKI_CONNECT_URL}. Is Anki running with the AnkiConnect add-on installed?",
            file=sys.stderr,
        )
        sys.exit(1)
 
    ensure_deck_exists(args.deck)

    folders = sorted(p for p in cards_dir.iterdir() if p.is_dir())
    print(f"Found {len(folders)} card folder(s) in {cards_dir}.")
 
    added = 0
    for folder in folders:
        if add_card_from_root_folder(folder, args.deck, args.tag):
            added += 1
 
    print(f"\nDone. {added}/{len(folders)} card(s) added.")




if __name__ == "__main__":
    main()



