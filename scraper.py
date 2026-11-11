import os
import json
import time
import logging
import re
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

BASE_URL = "https://www.coachcox.co.uk"
LIST_URL = f"{BASE_URL}/imstats/races/"
OUTPUT_FILE = "hkg_finishers.json"
WHITELIST_FILE = "whitelist.json"
REQUEST_DELAY = 1.2

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

def load_whitelist() -> List[str]:
    if os.path.exists(WHITELIST_FILE):
        try:
            with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [str(name).strip().lower() for name in data if name]
        except Exception as e:
            logging.warning(f"Could not read {WHITELIST_FILE}: {e}")
    return []

def get_race_links() -> List[Dict[str, str]]:
    logging.info(f"Fetching race directory from {LIST_URL}")
    try:
        response = requests.get(LIST_URL, headers=HEADERS, timeout=20, allow_redirects=True)
        if response.status_code != 200:
            logging.error(f"Failed to fetch race index. Status: {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"Network error fetching race index: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    race_links = []
    
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if "/imstats/race/" in href:
            clean_href = href.split("?")[0]
            if not clean_href.endswith("/results/"):
                clean_href = clean_href.rstrip("/") + "/results/"
            
            full_url = BASE_URL + clean_href if clean_href.startswith("/") else clean_href
            if full_url not in [r["url"] for r in race_links]:
                race_name = anchor.text.strip() or "IRONMAN Race"
                race_links.append({"url": full_url, "name": race_name})

    logging.info(f"Discovered {len(race_links)} race result links to crawl.")
    return race_links

def parse_race_results(race_info: Dict[str, str], whitelist: List[str]) -> List[Dict[str, Any]]:
    url = race_info["url"]
    try:
        response = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        if response.status_code != 200:
            return []
    except Exception as e:
        logging.debug(f"Error fetching {url}: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    
    h1 = soup.find("h1")
    page_title = h1.text.strip() if h1 else race_info["name"]
    year_match = re.search(r"\b(19|20)\d{2}\b", page_title) or re.search(r"\b(19|20)\d{2}\b", url)
    race_year = int(year_match.group(0)) if year_match else None
    
    results = []
    table = soup.find("table")
    if not table:
        return []

    rows = table.find_all("tr")
    if len(rows) < 2:
        return []

    for row in rows[1:]:
        try:
            cols = [td.text.strip() for td in row.find_all(["td", "th"])]
            if len(cols) < 4:
                continue
                
            row_text = " ".join(cols).lower()
            
            # Check if row belongs to Hong Kong or matches whitelist
            is_hkg = "hkg" in row_text or "hong kong" in row_text
            
            # Identify athlete name (usually the longest non-numeric text string in early columns)
            text_cols = [c for c in cols[:3] if not c.isdigit() and len(c) > 2]
            athlete_name = text_cols[0] if text_cols else cols[1] if len(cols) > 1 else cols[0]
            
            is_whitelisted = athlete_name.lower() in whitelist

            if is_hkg or is_whitelisted:
                # Extract all valid time strings matching HH:MM:SS format in the row
                times = re.findall(r"\b\d{1,2}:\d{2}:\d{2}\b", row_text)
                
                swim = times[0] if len(times) > 0 else "N/A"
                bike = times[1] if len(times) > 1 else "N/A"
                run = times[2] if len(times) > 2 else "N/A"
                total = times[3] if len(times) > 3 else (times[-1] if times else "N/A")

                # Extract gender and age group if present
                gender = "M" if " m " in f" {row_text} " else ("F" if " f " in f" {row_text} " else "N/A")
                age_group_match = re.search(r"\b[mp]\d{2}-\d{2}\b", row_text)
                age_group = age_group_match.group(0).upper() if age_group_match else "N/A"

                results.append({
                    "athlete_name": athlete_name,
                    "gender": gender,
                    "age_group": age_group,
                    "swim_time": swim,
                    "bike_time": bike,
                    "run_time": run,
                    "total_time": total,
                    "overall_rank": "N/A",
                    "div_rank": "N/A",
                    "race_name": page_title,
                    "race_year": race_year,
                    "source_url": url
                })
        except Exception as row_err:
            continue

    return results

def main():
    whitelist = load_whitelist()
    race_links = get_race_links()
    all_finishers = []
    
    for race in race_links:
        race_results = parse_race_results(race, whitelist)
        if race_results:
            all_finishers.extend(race_results)
            logging.info(f"Found {len(race_results)} match(es) in {race['name']}")
        time.sleep(REQUEST_DELAY)

    # Deduplicate entries
    deduped = {}
    for entry in all_finishers:
        key = f"{entry['athlete_name']}_{entry['race_name']}_{entry['total_time']}".lower()
        deduped[key] = entry

    final_results = list(deduped.values())
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)

    logging.info(f"Successfully scraped and exported {len(final_results)} total records to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
