import os
import json
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

OUTPUT_FILE = "hkg_finishers.json"

# Public multi-sport and triathlon federation results endpoint
PUBLIC_RESULTS_API = "https://api.results.triathlon.org/v1/results?country=HKG&limit=500"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
}

def main():
    logging.info("Fetching public Hong Kong triathlon and Ironman finish records...")
    all_finishers = []
    
    try:
        response = requests.get(PUBLIC_RESULTS_API, headers=HEADERS, timeout=20)
        logging.info(f"API Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            items = data if isinstance(data, list) else data.get("items", data.get("results", []))
            
            for item in items:
                # Filter to long distance / ironman events if designated, or capture all public records
                all_finishers.append({
                    "athlete_name": item.get("name", "Unknown"),
                    "gender": item.get("gender", "M"),
                    "age_group": item.get("category", "N/A"),
                    "swim_time": item.get("swim", "N/A"),
                    "bike_time": item.get("bike", "N/A"),
                    "run_time": item.get("run", "N/A"),
                    "total_time": item.get("total_time", "N/A"),
                    "overall_rank": str(item.get("rank", "N/A")),
                    "div_rank": str(item.get("category_rank", "N/A")),
                    "race_name": item.get("event_name", "IRONMAN / Triathlon Event"),
                    "race_year": item.get("year", 2026),
                    "source_url": PUBLIC_RESULTS_API
                })
        else:
            logging.error(f"API endpoint returned non-200 status: {response.status_code}")
    except Exception as e:
        logging.error(f"Error connecting to results feed: {e}")

    # Write out the resulting dataset to the JSON file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_finishers, f, indent=2, ensure_ascii=False)
    
    logging.info(f"Successfully wrote {len(all_finishers)} records to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
