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

# Official Ironman results handler base configuration
HANDLER_BASE_URL = "http://www.ironman.com/handlers/eventresults.aspx"
OUTPUT_FILE = "hkg_finishers.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

def get_official_race_targets() -> List[Dict[str, str]]:
    """
    Discovers official Ironman event result links and dates directly from the official index.
    """
    directory_url = "https://www.ironman.com/results"
    logging.info(f"Connecting to official Ironman results directory: {directory_url}")
    
    race_targets = []
    try:
        response = requests.get(directory_url, headers=HEADERS, timeout=25)
        if response.status_code != 200:
            logging.error(f"Failed to reach official results page. Status: {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, "html.parser")
        # Find event result anchors or redirection links pointing to event results
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "eventresults.aspx" in href or "results" in href:
                full_url = href if href.startswith("http") else f"https://www.ironman.com{href}"
                if full_url not in [r["url"] for r in race_targets]:
                    race_targets.append({"url": full_url, "name": a.text.strip() or "IRONMAN Event"})
    except Exception as e:
        logging.error(f"Error connecting to official Ironman index: {e}")
        
    return race_targets

def parse_official_race_endpoint(event_url: str) -> List[Dict[str, Any]]:
    """
    Queries official event result tables, handling sex/age-group filters 
    and extracting exact splits, transition times, and country codes.
    """
    hkg_athletes = []
    try:
        res = requests.get(event_url, headers=HEADERS, timeout=20)
        if res.status_code != 200:
            return []
            
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Extract event title and metadata
        title_el = soup.select_one(".moduleContentInner header h1, #eventDetails h3.eventTitle")
        race_name = title_el.text.strip() if title_el else "IRONMAN Race"
        
        year_match = re.search(r"\b(19|20)\d{2}\b", race_name) or re.search(r"\b(19|20)\d{2}\b", event_url)
        race_year = int(year_match.group(0)) if year_match else 2026

        # Locate results table
        table = soup.select_one("table.eventResults, table")
        if not table:
            return []

        rows = table.find_all("tr")
        if len(rows) < 2:
            return []

        for row in rows[1:]:
            cols = [td.get_text().strip() for td in row.find_all(["td", "th"])]
            if len(cols) < 5:
                continue
                
            row_text = " ".join(cols).lower()
            
            # Explicit check for Hong Kong country code or representation string
            if "hkg" in row_text or "hong kong" in row_text:
                # Standard mapping for official columns:
                # Name, Country, Div Rank, Gen Rank, Overall Rank, Swim, (T1/Bike/T2/Run depending on layout), Finish
                athlete_name = cols[0] if len(cols) > 0 else "Unknown"
                
                # Extract time metrics matching HH:MM:SS format
                times = re.findall(r"\b\d{1,2}:\d{2}:\d{2}\b", row_text)
                
                swim = times[0] if len(times) > 0 else "N/A"
                bike = times[1] if len(times) > 1 else "N/A"
                run = times[2] if len(times) > 2 else "N/A"
                finish = times[3] if len(times) > 3 else (times[-1] if times else "N/A")

                # Extract gender and age category
                gender = "M" if " m " in f" {row_text} " else ("F" if " f " in f" {row_text} " else "N/A")
                age_group_match = re.search(r"\b[mp]\d{2}-\d{2}\b", row_text)
                age_group = age_group_match.group(0).upper() if age_group_match else "N/A"

                hkg_athletes.append({
                    "athlete_name": athlete_name,
                    "gender": gender,
                    "age_group": age_group,
                    "swim_time": swim,
                    "bike_time": bike,
                    "run_time": run,
                    "total_time": finish,
                    "overall_rank": cols[4] if len(cols) > 4 and cols[4].isdigit() else "N/A",
                    "div_rank": cols[2] if len(cols) > 2 and cols[2].isdigit() else "N/A",
                    "race_name": race_name,
                    "race_year": race_year,
                    "source_url": event_url
                })
    except Exception as err:
        logging.debug(f"Error parsing official endpoint {event_url}: {err}")
        
    return hkg_athletes

def main():
    logging.info("Starting official Ironman results extraction...")
    targets = get_official_race_targets()
    
    all_finishers = []
    for target in targets:
        results = parse_official_race_endpoint(target["url"])
        if results:
            all_finishers.extend(results)
            logging.info(f"Captured {len(results)} HKG finisher(s) from {target['name']}")
        time.sleep(1.0) # Polite request spacing

    # Deduplicate entries based on name, race, and finish time
    deduped = {}
    for entry in all_finishers:
        key = f"{entry['athlete_name']}_{entry['race_name']}_{entry['total_time']}".lower()
        deduped[key] = entry

    final_results = list(deduped.values())

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)

    logging.info(f"Successfully compiled {len(final_results)} official HKG records to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
