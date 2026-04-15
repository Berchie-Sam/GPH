"""
MP Reference Builder

Scrape MP information from Parliament of Ghana website and Wikipedia,
then merge to create a comprehensive reference dataset for the 
9th Parliament (2024 election).
"""

import re
import csv
import time
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict

# Constants
PARLIAMENT_GH_BASE = "https://www.parliament.gh"
PARLIAMENT_GH_LIST = "https://www.parliament.gh/members"
PARLIAMENT_GH_PAGES = 7  # pages 1–7

WIKIPEDIA_URL = (
    "https://en.wikipedia.org/wiki/"
    "List_of_MPs_elected_in_the_2024_Ghanaian_general_election"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}

POLITE_DELAY = 1.5  # seconds between requests

PARTY_ABBREV = {
    "national democratic congress": "NDC",
    "new patriotic party": "NPP",
    "independent": "IND",
    "people's national convention": "PNC",
    "convention people's party": "CPP",
}

MP_REF_COLUMNS = [
    "mp_id",
    "full_name",
    "name_normalised",
    "party",
    "party_abbrev",
    "constituency",
    "region",
    "majority",
    "previous_mp",
    "previous_party",
    "parliament",
    "source",
]


def _abbrev(party: str) -> str:
    """Return standardised party abbreviation."""
    key = party.strip().lower()
    return PARTY_ABBREV.get(key, party.upper()[:3])


def _normalise_name(name: str) -> str:
    """
    Canonical name key for fuzzy matching:
    lowercase, strip titles/roles, collapse spaces, hyphens → spaces.
    """
    name = re.sub(r"\(.*?\)", "", name)  # remove role annotations
    name = re.sub(r"-", " ", name)  # hyphens → spaces
    name = re.sub(r"\s+", " ", name).strip()
    return name.lower()


def _save_csv(rows: List[Dict], path: str, columns: List[str]):
    """Save rows to CSV."""
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Saved {len(rows):,} rows → {path}")


