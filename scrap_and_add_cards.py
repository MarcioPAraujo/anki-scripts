import argparse

from cards_webscrap import scrap_post
from add_cards_to_anki import check_anki_connect, add_cards

def main():
    parser = argparse.ArgumentParser(description="Scrape a mairovergara.com post into Anki-ready card folders")

    parser.add_argument("url", help="Post url, e.g. https://www.mairovergara.com/strike-off-phrasal-verb-significado/")

    parser.add_argument("--out-dir", default="./cards", help="Where to write card folders (default: ./cards)")

    parser.add_argument("--dry-run", action="store_true", help="Print extracted pairs without downloading anything")

    parser.add_argument("--yes", action="store_true", help="Skip confirmation of the directories")

    parser.add_argument("--deck", default="English", help="Target Anki deck name (use '::' for subdecks)")

    parser.add_argument("--tag", default="", help="Optional tag to add to every imported note")

    parser.add_argument("--skip-anki", action="store_true", help="Only does the scrap part, and the cards are not added to anki")

    args = parser.parse_args()

    if not args.dry_run and not args.skip_anki:
        check_anki_connect(args.deck)

    root_folder = scrap_post(args.url, args.out_dir, args.dry_run, args.yes)

    if root_folder is None:
        return

    if args.skip_anki:
        print("\n--skip-anki: skipping anki cards import, files are in the folder")
        return

    add_cards(root_folder, args.deck, args.tag)
    
if __name__ == "__main__":
    main()
