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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

def get_all_race_links() -> List[Dict[str, str]]:
    logging.info(f"Fetching master race directory from {LIST_URL}")
    try:
        response = requests.get(LIST_URL, headers=HEADERS, timeout=20)
        if response.status_code != 200:
            logging.error(f"Failed to fetch master directory. Status: {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"Network error fetching master directory: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    race_links = []
    
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if "/imstats/race/" in href:
            clean_href = href.split("?")[0].rstrip("/") + "/results/"
            full_url = BASE_URL + clean_href if clean_href.startswith("/") else clean_href
            if full_url not in [r["url"] for r in race_links]:
                race_name = anchor.text.strip() or "IRONMAN Race"
                race_links.append({"url": full_url, "name": race_name})

    logging.info(f"Discovered {len(race_links)} total historical race result pages to parse.")
    return race_links

def parse_race_page(race_info: Dict[str, str]) -> List[Dict[str, Any]]:
    url = race_info["url"]
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return []
    except Exception:
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
        cols = [td.text.strip() for td in row.find_all(["td", "th"])]
        if len(cols) < 4:
            continue
            
        row_text = " ".join(cols).lower()
        
        # Check explicitly for Hong Kong country tags in the row
        if "hkg" in row_text or "hong kong" in row_text:
            times = re.findall(r"\b\d{1,2}:\d{2}:\d{2}\b", row_text)
            
            # Identify athlete name from text columns
            text_cols = [c for c in cols[:3] if not c.isdigit() and len(c) > 2]
            athlete_name = text_cols[0] if text_cols else cols[0]

            results.append({
                "athlete_name": athlete_name,
                "gender": "M" if " m " in f" {row_text} " else ("F" if " f " in f" {row_text} " else "N/A"),
                "age_group": re.search(r"\b[mp]\d{2}-\d{2}\b", row_text).group(0).upper() if re.search(r"\b[mp]\d{2}-\d{2}\b", row_text) else "N/A",
                "swim_time": times[0] if len(times) > 0 else "N/A",
                "bike_time": times[1] if len(times) > 1 else "N/A",
                "run_time": times[2] if len(times) > 2 else "N/A",
                "total_time": times[3] if len(times) > 3 else (times[-1] if times else "N/A"),
                "overall_rank": cols[5] if len(cols) > 5 and cols[5].isdigit() else "N/A",
                "div_rank": cols[3] if len(cols) > 3 and cols[3].isdigit() else "N/A",
                "race_name": page_title,
                "race_year": race_year,
                "source_url": url
            })

    return results

def main():
    race_links = get_all_race_links()
    all_finishers = []
    
    for race in race_links:
        match_results = parse_race_page(race)
        if match_results:
            all_finishers.extend(match_results)
            logging.info(f"Found {len(match_results)} HKG finisher(s) in {race['name']}")
        time.sleep(0.5) # Polite request delay

    # Deduplicate entries
    deduped = {}
    for entry in all_finishers:
        key = f"{entry['athlete_name']}_{entry['race_name']}_{entry['total_time']}".lower()
        deduped[key] = entry

    final_results = list(deduped.values())

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)

    logging.info(f"Successfully compiled {len(final_results)} total HKG records to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
