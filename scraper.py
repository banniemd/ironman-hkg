import os
import json
import time
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

BASE_URL = "https://www.coachcox.co.uk"
OUTPUT_FILE = "hkg_finishers.json"
WHITELIST_FILE = "whitelist.json"
REQUEST_DELAY = 1.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest"
}

def load_whitelist():
    if os.path.exists(WHITELIST_FILE):
        try:
            with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [str(name).strip().lower() for name in data if name]
        except Exception as e:
            logging.warning(f"Could not read {WHITELIST_FILE}: {e}")
    return []

def main():
    whitelist = load_whitelist()
    all_finishers = []

    # Fetch index of races from CoachCox API endpoint
    try:
        index_url = f"{BASE_URL}/imstats/races/data/"
        logging.info(f"Fetching race index from {index_url}")
        res = requests.get(index_url, headers=HEADERS, timeout=20)
        
        if res.status_code == 200:
            races = res.json()
        else:
            logging.warning("Index endpoint returned non-200, attempting fallbacks.")
            races = []
    except Exception as e:
        logging.error(f"Error fetching index: {e}")
        races = []

    # Iterate over discovered or known major race IDs
    for race in races:
        race_id = race.get("id") or race.get("race_id")
        if not race_id:
            continue

        data_url = f"{BASE_URL}/imstats/race/{race_id}/data/"
        try:
            r_res = requests.get(data_url, headers=HEADERS, timeout=15)
            if r_res.status_code != 200:
                continue

            results = r_res.json()
            for row in results:
                row_str = json.dumps(row).lower()
                athlete_name = row.get("name") or row.get("athlete", "Unknown")
                
                is_hkg = "hkg" in row_str or "hong kong" in row_str
                is_whitelisted = athlete_name.lower() in whitelist

                if is_hkg or is_whitelisted:
                    all_finishers.append({
                        "athlete_name": athlete_name,
                        "gender": row.get("gender") or row.get("sex", "N/A"),
                        "age_group": row.get("age_group") or row.get("category", "N/A"),
                        "swim_time": row.get("swim", "N/A"),
                        "bike_time": row.get("bike", "N/A"),
                        "run_time": row.get("run", "N/A"),
                        "total_time": row.get("overall") or row.get("total", "N/A"),
                        "overall_rank": row.get("overall_rank", "N/A"),
                        "div_rank": row.get("div_rank", "N/A"),
                        "race_name": race.get("name", "IRONMAN Race"),
                        "race_year": race.get("year"),
                        "source_url": f"{BASE_URL}/imstats/race/{race_id}/results/"
                    })
            time.sleep(REQUEST_DELAY)
        except Exception as err:
            logging.debug(f"Error parsing race {race_id}: {err}")
            continue

    # Deduplicate entries
    deduped = {}
    for entry in all_finishers:
        key = f"{entry['athlete_name']}_{entry['race_name']}_{entry['total_time']}".lower()
        deduped[key] = entry

    final_results = list(deduped.values())

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)

    logging.info(f"Successfully saved {len(final_results)} HKG finishers to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
