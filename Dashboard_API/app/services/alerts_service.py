from sqlalchemy import func, or_, case
from app.models.alerts import WeeklyAlertFact
from app.models.prediction_detail import PredictionDetail
from app.models.scenario import ScenarioDim
from app.extensions import db
import io
import csv
from datetime import datetime

class AlertsService:
    @staticmethod
    def _apply_filters(query, model, cities=None, diseases=None, levels=None, date_from=None, date_to=None, prediction_id=None):
        if prediction_id:
            query = query.filter(model.prediction_id == prediction_id)
        else:
            if hasattr(model, 'prediction_id'):
                query = query.filter(model.prediction_id.is_(None))
        if cities:
            query = query.filter(model.city.in_(cities))
        if diseases:
            query = query.filter(model.disease.in_(diseases))
        if levels:
            query = query.filter(model.alert_level.in_(levels))
        if date_from:
            try:
                dt = datetime.strptime(date_from, "%Y-%m-%d").date()
                date_col = model.week if hasattr(model, 'week') else model.week_start
                query = query.filter(date_col >= dt)
            except ValueError:
                pass
        if date_to:
            try:
                dt = datetime.strptime(date_to, "%Y-%m-%d").date()
                date_col = model.week if hasattr(model, 'week') else model.week_start
                query = query.filter(date_col <= dt)
            except ValueError:
                pass
        return query

    @staticmethod
    def get_filters(prediction_id=None):
        model = WeeklyAlertFact
        id_col = model.alert_id
        date_col = model.week_start

        # Quick distinct filters with order
        cities = db.session.query(model.city.distinct()).order_by(model.city).all()
        diseases = db.session.query(model.disease.distinct()).order_by(model.disease).all()
        
        min_date = db.session.query(func.min(date_col)).scalar()
        max_date = db.session.query(func.max(date_col)).scalar()
        
        from app.models.geography import GeographyDim
        geo_records = GeographyDim.query.all()
        geo_details = {
            g.city: {"state": g.state or "", "country": g.country}
            for g in geo_records
        }
        
        return {
            "cities": [c[0] for c in cities if c[0]],
            "diseases": [d[0] for d in diseases if d[0]],
            "date_min": str(min_date) if min_date else "",
            "date_max": str(max_date) if max_date else "",
            "geo_details": geo_details
        }

    @staticmethod
    def get_summary(cities=None, diseases=None, levels=None, date_from=None, date_to=None, prediction_id=None):
        model = WeeklyAlertFact
        id_col = model.alert_id
        date_col = model.week_start

        # 1. Total counts by level
        query = db.session.query(
            model.alert_level, func.count(id_col)
        )
        query = AlertsService._apply_filters(query, model, cities, diseases, levels, date_from, date_to, prediction_id)
        results = query.group_by(model.alert_level).all()
        
        counts = {level: 0 for level in ["Normal", "Watch", "Warning", "Emergency"]}
        total = 0
        for level, count in results:
            if level in counts:
                counts[level] = count
                total += count
        counts["total"] = total

        # 2. Time-series weekly alert counts for sparklines
        trend_query = db.session.query(
            date_col,
            model.alert_level,
            func.count(id_col)
        )
        trend_query = AlertsService._apply_filters(trend_query, model, cities, diseases, levels, date_from, date_to, prediction_id)
        trend_results = trend_query.group_by(date_col, model.alert_level).order_by(date_col.asc()).all()

        weeks_map = {}
        for w_start, lvl, cnt in trend_results:
            if w_start is None:
                continue
            w_str = str(w_start)
            if w_str not in weeks_map:
                weeks_map[w_str] = {l: 0 for l in ["Normal", "Watch", "Warning", "Emergency", "total"]}
            if lvl in weeks_map[w_str]:
                weeks_map[w_str][lvl] = cnt
            weeks_map[w_str]["total"] += cnt

        sorted_weeks = sorted(weeks_map.keys())
        trends = {
            "weeks": sorted_weeks,
            "Normal": [weeks_map[w]["Normal"] for w in sorted_weeks],
            "Watch": [weeks_map[w]["Watch"] for w in sorted_weeks],
            "Warning": [weeks_map[w]["Warning"] for w in sorted_weeks],
            "Emergency": [weeks_map[w]["Emergency"] for w in sorted_weeks],
            "total": [weeks_map[w]["total"] for w in sorted_weeks]
        }
        
        counts["trends"] = trends
        return counts

    @staticmethod
    def get_timeline(city=None, disease=None, prediction_id=None):
        query = WeeklyAlertFact.query
        if prediction_id:
            query = query.filter_by(prediction_id=prediction_id)
        else:
            query = query.filter(WeeklyAlertFact.prediction_id.is_(None))
            
        if city:
            query = query.filter_by(city=city)
        if disease:
            query = query.filter_by(disease=disease)
        
        alerts = query.order_by(WeeklyAlertFact.week_start.asc()).all()
        
        # Outbreak real dates from Scenarios
        outbreak_start = outbreak_end = None
        if city and disease:
            sc = ScenarioDim.query.filter_by(city=city, disease=disease).first()
            if sc:
                outbreak_start = str(sc.exact_start) if sc.exact_start else None
                outbreak_end = str(sc.exact_end) if sc.exact_end else None
                
        return {
            "weeks": [str(a.week_start) for a in alerts],
            "fusion_score": [a.fusion_score for a in alerts],
            "alert_level": [a.alert_level for a in alerts],
            "IF_FLAG": [a.if_flag for a in alerts],
            "DBSCAN_FLAG": [a.dbscan_flag for a in alerts],
            "lstm_pred": [a.lstm_pred for a in alerts],
            "lstm_prob": [round(float(a.lstm_prob), 4) if a.lstm_prob is not None else 0.0 for a in alerts],
            "total_visits": [a.total_visits or 0.0 for a in alerts],
            "true_outbreak": [a.true_outbreak or 0 for a in alerts],
            "outbreak_start": outbreak_start,
            "outbreak_end": outbreak_end
        }

    @staticmethod
    def get_heatmap(disease=None, prediction_id=None):
        model = WeeklyAlertFact
        id_col = model.alert_id
        date_col = model.week_start

        # Subquery to extract month in SQL (substr YYYY-MM) and compute max alert level numeric value
        # Numeric alert mapping: Normal=0, Watch=1, Warning=2, Emergency=3
        alert_mapping = case(
            (model.alert_level == "Emergency", 3),
            (model.alert_level == "Warning", 2),
            (model.alert_level == "Watch", 1),
            else_=0
        )
        
        query = db.session.query(
            model.city,
            func.substr(date_col, 1, 7).label("month"),
            func.max(alert_mapping).label("max_alert_numeric")
        )
        
        if prediction_id:
            query = query.filter(model.prediction_id == prediction_id)
        else:
            query = query.filter(model.prediction_id.is_(None))
            
        if disease and disease != "all":
            query = query.filter(model.disease == disease)
            
        results = query.group_by(model.city, func.substr(date_col, 1, 7)).all()
        
        # Build pivot structure
        cities_set = set()
        months_set = set()
        data_map = {} # (city, month) -> val
        
        for r_city, r_month, r_val in results:
            if not r_city or not r_month:
                continue
            cities_set.add(r_city)
            months_set.add(r_month)
            data_map[(r_city, r_month)] = int(r_val)
            
        cities = sorted(list(cities_set))
        months = sorted(list(months_set))
        
        z = []
        for c in cities:
            row = []
            for m in months:
                row.append(data_map.get((c, m), 0))
            z.append(row)
            
        return {
            "cities": cities,
            "months": months,
            "z": z
        }

    @staticmethod
    def get_paginated_alerts(cities=None, diseases=None, levels=None, date_from=None, date_to=None, page=1, per_page=50, prediction_id=None):
        model = WeeklyAlertFact
        id_col = model.alert_id
        date_col = model.week_start

        query = WeeklyAlertFact.query
        query = AlertsService._apply_filters(query, model, cities, diseases, levels, date_from, date_to, prediction_id)
        
        # Order chronologically and by geography
        query = query.order_by(date_col.desc(), model.city.asc())
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        records = []
        for a in pagination.items:
            records.append({
                "CITY": a.city,
                "DISEASE": a.disease,
                "WEEK_START": str(a.week_start),
                "IF_FLAG": a.if_flag,
                "DBSCAN_FLAG": a.dbscan_flag,
                "lstm_pred": a.lstm_pred,
                "lstm_prob": round(float(a.lstm_prob), 4) if a.lstm_prob is not None else 0.0,
                "fusion_score": a.fusion_score,
                "alert_level": a.alert_level,
                "total_visits": a.total_visits or 0.0
            })
            
        return {
            "data": records,
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages
        }

    @staticmethod
    def generate_csv_export(cities=None, diseases=None, levels=None, date_from=None, date_to=None, prediction_id=None):
        model = WeeklyAlertFact
        id_col = model.alert_id
        date_col = model.week_start

        query = WeeklyAlertFact.query
        query = AlertsService._apply_filters(query, model, cities, diseases, levels, date_from, date_to, prediction_id)
        query = query.order_by(date_col.desc())
        
        # Limit to 5000 rows to prevent memory exhaustion
        alerts = query.limit(5000).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "CITY", "DISEASE", "WEEK_START", "TARGET_DATE", "IF_FLAG", 
            "DBSCAN_FLAG", "LSTM_PRED", "LSTM_PROB", "FUSION_SCORE", 
            "ALERT_LEVEL", "TOTAL_VISITS", "TRUE_OUTBREAK"
        ])
        
        for a in alerts:
            writer.writerow([
                a.city, a.disease, str(a.week_start), str(a.target_date), a.if_flag,
                a.dbscan_flag, a.lstm_pred, a.lstm_prob, a.fusion_score,
                a.alert_level, a.total_visits, a.true_outbreak
            ])
            
        return output.getvalue()
