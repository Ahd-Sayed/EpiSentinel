from flask import jsonify

def api_response(success=True, message="", data=None, meta=None, status_code=200):
    response = {
        "success": success,
        "message": message,
        "data": data if data is not None else {}
    }
    if meta is not None:
        response["meta"] = meta
        
    return jsonify(response), status_code


def parse_prediction_id(val):
    if val in [None, "", "null", "undefined", "historical"]:
        return None
    try:
        return int(val)
    except ValueError:
        return None
