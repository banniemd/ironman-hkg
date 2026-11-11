import os
import json
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

OUTPUT_FILE = "hkg_finishers.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

def fetch_official_timing_api():
    """
    Queries official international timing endpoints for Hong Kong (HKG) participants.
    """
    all_finishers = []
    
    # Standard official timing API search parameters for HKG across major events
    api_endpoints = [
        "https://api.mikatiming.de/contests/ironman/participants?country=HKG",
        "https://track.ironman.com/api/participants?country=HKG"
    ]
    
    for url in api_endpoints:
        try:
            logging.info(f"Querying official timing API: {url}")
            response = requests.get(url, headers=HEADERS, timeout=20)
            if response.status_code == 200:
                data = response.json()
                participants = data.get("participants", data.get("results", []))
                
                for p in participants:
                    all_finishers.append({
                        "athlete_name": f"{p.get('firstname', '')} {p.get('lastname', '')}".strip(),
                        "gender": p.get("gender", "N/A"),
                        "age_group": p.get("age_group", p.get("class", "N/A")),
                        "swim_time": p.get("swim", p.get("splits", {}).get("swim", "N/A")),
                        "bike_time": p.get("bike", p.get("splits", {}).get("bike", "N/A")),
                        "run_time": p.get("run", p.get("splits", {}).get("run", "N/A")),
                        "total_time": p.get("finish", p.get("net_time", "N/A")),
                        "overall_rank": str(p.get("overall_rank", "N/A")),
                        "div_rank": str(p.get("age_group_rank", "N/A")),
                        "race_name": p.get("event_name", "IRONMAN Event"),
                        "race_year": p.get("year", 2026),
                        "source_url": url
                    })
                break # Exit loop if successful
        except Exception as e:
            logging.warning(f"API endpoint {url} failed or blocked: {e}")
            
    return all_finishers

def main():
    logging.info("Starting direct official timing data extraction...")
    finishers = fetch_official_timing_api()
    
    # Deduplicate results
    deduped = {}
    for entry in finishers:
        key = f"{entry['athlete_name']}_{entry['race_name']}_{entry['total_time']}".lower()
        deduped[key] = entry

    final_results = list(deduped.values())

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)

    logging.info(f"Successfully compiled {len(final_results)} records to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
