import os
import sqlite3
import pandas as pd
import json
from datetime import datetime
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "epiguard.db")
FILES = {
    "summary":        os.path.join(BASE_DIR, "task4_summary.json"),
    "validation":     os.path.join(BASE_DIR, "task4_validation.csv"),
    "validation_final": os.path.join(BASE_DIR, "task4_validation_FINAL.csv"),
    "scenarios":      os.path.join(BASE_DIR, "scenarios_exact_dates.csv"),
    "alerts":         os.path.join(BASE_DIR, "task4_weekly_alerts.csv"),
    "signals":        os.path.join(BASE_DIR, "merged_weekly_signals.csv"),
    "signals_overlap": os.path.join(BASE_DIR, "merged_weekly_signals_overlap.csv"),
    "lstm":           os.path.join(BASE_DIR, "lstm_test_predictions.csv"),
    "patients":       os.path.join(BASE_DIR, "test_df_with_if_dbscan_predictions.csv"),
}

DISEASE_EMOJI = {
    "Ebola virus disease": "🦠",
    "Cholera":             "💧",
    "COVID-19":            "😷",
    "Malaria":             "🦟",
    "Mpox":                "🟤",
    "Dengue fever":        "🦟",
    "Lassa fever":         "🔴",
    "Meningitis":          "🧠",
    "Typhoid fever":       "💊",
}

