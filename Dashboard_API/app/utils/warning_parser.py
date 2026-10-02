import json

def parse_pipeline_warnings(warnings_dict):
    parsed = []
    # 1. missing_symptom_cols_filled
    val = warnings_dict.get("missing_symptom_cols_filled", [])
    if val:
        parsed.append({
            "type": "missing_symptom_cols_filled",
            "value": ", ".join(val)
        })
        
    # 2. rows_with_fallback_age
    val = warnings_dict.get("rows_with_fallback_age", 0)
    if val > 0:
        parsed.append({
            "type": "rows_with_fallback_age",
            "value": str(val)
        })
        
    # 3. rows_with_fallback_latlon
    val = warnings_dict.get("rows_with_fallback_latlon", 0)
    if val > 0:
        parsed.append({
            "type": "rows_with_fallback_latlon",
            "value": str(val)
        })
        
    # 4. unseen_disease_for_lstm
    val = warnings_dict.get("unseen_disease_for_lstm", [])
    if val:
        parsed.append({
            "type": "unseen_disease_for_lstm",
            "value": ", ".join(val)
        })
        
    # 5. unseen_city_country_for_lstm
    val = warnings_dict.get("unseen_city_country_for_lstm", [])
    if val:
        parsed.append({
            "type": "unseen_city_country_for_lstm",
            "value": ", ".join(val)
        })
        
    # 6. groups_too_short_for_lstm
    val = warnings_dict.get("groups_too_short_for_lstm", [])
    if val:
        parsed.append({
            "type": "groups_too_short_for_lstm",
            "value": ", ".join(val)
        })
        
    # 7. rows_dropped_bad_dates
    val = warnings_dict.get("rows_dropped_bad_dates", 0)
    if val > 0:
        parsed.append({
            "type": "rows_dropped_bad_dates",
            "value": str(val)
        })
        
    return parsed
