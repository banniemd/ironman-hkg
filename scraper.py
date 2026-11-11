import os
import json
import logging
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

SEARCH_PAGE_URL = "https://www.coachcox.co.uk/imstats/search/"
OUTPUT_FILE = "hkg_finishers.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

def main():
    params = {
        "nationality": "Hong Kong",
        "type": "Ironman"
    }
    
    logging.info("Fetching results from CoachCox search page...")
    all_finishers = []
    
    try:
        response = requests.get(SEARCH_PAGE_URL, params=params, headers=HEADERS, timeout=20)
        logging.info(f"Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table")
            
            if table:
                rows = table.find_all("tr")
                logging.info(f"Found results table with {len(rows)} rows.")
                
                for row in rows[1:]: # Skip header row
                    cols = [td.text.strip() for td in row.find_all(["td", "th"])]
                    if len(cols) >= 9:
                        all_finishers.append({
                            "athlete_name": cols[0],
                            "race_name": cols[1],
                            "age_group": cols[2],
                            "div_rank": cols[3],
                            "total_time": cols[4],
                            "overall_rank": cols[5],
                            "swim_time": cols[6],
                            "bike_time": cols[7],
                            "run_time": cols[8],
                            "gender": "M",
                            "race_year": 2026,
                            "source_url": SEARCH_PAGE_URL
                        })
            else:
                logging.warning("No results table found on the page matching criteria.")
        else:
            logging.error(f"Page request failed with status {response.status_code}")
    except Exception as e:
        logging.error(f"Error scraping search page: {e}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_finishers, f, indent=2, ensure_ascii=False)
    
    logging.info(f"Successfully wrote {len(all_finishers)} records to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
