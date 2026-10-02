from flask import Blueprint, render_template, request, make_response, current_app
from flask_login import login_required
from app.services.explorer_service import ExplorerService
from app.utils.helpers import parse_prediction_id, api_response
from app.utils.pdf_generator import generate_pdf_bytes

explorer_bp = Blueprint("explorer", __name__)

@explorer_bp.route("/explorer")
@login_required
def explorer_page():
    return render_template("explorer.html", active="explorer")

@explorer_bp.route("/upload")
@login_required
def upload_page():
    return render_template("upload.html", active="upload")

@explorer_bp.route("/runs/<int:run_id>")
@login_required
def run_details_page(run_id):
    return render_template("run_details.html", run_id=run_id, active="upload")

@explorer_bp.route("/compare")
@login_required
def compare_page():
    return render_template("compare.html", active="explorer")

@explorer_bp.route("/warning-center")
@login_required
def warning_center_page():
    return render_template("warning_center.html", active="explorer")

@explorer_bp.route("/monitoring")
@login_required
def monitoring_page():
    return render_template("monitoring.html", active="monitoring")

@explorer_bp.route("/analytics")
@login_required
def analytics_page():
    return render_template("analytics.html", active="analytics")

# ── Tab 1: Weekly Alerts ──────────────────────────────────────────────────────
@explorer_bp.route("/api/data/alerts")
@login_required
def api_data_alerts():
    try:
        args = request.args
        page = int(args.get("page", 1))
        search = args.get("search")
        sort_by = args.get("sort_by")
        sort_dir = args.get("sort_dir", "asc")
        prediction_id = parse_prediction_id(args.get('prediction_id'))
        
        data, total, pg, pgs = ExplorerService.get_alerts(
            cities=args.getlist("city") or None,
            diseases=args.getlist("disease") or None,
            levels=args.getlist("level") or None,
            date_from=args.get("from"),
            date_to=args.get("to"),
            score_min=args.get("score_min"),
            search=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
            page=page,
            per_page=50,
            prediction_id=prediction_id
        )
        
        meta = {"page": pg, "pages": pgs, "total": total}
        return api_response(
            success=True, 
            message="Alert logs retrieved", 
            data={"data": data, "page": pg, "pages": pgs, "total": total}, 
            meta=meta
        )
    except Exception as e:
        return api_response(success=False, message=str(e), status_code=500)

# ── Tab 2: LSTM Predictions ───────────────────────────────────────────────────
@explorer_bp.route("/api/data/lstm")
@login_required
def api_data_lstm():
    try:
        args = request.args
        page = int(args.get("page", 1))
        search = args.get("search")
        sort_by = args.get("sort_by")
        sort_dir = args.get("sort_dir", "asc")
        prediction_id = parse_prediction_id(args.get('prediction_id'))
        
        data, total, pg, pgs = ExplorerService.get_lstm(
            country=args.get("country"),
            cities=args.getlist("city") or None,
            diseases=args.getlist("disease") or None,
            date_from=args.get("from"),
            date_to=args.get("to"),
            search=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
            page=page,
            per_page=50,
            prediction_id=prediction_id
        )
        
        meta = {"page": pg, "pages": pgs, "total": total}
        return api_response(
            success=True, 
            message="LSTM prediction logs retrieved", 
            data={"data": data, "page": pg, "pages": pgs, "total": total}, 
            meta=meta
        )
    except Exception as e:
        return api_response(success=False, message=str(e), status_code=500)

