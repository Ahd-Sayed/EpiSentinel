import os
import pandas as pd
import numpy as np

class ValidationService:
    @staticmethod
    def generate_validation_report(filepath):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
            
        n_rows = 0
        n_cols = 0
        detected_cols = []
        duplicate_rows_count = 0
        duplicate_visits_count = 0
        invalid_dates_count = 0
        null_values_count = 0
        unique_cities = set()
        unique_diseases = set()
        memory_usage_mb = 0.0
        date_min = None
        date_max = None
        latlon_nulls = 0
        
        group_weeks = {}
        
        try:
            chunk_size = 50000
            for chunk in pd.read_csv(filepath, chunksize=chunk_size):
                if not detected_cols:
                    detected_cols = list(chunk.columns)
                    n_cols = len(detected_cols)
                    
                n_rows += len(chunk)
                duplicate_rows_count += int(chunk.duplicated().sum()) # Chunk-local duplicates
                
                visit_key_cols = ["VISIT_DATE", "CITY", "DISEASE"]
                if "AGE_AT_VISIT" in chunk.columns:
                    visit_key_cols.append("AGE_AT_VISIT")
                # Handle case where required columns might be missing
                present_key_cols = [c for c in visit_key_cols if c in chunk.columns]
                if present_key_cols:
                    duplicate_visits_count += int(chunk.duplicated(subset=present_key_cols).sum())
                    
                if "VISIT_DATE" in chunk.columns:
                    parsed_dates = pd.to_datetime(chunk["VISIT_DATE"], errors="coerce")
                    invalid_dates_count += int(parsed_dates.isna().sum())
                    
                    valid_dates = parsed_dates.dropna()
                    if not valid_dates.empty:
                        c_min = valid_dates.min().strftime("%Y-%m-%d")
                        c_max = valid_dates.max().strftime("%Y-%m-%d")
                        if date_min is None or c_min < date_min: date_min = c_min
                        if date_max is None or c_max > date_max: date_max = c_max
                        
                    # For LSTM coverage
                    if "CITY" in chunk.columns and "DISEASE" in chunk.columns:
                        chunk["_date"] = parsed_dates
                        valid_chunk = chunk.dropna(subset=["_date"]).copy()
                        if not valid_chunk.empty:
                            valid_chunk["_week"] = valid_chunk["_date"].dt.to_period("W").apply(lambda r: r.start_time)
                            for city, disease, week in zip(valid_chunk["CITY"], valid_chunk["DISEASE"], valid_chunk["_week"]):
                                group_weeks.setdefault((city, disease), set()).add(week)
                                
                null_values_count += int(chunk.isna().sum().sum())
                
                if "CITY" in chunk.columns:
                    unique_cities.update(chunk["CITY"].dropna().unique())
                if "DISEASE" in chunk.columns:
                    unique_diseases.update(chunk["DISEASE"].dropna().unique())
                    
                if "LAT" in chunk.columns:
                    latlon_nulls += int(chunk["LAT"].isna().sum())
                if "LON" in chunk.columns:
                    latlon_nulls += int(chunk["LON"].isna().sum())
                    
                memory_usage_mb += float(chunk.memory_usage(deep=True).sum() / 1024 / 1024)
                
        except Exception as e:
            raise ValueError(f"Failed to read CSV dataset: {e}")
            
        total_cells = n_rows * max(1, n_cols)
        
        # 1. Required and optional columns checks
        required_cols = ["VISIT_DATE", "CITY", "COUNTRY", "DISEASE"]
        missing_cols = [c for c in required_cols if c not in detected_cols]
        
        optional_candidates = ["LAT", "LON", "AGE_AT_VISIT", "COMORBIDITY_COUNT"] + [
            f"sym_{s}" for s in [
                "fever", "chills", "headache", "fatigue", "vomiting", "diarrhea",
                "cough", "shortness_of_breath", "chest_pain", "rash", "muscle_pain",
                "abdominal_pain", "night_sweats", "weight_loss", "jaundice", "stiff_neck",
                "sensitivity_to_light", "red_eyes", "runny_nose", "sore_throat",
                "hemorrhage", "sweating", "dehydration", "muscle_cramps", "loss_of_smell",
                "swollen_lymph_nodes", "pain_behind_eyes", "general_weakness"
            ]
        ]
        
        detected_optional = [c for c in optional_candidates if c in detected_cols]
        missing_optional = [c for c in optional_candidates if c not in detected_cols]
        
        if missing_cols:
            return {
                "valid": False,
                "missing_required": missing_cols,
                "message": f"Missing required columns: {', '.join(missing_cols)}"
            }
            
        if date_min and date_max:
            date_range_str = f"{date_min} to {date_max}"
        else:
            date_range_str = "No valid dates found"
            
        unique_cities_count = len(unique_cities)
        unique_diseases_count = len(unique_diseases)
        
        est_exec_time_seconds = 0.5 + (n_rows / 10000) * 0.8
        
        completeness_score = (1.0 - (null_values_count / max(1, total_cells))) * 100
        duplicates_score = (1.0 - (duplicate_rows_count / max(1, n_rows))) * 100
        consistency_score = (1.0 - (invalid_dates_count / max(1, n_rows))) * 100
        
        skipped_groups = sum(1 for w in group_weeks.values() if len(w) < 8)
        total_groups = len(group_weeks)
        coverage_score = (1.0 - (skipped_groups / max(1, total_groups))) * 100 if total_groups > 0 else 0.0
            
        # Overall quality score
        overall_quality = (completeness_score + duplicates_score + consistency_score + (coverage_score if total_groups > 0 else 100.0)) / 4.0
        
        # 8. Automated recommendations list
        recs = []
        
        # Coordinates check
        has_coords = "LAT" in detected_cols and "LON" in detected_cols
        if not has_coords:
            recs.append({
                "type": "info",
                "message": "✔ Missing coordinates (LAT/LON) will be filled automatically using city center defaults."
            })
        else:
            if latlon_nulls > 0:
                recs.append({
                    "type": "info",
                    "message": "✔ Missing coordinates in some rows will be resolved automatically using city fallback matching."
                })
                
        # Symptoms check
        missing_syms = [s for s in optional_candidates if s.startswith("sym_") and s not in detected_cols]
        if missing_syms:
            recs.append({
                "type": "info",
                "message": "✔ Missing symptom columns will be treated as zero (not reported) in Isolation Forest."
            })
            
        # Duplicates check
        if duplicate_rows_count > 0:
            recs.append({
                "type": "warning",
                "message": f"⚠ Dataset contains {duplicate_rows_count:,} duplicate rows, which may artificially inflate alert scores."
            })
            
        # Invalid dates check
        if invalid_dates_count > 0:
            recs.append({
                "type": "warning",
                "message": f"⚠ {invalid_dates_count:,} rows contain unparseable VISIT_DATE values and will be dropped on execution."
            })
            
        # LSTM coverage checks
        if skipped_groups > 0:
            recs.append({
                "type": "warning",
                "message": f"⚠ LSTM will skip {skipped_groups} city-disease groups because they contain fewer than 8 weeks of history."
            })
            
        if len(recs) == 0:
            recs.append({
                "type": "success",
                "message": "✔ Perfect dataset structure! No quality issues detected."
            })
            
        return {
            "valid": True,
            "filename": os.path.basename(filepath),
            "filesize_mb": round(os.path.getsize(filepath) / 1024 / 1024, 2),
            "total_rows": n_rows,
            "total_columns": n_cols,
            "date_range": date_range_str,
            "unique_cities": unique_cities_count,
            "unique_diseases": unique_diseases_count,
            "required_cols": required_cols,
            "detected_optional": detected_optional,
            "missing_optional": missing_optional,
            "duplicate_rows": duplicate_rows_count,
            "duplicate_visits": duplicate_visits_count,
            "invalid_dates": invalid_dates_count,
            "null_values": null_values_count,
            "memory_usage_mb": round(memory_usage_mb, 2),
            "est_exec_time_seconds": round(est_exec_time_seconds, 1),
            "quality_scores": {
                "overall": round(overall_quality, 1),
                "completeness": round(completeness_score, 1),
                "duplicates": round(duplicates_score, 1),
                "consistency": round(consistency_score, 1),
                "coverage": round(coverage_score, 1)
            },
            "recommendations": recs
        }