def _load_csv(path: str) -> List[Dict]:
    """Load CSV file."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ══════════════════════════════════════════════════════
# Source A — Parliament.gh
# ══════════════════════════════════════════════════════

def scrape_parliament_gh(pages: int = PARLIAMENT_GH_PAGES) -> List[Dict]:
    """
    Scrape MP listing pages from parliament.gh/members.
    
    Requires: requests, beautifulsoup4
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError(
            "requests / beautifulsoup4 required. Run: pip install requests beautifulsoup4"
        )

    print(f"\nScraping parliament.gh ({pages} pages)…")
    session = requests.Session()
    records = []

    for page_num in range(1, pages + 1):
        url = (
            PARLIAMENT_GH_LIST
            if page_num == 1
            else f"{PARLIAMENT_GH_LIST}?page={page_num}"
        )
        print(f"  Page {page_num}/{pages}: {url}")

        try:
            resp = session.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            time.sleep(POLITE_DELAY)
        except Exception as e:
            print(f"    ERROR: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.find_all("a", href=re.compile(r"members\?mp=\d+"))

        for card in cards:
            href = card.get("href", "")
            mp_id = re.search(r"mp=(\d+)", href)
            mp_id = mp_id.group(1) if mp_id else ""

            h5 = card.find("h5")
            name = h5.get_text(strip=True) if h5 else ""

            # Text after h5: "Constituency\nParty"
            lines = [
                ln.strip()
                for ln in card.get_text("\n", strip=True).splitlines()
                if ln.strip() and ln.strip() != name
            ]
            constituency = lines[0] if len(lines) > 0 else ""
            party = lines[1] if len(lines) > 1 else ""

            if not name:
                continue

            records.append({
                "mp_id": mp_id,
                "full_name": name,
                "name_normalised": _normalise_name(name),
                "party": party,
                "party_abbrev": _abbrev(party),
                "constituency": constituency,
                "region": "",
                "majority": "",
                "previous_mp": "",
                "previous_party": "",
                "parliament": "9th",
                "source": "parliament.gh",
            })

    print(f"  Total from parliament.gh: {len(records)}")
    return records


# ══════════════════════════════════════════════════════
# Source B — Wikipedia
# ══════════════════════════════════════════════════════

def scrape_wikipedia() -> List[Dict]:
    """
    Parse Wikipedia table of MPs elected in 2024 election.
    
    Requires: requests, beautifulsoup4
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError(
            "requests / beautifulsoup4 required. Run: pip install requests beautifulsoup4"
        )

    print("\nScraping Wikipedia…")

    try:
        resp = requests.get(WIKIPEDIA_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"  ERROR: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    records = []

    # Walk through headings and tables
    current_region = "Unknown"
    for element in soup.find_all(["h2", "h3", "table"]):
        if element.name in ("h2", "h3"):
            text = element.get_text(strip=True)
            m = re.match(r"^(.+?Region)\s*[-–]", text)
            if m:
                current_region = m.group(1).strip()

        elif element.name == "table":
            rows = element.find_all("tr")
            if not rows:
                continue

            headers = [th.get_text(strip=True).lower()
                      for th in rows[0].find_all(["th", "td"])]
            if "elected mp" not in headers and "constituency" not in headers:
                continue  # not an MP table

            col = {h: i for i, h in enumerate(headers)}

            for tr in rows[1:]:
                cells = [td.get_text(strip=True)
                        for td in tr.find_all(["td", "th"])]
                if len(cells) < 3:
                    continue

                def _c(key, fallback=""):
                    idx = col.get(key)
                    return cells[idx] if idx is not None and idx < len(cells) else fallback

                name = _c("elected mp")
                party = _c("elected party")
                # Strip role annotations
                name_clean = re.sub(r"\(.*?\)", "", name).strip()

                if not name_clean:
                    continue

                records.append({
                    "mp_id": "",
                    "full_name": name_clean,
                    "name_normalised": _normalise_name(name_clean),
                    "party": party,
                    "party_abbrev": _abbrev(party),
                    "constituency": _c("constituency"),
                    "region": current_region,
                    "majority": _c("majority"),
                    "previous_mp": _c("previous mp"),
                    "previous_party": _c("previous party"),
                    "parliament": "9th",
                    "source": "wikipedia",
                })

    print(f"  Total from Wikipedia: {len(records)}")
    return records


# ══════════════════════════════════════════════════════
# Merge Sources
# ══════════════════════════════════════════════════════

def merge_sources(gh_records: List[Dict], wiki_records: List[Dict]) -> List[Dict]:
    """
    Merge parliament.gh and Wikipedia by fuzzy name matching.
    
    Strategy:
    1. Index parliament.gh by normalised name
    2. For each Wikipedia record, find best parliament.gh match (score ≥ 0.80)
    3. Copy mp_id to Wikipedia record if found
    4. Return merged dataset (Wikipedia richer, plus unmatched parliament.gh)
    """
    try:
        import difflib
    except ImportError:
        raise RuntimeError("difflib required (built-in)")

    print("\nMerging sources…")

    gh_by_name = {r["name_normalised"]: r for r in gh_records}
    gh_name_list = list(gh_by_name.keys())
    merged = []
    unmatched_gh = set(gh_name_list)

    for wr in wiki_records:
        wn = wr["name_normalised"]

        # Direct lookup
        if wn in gh_by_name:
            wr["mp_id"] = gh_by_name[wn]["mp_id"]
            unmatched_gh.discard(wn)
        else:
            # Fuzzy match
            matches = difflib.get_close_matches(wn, gh_name_list, n=1, cutoff=0.80)
            if matches:
                gh_match = gh_by_name[matches[0]]
                wr["mp_id"] = gh_match["mp_id"]
                unmatched_gh.discard(matches[0])

        merged.append(wr)

    # Add unmatched parliament.gh records
    for name_key in unmatched_gh:
        r = gh_by_name[name_key].copy()
        r["source"] = "parliament.gh (unmatched to wiki)"
        merged.append(r)

    wiki_matched = sum(1 for r in merged if r["mp_id"] and r["source"] == "wikipedia")
    print(f"  Wikipedia with mp_id: {wiki_matched}/{len(wiki_records)}")
    print(f"  parliament.gh unmatched: {len(unmatched_gh)}")
    print(f"  Total merged: {len(merged)}")

    return merged


# ══════════════════════════════════════════════════════
# Offline Reference (for development)
# ══════════════════════════════════════════════════════

def build_reference_offline() -> List[Dict]:
    """
    Build a minimal MP reference from hardcoded sample data.
    
    Used for development when internet not available.
    Covers key MPs for initial testing.
    """
    print("Building offline reference from sample data…")

    # Sample of MPs with known attributes
    sample_data = [
        # NDC Leadership
        ("", "Cassiel Ato Baah Forson", "National Democratic Congress", "Ajumako Enyan Esiam", "Central Region"),
        ("", "Mahama Ayariga", "National Democratic Congress", "Bawku Central", "Upper East Region"),
        ("", "Alban Sumana Kingsford Bagbin", "National Democratic Congress", "Nadowli Kaleo", "Upper West Region"),
        # NPP Leadership
        ("", "Alexander Kwamena Afenyo-Markin", "New Patriotic Party", "Effutu", "Central Region"),
        ("", "Stephen Amoah", "New Patriotic Party", "Old Tafo", "Ashanti Region"),
        # Notable MPs
        ("", "Samuel Okudzeto Ablakwa", "National Democratic Congress", "North Tongu", "Volta Region"),
        ("", "Kobena Mensah Woyome", "National Democratic Congress", "South Tongu", "Volta Region"),
        ("", "Isaac Adongo", "National Democratic Congress", "Bolgatanga Central", "Upper East Region"),
        ("", "Ursula Owusu-Ekuful", "New Patriotic Party", "Ablekuma West", "Greater Accra Region"),
        ("", "Kojo Oppong Nkrumah", "New Patriotic Party", "Ofoase Ayirebi", "Eastern Region"),
        ("", "Elizabeth Ofosu-Adjare", "National Democratic Congress", "Techiman North", "Bono East Region"),
    ]

    records = []
    for mp_id, name, party, constituency, region in sample_data:
        records.append({
            "mp_id": mp_id,
            "full_name": name,
            "name_normalised": _normalise_name(name),
            "party": party,
            "party_abbrev": _abbrev(party),
            "constituency": constituency,
            "region": region,
            "majority": "",
            "previous_mp": "",
            "previous_party": "",
            "parliament": "9th",
            "source": "offline_sample",
        })

    print(f"  Built offline reference: {len(records)} MPs")
    return records


# ══════════════════════════════════════════════════════
# Build Reference (Main Entry Point)
# ══════════════════════════════════════════════════════

def build_reference_online(out_path: str = "ghana_mps_9th_parliament.csv") -> List[Dict]:
    """
    Full scrape: parliament.gh (all pages) + Wikipedia, then merge.
    
    Requires: requests, beautifulsoup4
    """
    gh_records = scrape_parliament_gh(PARLIAMENT_GH_PAGES)
    wiki_records = scrape_wikipedia()
    merged = merge_sources(gh_records, wiki_records)
    _save_csv(merged, out_path, MP_REF_COLUMNS)
    return merged


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build MP reference dataset")
    parser.add_argument("--offline", action="store_true",
                       help="Build from sample data (no internet)")
    parser.add_argument("--output", default="ghana_mps_9th_parliament.csv",
                       help="Output CSV path")
    args = parser.parse_args()

    if args.offline:
        records = build_reference_offline()
    else:
        records = build_reference_online(args.output)

    print(f"\nReference dataset: {len(records)} MPs")
    print(f"Saved to: {args.output}")
