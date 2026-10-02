import sqlite3

def apply_migration():
    # Connect to the actual database used by Flask
    db_path = "db/episentinel.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    tables_to_alter = [
        "Fact_WeeklyAlerts",
        "Fact_PatientVisits",
        "Fact_WeeklyVisitsAndSymptoms"
    ]
    
    for table in tables_to_alter:
        # Check if column exists
        c.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in c.fetchall()]
        if "prediction_id" not in columns:
            print(f"Adding prediction_id to {table}")
            c.execute(f"ALTER TABLE {table} ADD COLUMN prediction_id INTEGER DEFAULT NULL")
            print(f"Added prediction_id to {table}.")
        else:
            print(f"{table} already has prediction_id.")
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    apply_migration()
