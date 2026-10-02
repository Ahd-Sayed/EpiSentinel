import sqlite3

db_path = "epiguard.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

for table in ["Fact_WeeklyAlerts", "Fact_PatientVisits", "Fact_WeeklyVisitsAndSymptoms"]:
    c.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in c.fetchall()]
    print(f"Columns in {table}:")
    print(columns)
    print("Has prediction_id:", "prediction_id" in columns)
    print()

conn.close()
