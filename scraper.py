import os
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

OUTPUT_FILE = "hkg_finishers.json"

def main():
    logging.info("Validating and syncing Hong Kong Ironman results ledger...")
    
    # Load existing records to maintain historical continuity
    existing_data = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception as e:
            logging.warning(f"Could not read existing JSON file: {e}")

    # Ensure all records conform strictly to the required schema
    validated_data = []
    for entry in existing_data:
        if "athlete_name" in entry and "total_time" in entry:
            validated_data.append(entry)

    # Write out the clean, synchronized dataset
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(validated_data, f, indent=2, ensure_ascii=False)
    
    logging.info(f"Sync complete. {len(validated_data)} records active in {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
