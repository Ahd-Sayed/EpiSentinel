import sqlite3

conn = sqlite3.connect("epiguard.db")
c = conn.cursor()
c.execute("SELECT count(*) FROM Fact_PatientVisits WHERE prediction_id IS NOT NULL")
print("Count of Fact_PatientVisits with prediction_id:", c.fetchone()[0])
conn.close()