def create_db_and_tables():
    print("[INFO] Creating database and tables...")
    if os.path.exists(DB_PATH):
        print(f"[INFO] Removing old database at {DB_PATH}")
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Dim_Calendar
    cursor.execute("""
    CREATE TABLE Dim_Calendar (
        date_id TEXT PRIMARY KEY,
        date_val DATE NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        week INTEGER NOT NULL,
        day INTEGER NOT NULL,
        season TEXT
    )""")

    # 2. Dim_Geography
    cursor.execute("""
    CREATE TABLE Dim_Geography (
        geo_id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT UNIQUE NOT NULL,
        state TEXT,
        country TEXT NOT NULL,
        latitude REAL,
        longitude REAL
    )""")

    # 3. Dim_Diseases
    cursor.execute("""
    CREATE TABLE Dim_Diseases (
        disease_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        emoji TEXT
    )""")

    # 4. Dim_Scenarios
    cursor.execute("""
    CREATE TABLE Dim_Scenarios (
        scenario_id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT NOT NULL,
        disease TEXT NOT NULL,
        exact_start DATE,
        exact_end DATE,
        n_records INTEGER,
        status TEXT,
        lstm_available BOOLEAN,
        first_alert_date DATE,
        lead_time_weeks REAL,
        max_alert_level TEXT,
        detection_rate REAL,
        detected BOOLEAN,
        before_detected BOOLEAN,
        in_test_period BOOLEAN
    )""")

    # 5. Fact_WeeklyAlerts
    cursor.execute("""
    CREATE TABLE Fact_WeeklyAlerts (
        alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT NOT NULL,
        disease TEXT NOT NULL,
        target_date DATE NOT NULL,
        lstm_target_next_week INTEGER,
        lstm_prob REAL,
        lstm_pred INTEGER,
        week_start DATE,
        if_flag INTEGER,
        dbscan_flag INTEGER,
        true_outbreak INTEGER,
        total_visits REAL,
        fusion_score INTEGER,
        alert_level TEXT NOT NULL
    )""")

    # 6. Fact_WeeklyVisitsAndSymptoms
    cursor.execute("""
    CREATE TABLE Fact_WeeklyVisitsAndSymptoms (
        signal_id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT NOT NULL,
        disease TEXT NOT NULL,
        target_date DATE NOT NULL,
        lstm_prob REAL,
        lstm_pred INTEGER,
        week_start DATE,
        if_flag INTEGER,
        dbscan_flag INTEGER,
        true_outbreak INTEGER,
        total_visits REAL,
        lstm_target_next_week INTEGER,
        y_true INTEGER,
        is_overlap BOOLEAN
    )""")

    # 7. Fact_LSTMPredictions
    cursor.execute("""
    CREATE TABLE Fact_LSTMPredictions (
        lstm_id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name TEXT,
        target_date DATE NOT NULL,
        y_true INTEGER NOT NULL,
        lstm_prob REAL NOT NULL,
        lstm_pred INTEGER NOT NULL,
        country TEXT NOT NULL,
        city TEXT NOT NULL,
        disease TEXT NOT NULL
    )""")

    # 8. Fact_PatientVisits
    cursor.execute("""
    CREATE TABLE Fact_PatientVisits (
        visit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        visit_date TIMESTAMP NOT NULL,
        visit_year INTEGER,
        visit_month INTEGER,
        visit_week INTEGER,
        visit_day INTEGER,
        encounterclass TEXT,
        gender TEXT,
        city TEXT NOT NULL,
        state TEXT,
        country TEXT NOT NULL,
        lat REAL,
        lon REAL,
        season TEXT,
        comorbidity_count INTEGER,
        age_at_visit REAL,
        disease TEXT NOT NULL,
        visit_number REAL,
        sym_fever INTEGER,
        sym_chills INTEGER,
        sym_headache INTEGER,
        sym_fatigue INTEGER,
        sym_vomiting INTEGER,
        sym_diarrhea INTEGER,
        sym_cough INTEGER,
        sym_shortness_of_breath INTEGER,
        sym_chest_pain INTEGER,
        sym_rash INTEGER,
        sym_muscle_pain INTEGER,
        sym_abdominal_pain INTEGER,
        sym_night_sweats INTEGER,
        sym_weight_loss INTEGER,
        sym_jaundice INTEGER,
        sym_stiff_neck INTEGER,
        sym_sensitivity_to_light INTEGER,
        sym_red_eyes INTEGER,
        sym_runny_nose INTEGER,
        sym_sore_throat INTEGER,
        sym_hemorrhage INTEGER,
        sym_sweating INTEGER,
        sym_dehydration INTEGER,
        sym_muscle_cramps INTEGER,
        sym_loss_of_smell INTEGER,
        sym_swollen_lymph_nodes INTEGER,
        sym_pain_behind_eyes INTEGER,
        sym_general_weakness INTEGER,
        is_outbreak INTEGER,
        hospital_name TEXT,
        city_enc INTEGER,
        country_enc INTEGER,
        disease_enc INTEGER,
        season_enc INTEGER,
        gender_enc INTEGER,
        age_at_visit_norm REAL,
        lat_norm REAL,
        lon_norm REAL,
        comorbidity_count_norm REAL,
        day_index REAL,
        day_index_norm REAL,
        recent_case_count REAL,
        recent_case_count_norm REAL,
        if_pred INTEGER,
        if_score REAL,
        pca_0 REAL,
        pca_1 REAL,
        pca_2 REAL,
        pca_3 REAL,
        pca_4 REAL,
        pca_5 REAL,
        pca_6 REAL,
        pca_7 REAL,
        dbscan_score REAL,
        dbscan_pred INTEGER
    )""")

    # 9. Users table
    cursor.execute("""
    CREATE TABLE Users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'Viewer'
    )""")

    conn.commit()
    conn.close()
    print("[OK] Database and tables created.")


def import_geography_and_diseases():
    print("[INFO] Loading Geography and Diseases metadata...")
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Geographies from patients dataset (load a sample of 5000 to extract lat/lon, or all unique cities)
    df_p = pd.read_csv(FILES["patients"], usecols=["CITY", "STATE", "COUNTRY", "LAT", "LON"])
    df_geo = df_p.drop_duplicates(subset=["CITY"]).copy()
    
    for _, row in df_geo.iterrows():
        try:
            conn.execute(
                "INSERT INTO Dim_Geography (city, state, country, latitude, longitude) VALUES (?, ?, ?, ?, ?)",
                (row["CITY"], row["STATE"], row["COUNTRY"], row["LAT"], row["LON"])
            )
        except sqlite3.IntegrityError:
            pass

    # 2. Diseases from emojis dictionary
    for name, emoji in DISEASE_EMOJI.items():
        try:
            conn.execute(
                "INSERT INTO Dim_Diseases (name, emoji) VALUES (?, ?)",
                (name, emoji)
            )
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    print("[OK] Dim_Geography and Dim_Diseases tables seeded.")


