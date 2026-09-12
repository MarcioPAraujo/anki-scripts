import argparse
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import quote
 
import requests
from bs4 import BeautifulSoup, Tag
import copy

USER_AGENT = "Mozilla/5.0 (compatible; anki-card-scraper/1.0)"

# target tags to search for the main content
CONTENT_SELECTORS = [
    "article",
    "div.entry-content",
    "div.post-content",
]

def fetch_html(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    return resp.text

def get_content_element(soup: BeautifulSoup):
    for selector in CONTENT_SELECTORS:
        el = soup.select_one(selector)
        if el:
            return el

    print("WARNING: no selector matched; using body", file=sys.stderr)
    return soup.body or soup

def extract_eng_pt_parts(p_element):
    if isinstance(p_element, str):
        soup = BeautifulSoup(p_element, 'html.parser')
        p_tag = soup.find("p") or soup
    else:
        p_tag = p_element

    #needed a copy because this DOM part will be modified to extract portuguese text
    p_copy = copy.deepcopy(p_tag)

    strong_tags = p_copy.find_all("strong")
    english_raw = " ".join(s.get_text() for s in strong_tags)
    english_text = " ".join(english_raw.split())

    for s in strong_tags:
        s.decompose()

    portuguese_raw = p_copy.get_text()
    portuguese_text = " ".join(portuguese_raw.split())

    return english_text, portuguese_text

    

# return english sentences and portuguese sentences
def extract_text_pairs(content: Tag | BeautifulSoup) -> tuple[list[str], list[str]]:
    english, portuguese = [], []


    for p in content.find_all("p"):

        if not p.find('strong'):
            continue

        if p.has_attr("class") or p.has_attr("id") or p.has_attr("style"):
            continue
            
        en, pt = extract_eng_pt_parts(p)
        if en and pt:
            english.append(en)
            portuguese.append(pt)

    return english, portuguese

def extract_mp3_urls(html: str) -> list[str]:
    urls = re.findall(r'https?://[^\s"\'()]+\.mp3', html)

    seen, ordered = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            ordered.append(u)

    return ordered

def slugify(text: str, max_words: int = 6) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())[:max_words]
    return "-".join(words) if words else "card"

def download_mp3(url: str, dest: Path):
    safe_url = quote(url, safe=":/?=&")
    resp = requests.get(safe_url, headers={"User-Agent": USER_AGENT}, timeout=60)
    resp.raise_for_status()
    dest.write_bytes(resp.content)

def main():
    parser = argparse.ArgumentParser(description="Scrape a mairovergara.com post into Anki-ready card folders")

    parser.add_argument("url", help="Post url, e.g. https://www.mairovergara.com/strike-off-phrasal-verb-significado/")

    parser.add_argument("--out-dir", default="./cards", help="Where to write card folders (default: ./cards)")

    parser.add_argument("--dry-run", action="store_true", help="Print extracted pairs without downloading anything")

    args = parser.parse_args()

    print(f"Fetching {args.url} ...")
    #read html page
    html = fetch_html(args.url)
    soup = BeautifulSoup(html, "html.parser")

    #retrieving the main content
    content = get_content_element(soup)

    #finding english and portuguese texts
    english, portuguese = extract_text_pairs(content)

    #finding mp3 url files
    mp3_urls = extract_mp3_urls(html)

    print(f"Found: {len(english)} English sentence(s), "
          f"{len(portuguese)} Portuguese translation(s), "
          f"{len(mp3_urls)} mp3 file(s).")
 
    counts = {len(english), len(portuguese), len(mp3_urls)}

    if len(counts) != 1:
        print("WARNING: counts don't match — pairing by position may be wrong for " "the tail end of the list. Inspect with --dry-run before trusting the output.", file=sys.stderr)

    # it's a safe guard to run the loop using the minimun content,
    # in case a phrase has more than one audio, english text or portuguese text
    n = min(len(english), len(portuguese), len(mp3_urls))


    for i in range(n):
        eng, por, mp3_url = english[i], portuguese[i], mp3_urls[i]
        folder_name = f"{i + 1:02d}-{slugify(eng)}"
        print(f"\n[{i + 1}/{n}] {folder_name}")
        print(f"  EN: {eng}")
        print(f"  PT: {por}")
        print(f"  MP3: {mp3_url}")
 
        if args.dry_run:
            continue

        title = soup.find("h1") or soup

        root_folder_name = slugify(title.get_text(), 10)

        root_folder = Path(args.out_dir) / root_folder_name

        folder = root_folder / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "english.txt").write_text(eng, encoding="utf-8")
        (folder / "portuguese.txt").write_text(por, encoding="utf-8")
 
        audio_dest = folder / mp3_url.split('/')[-1]
        if audio_dest.exists():
            print("  [skip] audio already downloaded")
        else:
            download_mp3(mp3_url, audio_dest)
            print("  [ok] audio downloaded")
 
    if args.dry_run:
        print("\nDry run complete — nothing was written to disk.")
    else:
        print(f"\nDone. {n} card folder(s) written to {args.out_dir}")
 
 
if __name__ == "__main__":
    main()
