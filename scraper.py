import os
import json
import time
import logging
import re
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

BASE_URL = "https://www.coachcox.co.uk"
LIST_URL = f"{BASE_URL}/imstats/races/"
OUTPUT_FILE = "hkg_finishers.json"
WHITELIST_FILE = "whitelist.json"
REQUEST_DELAY = 1.5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

def load_whitelist() -> List[str]:
    """Loads a list of athlete names (case-insensitive) to include regardless of flag."""
    if os.path.exists(WHITELIST_FILE):
        try:
            with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [name.strip().lower() for name in data if isinstance(name, str)]
        except Exception as e:
            logging.warning(f"Could not read {WHITELIST_FILE}: {e}")
    return []

def get_race_links() -> List[Dict[str, str]]:
    """Fetches all race URLs from the CoachCox race directory."""
    logging.info(f"Fetching race index from {LIST_URL}")
    response = requests.get(LIST_URL, headers=HEADERS, timeout=15)
    if response.status_code != 200:
        logging.error(f"Failed to fetch race list. Status: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    race_links = []
    
    # Target links matching the race pattern /imstats/race/{id}/results/ or /imstats/race/{id}/
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if "/imstats/race/" in href:
            clean_href = href.split("?")[0]
            if not clean_href.endswith("/results/"):
                if clean_href.endswith("/"):
                    clean_href += "results/"
                else:
                    clean_href += "/results/"
            
            full_url = BASE_URL + clean_href if clean_href.startswith("/") else clean_href
            if full_url not in [r["url"] for r in race_links]:
                race_name = anchor.text.strip() or "Unknown Race"
                race_links.append({"url": full_url, "name": race_name})

    logging.info(f"Found {len(race_links)} race result links.")
    return race_links

def parse_race_results(race_info: Dict[str, str], whitelist: List[str]) -> List[Dict[str, Any]]:
    """Parses individual race result tables for HKG / Hong Kong or Whitelisted athletes."""
    url = race_info["url"]
    logging.info(f"Scraping: {url}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            logging.warning(f"Skipping {url} — HTTP Status {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"Error requesting {url}: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    
    # Extract Race Name & Year from page title or url
    page_title = soup.find("h1").text.strip() if soup.find("h1") else race_info["name"]
    year_match = re.search(r"\b(19|20)\d{2}\b", page_title) or re.search(r"\b(19|20)\d{2}\b", url)
    race_year = int(year_match.group(0)) if year_match else None
    
    results = []
    table = soup.find("table")
    if not table:
        return []

    headers = [th.text.strip().lower() for th in table.find_all("th")]
    
    # Map key column indices dynamically
    col_map = {}
    for idx, h in enumerate(headers):
        if "name" in h or "athlete" in h: col_map["name"] = idx
        elif "country" in h or "nat" in h or "nation" in h or "flag" in h: col_map["country"] = idx
        elif "gender" in h or "sex" in h: col_map["gender"] = idx
        elif "group" in h or "cat" in h or "div" in h or "age" in h: col_map["age_group"] = idx
        elif "swim" in h: col_map["swim"] = idx
        elif "bike" in h: col_map["bike"] = idx
        elif "run" in h: col_map["run"] = idx
        elif "finish" in h or "total" in h or "time" in h: col_map["total"] = idx
        elif "overall" in h or "rank" in h: col_map["overall_rank"] = idx
        elif "division" in h or "div rank" in h: col_map["div_rank"] = idx

    for row in table.find_all("tr")[1:]:
        cols = row.find_all(["td", "th"])
        if len(cols) < 4:
            continue
            
        def get_val(key):
            idx = col_map.get(key)
            return cols[idx].text.strip() if idx is not None and idx < len(cols) else "N/A"

        athlete_name = get_val("name")
        country = get_val("country")
        
        is_hkg = country.upper() in ["HKG", "HONG KONG", "HONG KONG, CHINA", "HK"]
        is_whitelisted = athlete_name.lower() in whitelist
        
        if is_hkg or is_whitelisted:
            results.append({
                "athlete_name": athlete_name,
                "gender": get_val("gender"),
                "age_group": get_val("age_group"),
                "swim_time": get_val("swim"),
                "bike_time": get_val("bike"),
                "run_time": get_val("run"),
                "total_time": get_val("total"),
                "overall_rank": get_val("overall_rank"),
                "div_rank": get_val("div_rank"),
                "race_name": page_title,
                "race_year": race_year,
                "source_url": url
            })

    return results

def main():
    whitelist = load_whitelist()
    race_links = get_race_links()
    
    all_finishers = []
    
    for race in race_links:
        race_results = parse_race_results(race, whitelist)
        all_finishers.extend(race_results)
        time.sleep(REQUEST_DELAY)

    # Deduplicate based on Athlete Name + Race Name + Total Time
    deduped = {}
    for entry in all_finishers:
        key = f"{entry['athlete_name']}_{entry['race_name']}_{entry['total_time']}".lower()
        deduped[key] = entry

    final_results = list(deduped.values())
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)

    logging.info(f"Successfully exported {len(final_results)} records to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
