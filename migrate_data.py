import pandas as pd
import sqlite3
import os

# --- Configuration ---
# 1. PATH TO YOUR OLD CSV FILE:
#    (Replace this with the actual path where your 5 rows CSV file is saved)
OLD_CSV_PATH = '/path/to/your/old/job_applications_Update.csv' 

# 2. NAME OF THE NEW SQLITE DATABASE FILE:
#    (Must match the name used in your Streamlit app: 'tracker.db')
NEW_DB_FILE = 'tracker.db' 

# 3. NAME OF THE TABLE:
#    (Must match the table name in your Streamlit app: 'applications')
TABLE_NAME = 'applications' 
# --------------------

def run_migration():
    """
    Loads data from the old CSV file and moves it into the new SQLite database.
    """
    print(f"--- Starting Data Migration from CSV to SQLite ---")
    print(f"Attempting to load CSV from: {OLD_CSV_PATH}")

    # 1. Load data from the old CSV file
    try:
        if not os.path.exists(OLD_CSV_PATH):
            print(f"ERROR: CSV file not found at {OLD_CSV_PATH}. Please check the path.")
            return

        # Read the CSV file into a DataFrame
        df = pd.read_csv(OLD_CSV_PATH)
        print(f"Successfully loaded {len(df)} rows from CSV.")

    except Exception as e:
        print(f"ERROR reading CSV: {e}")
        return

    # 2. Connect to the new SQLite database
    try:
        conn = sqlite3.connect(NEW_DB_FILE)
        print(f"Successfully connected to database: {NEW_DB_FILE}")
    except Exception as e:
        print(f"ERROR connecting to SQLite: {e}")
        return

    # 3. Write the DataFrame to the SQLite table
    try:
        # Use 'append' mode to add rows without creating a new table
        # We assume the table was already created by the Streamlit app's initialization logic.
        df.to_sql(TABLE_NAME, conn, if_exists='append', index=False)
        conn.commit()
        conn.close()
        print(f"SUCCESS: {len(df)} rows migrated and appended to table '{TABLE_NAME}'.")
    except Exception as e:
        print(f"ERROR writing data to SQLite table: {e}")

if __name__ == "__main__":
    run_migration()
