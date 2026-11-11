import os
import json
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

SEARCH_URL = "https://www.coachcox.co.uk/imstats/search/data/"
OUTPUT_FILE = "hkg_finishers.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.coachcox.co.uk/imstats/search/"
}

def main():
    payload = {
        "nationality": "Hong Kong",
        "type": "Ironman"
    }
    
    logging.info(f"Querying CoachCox search endpoint for Hong Kong Ironman finishers...")
    try:
        response = requests.post(SEARCH_URL, data=payload, headers=HEADERS, timeout=20)
        if response.status_code != 200:
            logging.error(f"Search API returned status code {response.status_code}")
            return
        
        data = response.json()
        # Handle different potential JSON response structures (list or nested dict keys)
        rows = data if isinstance(data, list) else data.get("data", data.get("results", []))
        
        logging.info(f"Retrieved {len(rows)} raw records from search API.")
    except Exception as e:
        logging.error(f"Failed to connect to CoachCox search API: {e}")
        return

    all_finishers = []
    for row in rows:
        athlete_name = row.get("name") or row.get("athlete", "Unknown")
        race_name = row.get("race") or row.get("race_name", "IRONMAN Race")
        
        all_finishers.append({
            "athlete_name": athlete_name,
            "gender": row.get("gender") or row.get("sex", "N/A"),
            "age_group": row.get("division") or row.get("age_group", "N/A"),
            "swim_time": row.get("swim_time") or row.get("swim", "N/A"),
            "bike_time": row.get("bike_time") or row.get("bike", "N/A"),
            "run_time": row.get("run_time") or row.get("run", "N/A"),
            "total_time": row.get("overall_time") or row.get("total", "N/A"),
            "overall_rank": str(row.get("overall_rank", "N/A")),
            "div_rank": str(row.get("division_rank", row.get("div_rank", "N/A"))),
            "race_name": race_name,
            "race_year": row.get("year"),
            "source_url": "https://www.coachcox.co.uk/imstats/search/"
        })

    # Deduplicate entries based on name, race, and total time
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
