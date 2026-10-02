from app.models.scenario import ScenarioDim
from app.models.alerts import WeeklyAlertFact
from app.models.disease import DiseaseDim
from app.extensions import db

class ScenarioService:
    @staticmethod
    def get_scenarios_validation():
        # Query scenarios
        scenarios = ScenarioDim.query.order_by(ScenarioDim.city.asc(), ScenarioDim.disease.asc()).all()
        
        # Load emojis from DiseaseDim for mapping
        diseases = DiseaseDim.query.all()
        emoji_map = {d.name: d.emoji for d in diseases}
        
        records = []
        for s in scenarios:
            records.append({
                "city":           s.city,
                "disease":        s.disease,
                "emoji":          emoji_map.get(s.disease, "🦠"),
                "lstm_available": bool(s.lstm_available),
                "first_alert":    str(s.first_alert_date) if s.first_alert_date else None,
                "lead_time":      round(float(s.lead_time_weeks), 2) if s.lead_time_weeks is not None else 0.0,
                "max_alert_level": s.max_alert_level,
                "detection_rate":  round(float(s.detection_rate) * 100, 1) if s.detection_rate is not None else 0.0,
                "detected":       bool(s.detected),
                "exact_start":    str(s.exact_start) if s.exact_start else None,
                "exact_end":      str(s.exact_end) if s.exact_end else None,
                "n_records":      int(s.n_records) if s.n_records else 0,
                "before_detected": bool(s.before_detected),
                "in_test_period": bool(s.in_test_period),
            })
        return records

    @staticmethod
    def get_scenario_timeline(city, disease, prediction_id=None):
        query = WeeklyAlertFact.query.filter_by(city=city, disease=disease)
        if prediction_id:
            query = query.filter(WeeklyAlertFact.prediction_id == prediction_id)
        else:
            query = query.filter(WeeklyAlertFact.prediction_id.is_(None))
            
        alerts = query.order_by(WeeklyAlertFact.week_start.asc()).all()
        
        # Outbreak real dates
        sc_row = ScenarioDim.query.filter_by(city=city, disease=disease).first()
        
        outbreak_start = str(sc_row.exact_start) if sc_row and sc_row.exact_start else None
        outbreak_end   = str(sc_row.exact_end)   if sc_row and sc_row.exact_end else None
        first_alert    = str(sc_row.first_alert_date) if sc_row and sc_row.first_alert_date else None
        
        return {
            "weeks":         [str(a.week_start) for a in alerts],
            "fusion_score":  [a.fusion_score for a in alerts],
            "IF_FLAG":       [a.if_flag for a in alerts],
            "DBSCAN_FLAG":   [a.dbscan_flag for a in alerts],
            "lstm_pred":     [a.lstm_pred for a in alerts],
            "lstm_prob":     [round(float(a.lstm_prob), 4) if a.lstm_prob is not None else 0.0 for a in alerts],
            "true_outbreak": [a.true_outbreak or 0 for a in alerts],
            "alert_level":   [a.alert_level for a in alerts],
            "outbreak_start": outbreak_start,
            "outbreak_end":   outbreak_end,
            "first_alert":    first_alert,
        }