def import_scenarios():
    print("[INFO] Loading Scenarios...")
    conn = sqlite3.connect(DB_PATH)
    
    # Merge scenarios_exact_dates, validation_FINAL, and validation (broken)
    sc = pd.read_csv(FILES["scenarios"])
    vf = pd.read_csv(FILES["validation_final"])
    v = pd.read_csv(FILES["validation"])
    
    merged = vf.merge(sc, on=["CITY", "DISEASE"], how="left")
    
    for _, row in merged.iterrows():
        # Get before_detected from broken validation file
        broken_row = v[(v["CITY"] == row["CITY"]) & (v["DISEASE"] == row["DISEASE"])]
        before_detected = bool(broken_row["detected"].iloc[0]) if not broken_row.empty else False
        in_test_period = bool(broken_row["in_test_period"].iloc[0]) if not broken_row.empty else True
        
        # Parse Dates
        first_alert = row.get("first_alert_date")
        first_alert_str = str(pd.to_datetime(first_alert).date()) if pd.notna(first_alert) else None
        
        exact_start_str = str(pd.to_datetime(row.get("exact_start")).date()) if pd.notna(row.get("exact_start")) else None
        exact_end_str = str(pd.to_datetime(row.get("exact_end")).date()) if pd.notna(row.get("exact_end")) else None
        
        conn.execute("""
            INSERT INTO Dim_Scenarios (
                city, disease, exact_start, exact_end, n_records, status, 
                lstm_available, first_alert_date, lead_time_weeks, max_alert_level, 
                detection_rate, detected, before_detected, in_test_period
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row["CITY"], row["DISEASE"], exact_start_str, exact_end_str, int(row["n_records"]) if pd.notna(row["n_records"]) else 0, row.get("status", "OK"),
            bool(row.get("lstm_available", True)), first_alert_str, float(row["lead_time_weeks"]), str(row["max_alert_level"]),
            float(row["detection_rate"]), bool(row["detected"]), before_detected, in_test_period
        ))

    conn.commit()
    conn.close()
    print("[OK] Dim_Scenarios table populated.")


def import_weekly_alerts():
    print("[INFO] Loading Weekly Alerts...")
    conn = sqlite3.connect(DB_PATH)
    
    df = pd.read_csv(FILES["alerts"])
    df["target_date"] = pd.to_datetime(df["target_date"]).dt.strftime("%Y-%m-%d")
    df["WEEK_START"] = pd.to_datetime(df["WEEK_START"]).dt.strftime("%Y-%m-%d")
    
    # Map column names to lowercase to match the DB schema
    df.columns = [c.lower() for c in df.columns]
    
    df.to_sql("Fact_WeeklyAlerts", conn, if_exists="append", index=False)
    
    conn.commit()
    conn.close()
    print("[OK] Fact_WeeklyAlerts populated.")


def import_weekly_signals():
    print("[INFO] Loading Weekly Visits and Signals...")
    conn = sqlite3.connect(DB_PATH)
    
    # Read both signals datasets
    s1 = pd.read_csv(FILES["signals"])
    s2 = pd.read_csv(FILES["signals_overlap"])
    
    # Add overlap flag
    s1["is_overlap"] = False
    s2["is_overlap"] = True
    
    s1["target_date"] = pd.to_datetime(s1["target_date"]).dt.strftime("%Y-%m-%d")
    s1["WEEK_START"] = pd.to_datetime(s1["WEEK_START"]).dt.strftime("%Y-%m-%d")
    s2["target_date"] = pd.to_datetime(s2["target_date"]).dt.strftime("%Y-%m-%d")
    s2["WEEK_START"] = pd.to_datetime(s2["WEEK_START"]).dt.strftime("%Y-%m-%d")
    
    # Clean up column names for insertions
    s1_cols = {
        "CITY": "city", "DISEASE": "disease", "target_date": "target_date", "lstm_prob": "lstm_prob",
        "lstm_pred": "lstm_pred", "WEEK_START": "week_start", "IF_FLAG": "if_flag", "DBSCAN_FLAG": "dbscan_flag",
        "true_outbreak": "true_outbreak", "total_visits": "total_visits", "is_overlap": "is_overlap", "y_true": "y_true"
    }
    s2_cols = {
        "CITY": "city", "DISEASE": "disease", "target_date": "target_date", "lstm_prob": "lstm_prob",
        "lstm_pred": "lstm_pred", "WEEK_START": "week_start", "IF_FLAG": "if_flag", "DBSCAN_FLAG": "dbscan_flag",
        "true_outbreak": "true_outbreak", "total_visits": "total_visits", "is_overlap": "is_overlap", "lstm_target_next_week": "lstm_target_next_week"
    }
    
    # Insert in bulk
    df1 = s1.rename(columns=s1_cols)[list(s1_cols.values())]
    df2 = s2.rename(columns=s2_cols)[list(s2_cols.values())]
    
    df1.to_sql("Fact_WeeklyVisitsAndSymptoms", conn, if_exists="append", index=False)
    df2.to_sql("Fact_WeeklyVisitsAndSymptoms", conn, if_exists="append", index=False)
    
    conn.commit()
    conn.close()
    print("[OK] Fact_WeeklyVisitsAndSymptoms populated.")


def import_lstm_predictions():
    print("[INFO] Loading LSTM Predictions...")
    conn = sqlite3.connect(DB_PATH)
    
    df = pd.read_csv(FILES["lstm"])
    df["target_date"] = pd.to_datetime(df["target_date"]).dt.strftime("%Y-%m-%d")
    
    cols = {
        "group": "group_name", "target_date": "target_date", "y_true": "y_true", "lstm_prob": "lstm_prob",
        "lstm_pred": "lstm_pred", "COUNTRY": "country", "CITY": "city", "DISEASE": "disease"
    }
    
    df_db = df.rename(columns=cols)[list(cols.values())]
    df_db.to_sql("Fact_LSTMPredictions", conn, if_exists="append", index=False)
    
    conn.commit()
    conn.close()
    print("[OK] Fact_LSTMPredictions populated.")


def import_patient_visits():
    print("[INFO] Bulk loading Patient Visits (926k+ rows). Please wait...")
    conn = sqlite3.connect(DB_PATH)
    
    # Load and insert in chunks of 100k rows
    chunksize = 100_000
    total_loaded = 0
    start_time = datetime.now()
    
    for chunk in pd.read_csv(FILES["patients"], chunksize=chunksize):
        # Convert date columns
        chunk["VISIT_DATE"] = pd.to_datetime(chunk["VISIT_DATE"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # Clean column names to lowercase
        chunk.columns = [c.lower() for c in chunk.columns]
        
        # Insert
        chunk.to_sql("Fact_PatientVisits", conn, if_exists="append", index=False)
        total_loaded += len(chunk)
        print(f"  Inserted {total_loaded:,} patient records...")
        
    duration = datetime.now() - start_time
    print(f"[OK] Fact_PatientVisits fully loaded ({total_loaded:,} rows) in {duration.total_seconds():.1f}s.")
    conn.commit()
    conn.close()


def populate_dim_calendar():
    print("[INFO] Populating Dim_Calendar...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Extract unique dates from alerts and patient visits
    dates = set()
    
    # 1. Weekly Alerts
    cursor.execute("SELECT DISTINCT target_date FROM Fact_WeeklyAlerts")
    for row in cursor.fetchall():
        if row[0]:
            dates.add(row[0].split()[0]) # YYYY-MM-DD
            
    # 2. Patient visits
    cursor.execute("SELECT DISTINCT strftime('%Y-%m-%d', visit_date) FROM Fact_PatientVisits")
    for row in cursor.fetchall():
        if row[0]:
            dates.add(row[0])
            
    print(f"  Found {len(dates):,} unique dates.")
    
    # Build insertion rows
    for d_str in sorted(list(dates)):
        try:
            dt = datetime.strptime(d_str, "%Y-%m-%d")
            # Determine Season based on month (simple mapping for demonstration)
            # Wet season: June to September (West Africa monsoon, etc.)
            # Dry season: November to March
            # Transition: April/May, October
            m = dt.month
            if m in [6, 7, 8, 9]:
                season = "Wet_Season"
            elif m in [11, 12, 1, 2, 3]:
                season = "Dry_Season"
            else:
                season = "Transition_Season"
                
            cursor.execute(
                "INSERT INTO Dim_Calendar (date_id, date_val, year, month, week, day, season) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (d_str, d_str, dt.year, dt.month, int(dt.strftime("%W")), dt.day, season)
            )
        except Exception as e:
            pass

    conn.commit()
    conn.close()
    print("[OK] Dim_Calendar table fully populated.")


def seed_users():
    print("[INFO] Seeding initial user accounts...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    users = [
        ("admin", "admin123", "Admin"),
        ("researcher", "research123", "Researcher"),
        ("viewer", "viewer123", "Viewer")
    ]
    
    for username, pwd, role in users:
        p_hash = generate_password_hash(pwd)
        try:
            cursor.execute(
                "INSERT INTO Users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, p_hash, role)
            )
            print(f"  Created user '{username}' with role '{role}'")
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    print("[OK] Seeding users completed.")


def create_indexes():
    print("[INFO] Creating Database Indexes for performance...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # List of indexes to create
    indexes = [
        # Fact_WeeklyAlerts
        ("idx_alerts_city_disease", "Fact_WeeklyAlerts", "city, disease"),
        ("idx_alerts_target_date", "Fact_WeeklyAlerts", "target_date"),
        ("idx_alerts_week_start", "Fact_WeeklyAlerts", "week_start"),
        ("idx_alerts_alert_level", "Fact_WeeklyAlerts", "alert_level"),
        ("idx_alerts_true_outbreak", "Fact_WeeklyAlerts", "true_outbreak"),
        
        # Fact_WeeklyVisitsAndSymptoms
        ("idx_signals_city_disease", "Fact_WeeklyVisitsAndSymptoms", "city, disease"),
        ("idx_signals_target_date", "Fact_WeeklyVisitsAndSymptoms", "target_date"),
        ("idx_signals_week_start", "Fact_WeeklyVisitsAndSymptoms", "week_start"),
        ("idx_signals_true_outbreak", "Fact_WeeklyVisitsAndSymptoms", "true_outbreak"),
        
        # Fact_LSTMPredictions
        ("idx_lstm_city_disease", "Fact_LSTMPredictions", "city, disease"),
        ("idx_lstm_target_date", "Fact_LSTMPredictions", "target_date"),
        
        # Fact_PatientVisits (Extremely important for 926k records)
        ("idx_patients_visit_date", "Fact_PatientVisits", "visit_date"),
        ("idx_patients_city", "Fact_PatientVisits", "city"),
        ("idx_patients_disease", "Fact_PatientVisits", "disease"),
        ("idx_patients_gender", "Fact_PatientVisits", "gender"),
        ("idx_patients_season", "Fact_PatientVisits", "season"),
        ("idx_patients_is_outbreak", "Fact_PatientVisits", "is_outbreak"),
        ("idx_patients_if_pred", "Fact_PatientVisits", "if_pred"),
        ("idx_patients_dbscan_pred", "Fact_PatientVisits", "dbscan_pred"),
        
        # Dim_Scenarios
        ("idx_scenarios_city_disease", "Dim_Scenarios", "city, disease"),
    ]
    
    for idx_name, table, columns in indexes:
        print(f"  Creating index {idx_name} on {table}({columns})...")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({columns})")
        
    conn.commit()
    conn.close()
    print("[OK] Indexes created successfully.")


if __name__ == "__main__":
    start_time = datetime.now()
    print("==================================================")
    print("      EpiGuard Africa SQLite Ingestion Script")
    print("==================================================")
    
    create_db_and_tables()
    import_geography_and_diseases()
    import_scenarios()
    import_weekly_alerts()
    import_weekly_signals()
    import_lstm_predictions()
    import_patient_visits()
    populate_dim_calendar()
    seed_users()
    create_indexes()
    
    duration = datetime.now() - start_time
    print("==================================================")
    print(f"Database build completed successfully in {duration.total_seconds():.1f}s.")
    print("==================================================")
