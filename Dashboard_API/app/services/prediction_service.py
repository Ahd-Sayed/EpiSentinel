import os
import time
import pandas as pd
from datetime import datetime
from flask import current_app
from app.extensions import db
from app.models.upload import Upload
from app.models.prediction import Prediction
from app.models.prediction_detail import PredictionDetail
from app.models.warning import WarningLog
from app.models.audit_log import AuditLog
from app.models.patients import PatientVisitFact
from app.models.alerts import WeeklyAlertFact
from app.models.signals import WeeklyVisitsAndSymptomsFact
from app.services.pipeline_service import PipelineService
from app.utils.warning_parser import parse_pipeline_warnings
import threading

class PredictionService:
    @staticmethod
    def run_prediction_sync(upload_id, filepath, username, ip_address=None):
        app = current_app._get_current_object()
        
        # 1. Update upload status to Running
        upload = Upload.query.get(upload_id)
        if not upload:
            raise ValueError(f"Upload ID {upload_id} not found.")
            
        upload.status = "Running"
        upload.progress_stage = "Uploading Dataset"
        upload.progress_percent = 5
        upload.pipeline_message = "Initializing upload parameters..."
        db.session.commit()
        
        # Log audit trail
        audit = AuditLog(user=username, action=f"Prediction started for upload_id={upload_id}", ip_address=ip_address)
        db.session.add(audit)
        db.session.commit()
        
        start_time = time.time()
        
        def update_progress(stage, percent, message):
            elapsed = time.time() - start_time
            # Safe division
            if percent > 5:
                total_est = (elapsed / (percent - 5)) * 95 # adjusted for initial offset
                eta = max(0.0, total_est - elapsed)
            else:
                eta = 0.0
                
            upload.progress_stage = stage
            upload.progress_percent = percent
            upload.elapsed_seconds = round(elapsed, 1)
            upload.estimated_remaining = round(eta, 1)
            upload.pipeline_message = message
            
            if upload.total_rows > 0:
                upload.processed_rows = int(upload.total_rows * (percent / 100.0))
                if elapsed > 0:
                    upload.current_speed = round(upload.processed_rows / elapsed, 1)
            db.session.commit()
            
        try:
            # Stage 2: Reading CSV
            update_progress("Reading CSV", 10, "Loading visit CSV file into pandas DataFrame...")
            df = pd.read_csv(filepath)
            upload.total_rows = len(df)
            upload.rows = len(df)
            db.session.commit()
            
            # Stage 3: Validating Dataset
            update_progress("Validating Dataset", 15, "Performing required columns and index check...")
            
            # Map CITY to COUNTRY from the raw uploaded data
            city_country_map = {}
            if "CITY" in df.columns and "COUNTRY" in df.columns:
                city_country_map = df.drop_duplicates(subset=["CITY"]).set_index("CITY")["COUNTRY"].to_dict()
            
            # Get pipeline
            pipeline = PipelineService.get_pipeline()
            
            # Execute pipeline (it runs stages internally from 25% to 85%)
            result = pipeline.full_pipeline(df, progress_callback=update_progress)
            
            # Stage 10: Saving Results
            update_progress("Saving Results", 90, "Writing predictions and flags to local SQLite database...")
            alerts = result["alerts"]
            warnings_dict = result["warnings"]
            
            # Compute alert level counts
            counts = {"Normal": 0, "Watch": 0, "Warning": 0, "Emergency": 0}
            for a in alerts:
                lvl = a["alert_level"]
                if lvl in counts:
                    counts[lvl] += 1
                elif lvl in ["Critical", "High", "Level 3"]:
                    counts["Emergency"] += 1
                    
            duration = time.time() - start_time
            
            # Calculate total groups (unique city/disease pairs)
            total_groups = len(df.groupby(["CITY", "DISEASE"])) if ("CITY" in df.columns and "DISEASE" in df.columns) else 0
            
            # Save Prediction header
            prediction = Prediction(
                upload_id=upload_id,
                started_at=datetime.utcfromtimestamp(start_time),
                finished_at=datetime.utcnow(),
                duration=duration,
                total_groups=total_groups,
                total_alerts=len(alerts),
                normal_count=counts["Normal"],
                watch_count=counts["Watch"],
                warning_count=counts["Warning"],
                emergency_count=counts["Emergency"]
            )
            db.session.add(prediction)
            db.session.commit()
            
            # Save WeeklyAlertFact and PredictionDetail
            alerts_batch = []
            details_batch = []
            
            # Map weekly cases to populate total_visits
            weekly_cases = {}
            if "weekly" in result:
                for _, row in result["weekly"].iterrows():
                    key = (row["CITY"], row["DISEASE"], str(row["VISIT_WEEK_START"].date()))
                    weekly_cases[key] = row["case_count"]

            CHUNK_SIZE = 10000
            for a in alerts:
                prob = a["lstm_probability"]
                if pd.isna(prob): prob = None
                else: prob = float(prob)
                
                city_val = a["city"]
                disease_val = a["disease"]
                target_date_str = a["as_of_week"]
                
                # Fetch mapped total visits
                key = (city_val, disease_val, target_date_str)
                total_visits = weekly_cases.get(key, 0.0)
                
                alerts_batch.append({
                    "prediction_id": prediction.id,
                    "city": city_val,
                    "disease": disease_val,
                    "target_date": datetime.strptime(target_date_str, "%Y-%m-%d").date(),
                    "week_start": datetime.strptime(target_date_str, "%Y-%m-%d").date(),
                    "if_flag": int(a["if_flag"]),
                    "dbscan_flag": int(a["dbscan_flag"]),
                    "lstm_pred": int(a["lstm_flag"]),
                    "lstm_prob": prob,
                    "fusion_score": int(a["points"]),
                    "alert_level": a["alert_level"],
                    "true_outbreak": 0,
                    "total_visits": float(total_visits)
                })

                details_batch.append({
                    "prediction_id": prediction.id,
                    "city": city_val,
                    "country": city_country_map.get(city_val, "Unknown"),
                    "disease": disease_val,
                    "week": target_date_str,
                    "if_flag": int(a["if_flag"]),
                    "dbscan_flag": int(a["dbscan_flag"]),
                    "lstm_flag": int(a["lstm_flag"]),
                    "lstm_probability": prob,
                    "points": int(a["points"]),
                    "alert_level": a["alert_level"]
                })

                if len(alerts_batch) >= CHUNK_SIZE:
                    db.session.bulk_insert_mappings(WeeklyAlertFact, alerts_batch)
                    db.session.bulk_insert_mappings(PredictionDetail, details_batch)
                    db.session.commit()
                    alerts_batch = []
                    details_batch = []

            if alerts_batch:
                db.session.bulk_insert_mappings(WeeklyAlertFact, alerts_batch)
                db.session.bulk_insert_mappings(PredictionDetail, details_batch)
                db.session.commit()
            
            # Save PatientVisitFact in batches
            if "visits" in result:
                visits_df = result["visits"].copy()
                visits_df.columns = [c.lower() for c in visits_df.columns]
                visits_df["prediction_id"] = prediction.id
                if "visit_date" in visits_df.columns:
                    # Coerce errors to NaT, then drop or fill if necessary, but to_datetime usually handles it
                    visits_df["visit_date"] = pd.to_datetime(visits_df["visit_date"])
                
                valid_cols = set(c.name for c in PatientVisitFact.__table__.columns)
                cols_to_keep = [c for c in visits_df.columns if c in valid_cols]
                visits_df = visits_df[cols_to_keep]
                
                CHUNK_SIZE = 10000
                total_records = len(visits_df)
                for i in range(0, total_records, CHUNK_SIZE):
                    chunk = visits_df.iloc[i:i+CHUNK_SIZE].copy()
                    chunk = chunk.where(pd.notnull(chunk), None)
                    batch = chunk.to_dict(orient="records")
                    
                    db.session.bulk_insert_mappings(PatientVisitFact, batch)
                    db.session.commit()
                    pct = 90 + (3 * min(1.0, (i + CHUNK_SIZE) / total_records))
                    update_progress("Saving Results", pct, f"Saving patient data: {min(i + len(batch), total_records):,} / {total_records:,} rows...")

            # Save WeeklyVisitsAndSymptomsFact
            if "weekly" in result:
                weekly_df = result["weekly"].copy()
                weekly_df.columns = [c.lower() for c in weekly_df.columns]
                weekly_df["prediction_id"] = prediction.id
                if "visit_week_start" in weekly_df.columns:
                    weekly_df["week_start"] = pd.to_datetime(weekly_df["visit_week_start"])
                    weekly_df["target_date"] = weekly_df["week_start"]
                    
                valid_cols = set(c.name for c in WeeklyVisitsAndSymptomsFact.__table__.columns)
                cols_to_keep = [c for c in weekly_df.columns if c in valid_cols]
                weekly_df = weekly_df[cols_to_keep]
                
                CHUNK_SIZE = 10000
                total_w = len(weekly_df)
                for i in range(0, total_w, CHUNK_SIZE):
                    chunk = weekly_df.iloc[i:i+CHUNK_SIZE].copy()
                    chunk = chunk.where(pd.notnull(chunk), None)
                    batch = chunk.to_dict(orient="records")
                    
                    db.session.bulk_insert_mappings(WeeklyVisitsAndSymptomsFact, batch)
                    db.session.commit()
                    pct = 93 + (2 * min(1.0, (i + CHUNK_SIZE) / total_w))
                    update_progress("Saving Results", pct, f"Saving weekly grouped data: {min(i + len(batch), total_w):,} / {total_w:,} rows...")

            
            # Save WarningLogs
            parsed_warnings = parse_pipeline_warnings(warnings_dict)
            warnings_to_save = []
            for pw in parsed_warnings:
                warnings_to_save.append(WarningLog(
                    prediction_id=prediction.id,
                    warning_type=pw["type"],
                    warning_value=pw["value"]
                ))
            if warnings_to_save:
                db.session.bulk_save_objects(warnings_to_save)
                
            # Stage 12: Generating Analytics
            update_progress("Generating Analytics", 95, "Summarizing alerts distribution and indexing charts...")
            
            # Update upload status to Completed
            upload.status = "Completed"
            upload.processing_time = duration
            upload.warnings_count = len(parsed_warnings)
            
            # Done!
            update_progress("Completed", 100, "Pipeline execution completed successfully!")
            
            # Log audit
            audit = AuditLog(
                user=username, 
                action=f"Prediction completed successfully for upload_id={upload_id}. Alerts={len(alerts)}", 
                ip_address=ip_address
            )
            db.session.add(audit)
            db.session.commit()
            
            return prediction.id
            
        except Exception as e:
            db.session.rollback()
            duration = time.time() - start_time

            upload.status = "Failed"
            upload.processing_time = duration
            upload.pipeline_message = str(e)
            db.session.commit()
            
            # Log audit and error
            audit = AuditLog(
                user=username, 
                action=f"Prediction failed for upload_id={upload_id}: {str(e)[:200]}", 
                ip_address=ip_address
            )
            db.session.add(audit)
            db.session.commit()
            
            app.logger.error(f"Error in prediction run {upload_id}: {e}", exc_info=True)
            raise e

    @staticmethod
    def start_prediction_async(upload_id, filepath, username, ip_address=None):
        app = current_app._get_current_object()
        
        def worker():
            with app.app_context():
                try:
                    PredictionService.run_prediction_sync(upload_id, filepath, username, ip_address)
                except Exception as e:
                    app.logger.error(f"Async prediction failed for upload {upload_id}: {e}")
                    
        t = threading.Thread(target=worker)
        t.daemon = True
        t.start()