# ── Tab 3: Merged Signals ─────────────────────────────────────────────────────
@explorer_bp.route("/api/data/signals")
@login_required
def api_data_signals():
    try:
        args = request.args
        page = int(args.get("page", 1))
        search = args.get("search")
        sort_by = args.get("sort_by")
        sort_dir = args.get("sort_dir", "asc")
        prediction_id = parse_prediction_id(args.get('prediction_id'))
        
        data, total, pg, pgs = ExplorerService.get_signals(
            cities=args.getlist("city") or None,
            diseases=args.getlist("disease") or None,
            seasons=args.getlist("season") or None,
            date_from=args.get("from"),
            date_to=args.get("to"),
            search=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
            page=page,
            per_page=50,
            prediction_id=prediction_id
        )
        
        meta = {"page": pg, "pages": pgs, "total": total}
        return api_response(
            success=True, 
            message="Merged signal logs retrieved", 
            data={"data": data, "page": pg, "pages": pgs, "total": total}, 
            meta=meta
        )
    except Exception as e:
        return api_response(success=False, message=str(e), status_code=500)

# ── Tab 4: Patient Records (fully paginated) ──────────────────────────────────
@explorer_bp.route("/api/data/patients")
@login_required
def api_data_patients():
    try:
        args = request.args
        page = int(args.get("page", 1))
        search = args.get("search")
        sort_by = args.get("sort_by")
        sort_dir = args.get("sort_dir", "asc")
        prediction_id = parse_prediction_id(args.get('prediction_id'))
        
        data, total, pg, pgs = ExplorerService.get_patients(
            cities=args.getlist("city") or None,
            diseases=args.getlist("disease") or None,
            gender=args.get("gender"),
            season=args.get("season"),
            is_outbreak=args.get("is_outbreak"),
            if_pred=args.get("if_pred"),
            dbscan_pred=args.get("dbscan_pred"),
            search=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
            page=page,
            per_page=50,
            prediction_id=prediction_id
        )
        
        meta = {"page": pg, "pages": pgs, "total": total}
        # Include total file rows count to maintain identical fields as original API
        return api_response(
            success=True, 
            message="Patient records retrieved", 
            data={
                "data": data,
                "total": total,
                "page": pg,
                "pages": pgs,
                "sample_size": total,  # Now full dataset, sample_size = total
                "total_file_rows": 926292
            },
            meta=meta
        )
    except Exception as e:
        return api_response(success=False, message=str(e), status_code=500)

# ── Metadata Filters dropdowns ────────────────────────────────────────────────
@explorer_bp.route("/api/data/filters")
@login_required
def api_data_filters():
    try:
        data = ExplorerService.get_filters()
        return api_response(success=True, message="Metadata filters loaded", data=data)
    except Exception as e:
        return api_response(success=False, message=str(e), status_code=500)

# ── Capped Export: CSV / Excel / PDF ──────────────────────────────────────────
@explorer_bp.route("/api/data/export/<source>")
@login_required
def api_export(source):
    try:
        export_format = request.args.get("format", "csv").lower()
        limit = int(request.args.get("limit", 5000))
        limit = min(limit, 10000) # enforce maximum hard boundary
        
        cols, records = ExplorerService.get_export_data(source, limit)
        if not cols or not records:
            return api_response(success=False, message="Unknown or empty dataset source", status_code=400)
            
        if export_format == "xlsx":
            xlsx_bytes = ExplorerService.generate_excel_bytes(cols, records)
            resp = make_response(xlsx_bytes)
            resp.headers["Content-Disposition"] = f"attachment; filename={source}_export.xlsx"
            resp.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            return resp
            
        elif export_format == "pdf":
            # Generate PDF via reportlab utility
            pdf_bytes = generate_pdf_bytes(cols, records, source.upper())
            resp = make_response(pdf_bytes)
            resp.headers["Content-Disposition"] = f"attachment; filename={source}_export.pdf"
            resp.headers["Content-Type"] = "application/pdf"
            return resp
            
        else: # default to CSV
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([c.upper() for c in cols])
            for r in records:
                writer.writerow([r.get(c.upper() if c != "target_date" else c, "") for c in cols])
                
            resp = make_response(output.getvalue())
            resp.headers["Content-Disposition"] = f"attachment; filename={source}_export.csv"
            resp.headers["Content-Type"] = "text/csv"
            return resp
            
    except Exception as e:
        return api_response(success=False, message=str(e), status_code=500)
