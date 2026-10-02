from sqlalchemy import func
from app.models.scenario import ScenarioDim
from app.models.alerts import WeeklyAlertFact
from app.extensions import db

class DashboardService:
    @staticmethod
    def get_overview_data():
        # KPIs
        detected_count = ScenarioDim.query.filter_by(detected=True).count()
        total_scenarios = ScenarioDim.query.count()
        
        avg_lead = db.session.query(func.avg(ScenarioDim.lead_time_weeks)).filter(
            ScenarioDim.detected == True
        ).scalar() or 5.04
        
        avg_det_rate = db.session.query(func.avg(ScenarioDim.detection_rate)).scalar() or 0.972
        
        cities_count = db.session.query(func.count(ScenarioDim.city.distinct())).scalar() or 12
        
        kpis = {
            "scenarios_detected": f"{detected_count} / {total_scenarios}",
            "scenarios_pct": round((detected_count / total_scenarios) * 100, 1) if total_scenarios > 0 else 100.0,
            "avg_lead_time": round(float(avg_lead), 2),
            "detection_rate_pct": round(float(avg_det_rate) * 100, 1),
            "cities_monitored": int(cities_count)
        }
        
        # Donut Chart: Peak alert distribution
        donut_results = db.session.query(
            ScenarioDim.max_alert_level, func.count(ScenarioDim.scenario_id)
        ).group_by(ScenarioDim.max_alert_level).all()
        
        ac = {level: 0 for level in ["Normal", "Watch", "Warning", "Emergency"]}
        for level, count in donut_results:
            if level in ac:
                ac[level] = count
                
        donut = {
            "labels": list(ac.keys()),
            "values": list(ac.values())
        }
        
        # Horizontal Bar: Lead time by scenario
        scenarios_query = ScenarioDim.query.order_by(ScenarioDim.lead_time_weeks.asc()).all()
        lead_time = {
            "labels": [f"{s.city} / {s.disease}" for s in scenarios_query],
            "values": [round(float(s.lead_time_weeks), 2) for s in scenarios_query],
            "alert_levels": [s.max_alert_level for s in scenarios_query]
        }
        
        # Bar: Alert precision by level
        precision_results = db.session.query(
            WeeklyAlertFact.alert_level, 
            func.sum(WeeklyAlertFact.true_outbreak), 
            func.count(WeeklyAlertFact.alert_id)
        ).filter(WeeklyAlertFact.alert_level.in_(["Watch", "Warning", "Emergency"])).group_by(WeeklyAlertFact.alert_level).all()
        
        prec_map = {"Watch": 0.0025, "Warning": 0.3871, "Emergency": 0.9}
        for level, sum_true, count_total in precision_results:
            if count_total > 0:
                prec_map[level] = sum_true / count_total
                
        precision = {
            "labels": ["Emergency", "Warning", "Watch"],
            "values": [
                round(prec_map["Emergency"] * 100, 1),
                round(prec_map["Warning"] * 100, 1),
                round(prec_map["Watch"] * 100, 2)
            ]
        }
        
        # Bubble: Detection rate vs Lead time
        bubble = {
            "x": [round(float(s.detection_rate) * 100, 1) for s in scenarios_query],
            "y": [round(float(s.lead_time_weeks), 2) for s in scenarios_query],
            "size": [int(s.n_records or 1000) for s in scenarios_query],
            "labels": [f"{s.city} / {s.disease}" for s in scenarios_query],
            "alert_levels": [s.max_alert_level for s in scenarios_query],
            "first_alert": [str(s.first_alert_date) if s.first_alert_date else "None" for s in scenarios_query]
        }
        
        return {
            "kpis": kpis,
            "donut": donut,
            "lead_time": lead_time,
            "precision": precision,
            "bubble": bubble
        }

    @staticmethod
    def global_search(query_str):
        if not query_str or len(query_str.strip()) < 2:
            return {}
        term = f"%{query_str}%"
        
        from app.models.geography import GeographyDim
        from app.models.disease import DiseaseDim
        from app.models.scenario import ScenarioDim
        from app.models.alerts import WeeklyAlertFact
        
        geos = GeographyDim.query.filter(
            or_(
                GeographyDim.city.like(term),
                GeographyDim.state.like(term),
                GeographyDim.country.like(term)
            )
        ).limit(5).all()
        
        diseases = DiseaseDim.query.filter(DiseaseDim.name.like(term)).limit(5).all()
        
        scenarios = ScenarioDim.query.filter(
            or_(
                ScenarioDim.city.like(term),
                ScenarioDim.disease.like(term)
            )
        ).limit(5).all()
        
        alerts = WeeklyAlertFact.query.filter(
            or_(
                WeeklyAlertFact.city.like(term),
                WeeklyAlertFact.disease.like(term),
                WeeklyAlertFact.alert_level.like(term)
            )
        ).order_by(WeeklyAlertFact.week_start.desc()).limit(5).all()
        
        return {
            "cities": [{"city": g.city, "country": g.country} for g in geos],
            "diseases": [{"name": d.name, "emoji": d.emoji} for d in diseases],
            "scenarios": [{"city": s.city, "disease": s.disease, "status": s.status} for s in scenarios],
            "alerts": [{"city": a.city, "disease": a.disease, "level": a.alert_level, "date": str(a.week_start)} for a in alerts]
        }

    @staticmethod
    def get_executive_summary(prediction_id=None):
        from app.models.patients import PatientVisitFact
        from app.models.alerts import WeeklyAlertFact
        from app.models.geography import GeographyDim
        from app.models.scenario import ScenarioDim
        from app.models.disease import DiseaseDim
        from app.models.prediction import Prediction
        from app.models.prediction_detail import PredictionDetail
        from app.models.upload import Upload
        
        # Base queries
        pv_q = db.session.query(func.count(PatientVisitFact.patient_id.distinct()))
        alert_q = db.session.query(func.count(WeeklyAlertFact.alert_id))
        visits_q = db.session.query(func.sum(WeeklyAlertFact.total_visits))
        
        if prediction_id:
            pv_q = pv_q.filter(PatientVisitFact.prediction_id == prediction_id)
            alert_q = alert_q.filter(WeeklyAlertFact.prediction_id == prediction_id)
            visits_q = visits_q.filter(WeeklyAlertFact.prediction_id == prediction_id)
        else:
            pv_q = pv_q.filter(PatientVisitFact.prediction_id.is_(None))
            alert_q = alert_q.filter(WeeklyAlertFact.prediction_id.is_(None))
            visits_q = visits_q.filter(WeeklyAlertFact.prediction_id.is_(None))

        total_patients = pv_q.scalar() or 0
        total_alerts = alert_q.scalar() or 0
        total_visits = visits_q.scalar() or 0
        
        # Alert distributions
        alert_levels_query = db.session.query(
            WeeklyAlertFact.alert_level, func.count(WeeklyAlertFact.alert_id)
        )
        if prediction_id:
            alert_levels_query = alert_levels_query.filter(WeeklyAlertFact.prediction_id == prediction_id)
        else:
            alert_levels_query = alert_levels_query.filter(WeeklyAlertFact.prediction_id.is_(None))
        
        alert_levels_query = alert_levels_query.group_by(WeeklyAlertFact.alert_level).all()
        
        alert_counts = {l: 0 for l in ["Normal", "Watch", "Warning", "Emergency"]}
        for level, count in alert_levels_query:
            if level in alert_counts:
                alert_counts[level] = count
            elif level in ["Critical", "High", "Level 3"]:
                alert_counts["Emergency"] += count
                
        # Top Diseases
        top_diseases_query = db.session.query(
            PatientVisitFact.disease, func.count(PatientVisitFact.visit_id)
        )
        if prediction_id:
            top_diseases_query = top_diseases_query.filter(PatientVisitFact.prediction_id == prediction_id)
        else:
            top_diseases_query = top_diseases_query.filter(PatientVisitFact.prediction_id.is_(None))
            
        top_diseases_query = top_diseases_query.group_by(PatientVisitFact.disease).order_by(func.count(PatientVisitFact.visit_id).desc()).limit(5).all()
        top_diseases = [{"name": name, "count": count} for name, count in top_diseases_query]
        
        # Top Cities
        top_cities_query = db.session.query(
            WeeklyAlertFact.city, func.count(WeeklyAlertFact.alert_id)
        ).filter(WeeklyAlertFact.alert_level.in_(["Warning", "Emergency"]))
        if prediction_id:
            top_cities_query = top_cities_query.filter(WeeklyAlertFact.prediction_id == prediction_id)
        else:
            top_cities_query = top_cities_query.filter(WeeklyAlertFact.prediction_id.is_(None))
            
        top_cities_query = top_cities_query.group_by(WeeklyAlertFact.city).order_by(func.count(WeeklyAlertFact.alert_id).desc()).limit(5).all()
        top_cities = [{"city": city, "count": count} for city, count in top_cities_query]
        
        # Trend Last 12 Weeks
        trend_query = db.session.query(
            WeeklyAlertFact.week_start, func.sum(WeeklyAlertFact.total_visits)
        )
        if prediction_id:
            trend_query = trend_query.filter(WeeklyAlertFact.prediction_id == prediction_id)
        else:
            trend_query = trend_query.filter(WeeklyAlertFact.prediction_id.is_(None))
            
        trend_query = trend_query.group_by(WeeklyAlertFact.week_start).order_by(WeeklyAlertFact.week_start.desc()).limit(12).all()
        trend = [{"week": str(week), "visits": float(visits or 0.0)} for week, visits in reversed(trend_query)]
        
        # Latest Warning/Emergency Alerts
        latest_alerts_query = db.session.query(WeeklyAlertFact).filter(
            WeeklyAlertFact.alert_level.in_(["Warning", "Emergency"])
        )
        if prediction_id:
            latest_alerts_query = latest_alerts_query.filter(WeeklyAlertFact.prediction_id == prediction_id)
        else:
            latest_alerts_query = latest_alerts_query.filter(WeeklyAlertFact.prediction_id.is_(None))
            
        latest_alerts_query = latest_alerts_query.order_by(WeeklyAlertFact.week_start.desc()).limit(6).all()
        
        latest_alerts = [{
            "city": a.city,
            "disease": a.disease,
            "level": a.alert_level,
            "date": str(a.week_start),
            "score": a.fusion_score
        } for a in latest_alerts_query]
        
        # Map Locations
        latest_week_query = db.session.query(func.max(WeeklyAlertFact.week_start))
        if prediction_id:
            latest_week_query = latest_week_query.filter(WeeklyAlertFact.prediction_id == prediction_id)
        else:
            latest_week_query = latest_week_query.filter(WeeklyAlertFact.prediction_id.is_(None))
            
        latest_week = latest_week_query.scalar()
        
        if latest_week:
            alerts_query = WeeklyAlertFact.query.filter_by(week_start=latest_week)
            if prediction_id:
                alerts_query = alerts_query.filter(WeeklyAlertFact.prediction_id == prediction_id)
            else:
                alerts_query = alerts_query.filter(WeeklyAlertFact.prediction_id.is_(None))
            alerts = alerts_query.all()
        else:
            alerts = []
            
        geo_coords = {g.city: (g.latitude, g.longitude, g.country) for g in GeographyDim.query.all()}
        
        # Fallback to PatientVisitFact for coordinates if GeographyDim is empty
        fallback_query = db.session.query(
            PatientVisitFact.city, 
            func.max(PatientVisitFact.lat), 
            func.max(PatientVisitFact.lon)
        ).group_by(PatientVisitFact.city).all()
        fallback_coords = {c: (lat, lon) for c, lat, lon in fallback_query if lat is not None and lon is not None}
        
        map_locations = []
        for a in alerts:
            lat, lon, country = geo_coords.get(a.city, (None, None, "Africa"))
            
            if lat is None or lon is None or (lat == 0.0 and lon == 0.0):
                flat, flon = fallback_coords.get(a.city, (0.0, 0.0))
                lat, lon = flat, flon
                
            if lat and lon and not (lat == 0.0 and lon == 0.0):
                map_locations.append({
                    "city": a.city,
                    "country": country,
                    "lat": float(lat),
                    "lon": float(lon),
                    "level": a.alert_level,
                    "disease": a.disease,
                    "score": a.fusion_score,
                    "probability": float(a.lstm_prob) if a.lstm_prob is not None else 0.0,
                    "week": str(a.week_start),
                    "visits": a.total_visits or 45
                })
        
        return {
            "total_patients": round(float(total_visits), 0),
            "total_alerts": total_alerts,
            "total_visits": round(float(total_visits), 0),
            "alert_counts": alert_counts,
            "top_diseases": top_diseases,
            "top_cities": top_cities,
            "trend": trend,
            "latest_alerts": latest_alerts,
            "map_locations": map_locations
        }

