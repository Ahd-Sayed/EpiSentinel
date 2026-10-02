import re

# 1. Update helpers.py
helpers_path = "app/utils/helpers.py"
with open(helpers_path, "r") as f:
    helpers_content = f.read()

if "parse_prediction_id" not in helpers_content:
    helpers_content += """

def parse_prediction_id(val):
    if val in [None, "", "null", "undefined", "historical"]:
        return None
    try:
        return int(val)
    except ValueError:
        return None
"""
    with open(helpers_path, "w") as f:
        f.write(helpers_content)

# 2. Update explorer_service.py
exp_srv_path = "app/services/explorer_service.py"
with open(exp_srv_path, "r") as f:
    exp_srv_content = f.read()

# Add prediction_id=None to get_alerts
exp_srv_content = re.sub(
    r"def get_alerts\(cities=None, diseases=None, levels=None, date_from=None, date_to=None, \n                   score_min=None, search=None, sort_by=None, sort_dir=\"asc\", page=1, per_page=50\):",
    r"def get_alerts(cities=None, diseases=None, levels=None, date_from=None, date_to=None,\n                   score_min=None, search=None, sort_by=None, sort_dir='asc', page=1, per_page=50, prediction_id=None):",
    exp_srv_content
)

# Add prediction_id=None to get_lstm
exp_srv_content = re.sub(
    r"def get_lstm\(country=None, cities=None, diseases=None, date_from=None, date_to=None,\n                 search=None, sort_by=None, sort_dir=\"asc\", page=1, per_page=50\):",
    r"def get_lstm(country=None, cities=None, diseases=None, date_from=None, date_to=None,\n                 search=None, sort_by=None, sort_dir='asc', page=1, per_page=50, prediction_id=None):",
    exp_srv_content
)

# Add prediction_id=None to get_signals
exp_srv_content = re.sub(
    r"def get_signals\(cities=None, diseases=None, seasons=None, date_from=None, date_to=None,\n                    search=None, sort_by=None, sort_dir=\"asc\", page=1, per_page=50\):",
    r"def get_signals(cities=None, diseases=None, seasons=None, date_from=None, date_to=None,\n                    search=None, sort_by=None, sort_dir='asc', page=1, per_page=50, prediction_id=None):",
    exp_srv_content
)

# Add prediction_id=None to get_patients
exp_srv_content = re.sub(
    r"def get_patients\(cities=None, diseases=None, gender=None, season=None, is_outbreak=None,\n                     date_from=None, date_to=None, search=None, sort_by=None, sort_dir=\"asc\",\n                     page=1, per_page=50\):",
    r"def get_patients(cities=None, diseases=None, gender=None, season=None, is_outbreak=None,\n                     date_from=None, date_to=None, search=None, sort_by=None, sort_dir='asc',\n                     page=1, per_page=50, prediction_id=None):",
    exp_srv_content
)

with open(exp_srv_path, "w") as f:
    f.write(exp_srv_content)

print("Updates applied to helpers.py and explorer_service.py")
