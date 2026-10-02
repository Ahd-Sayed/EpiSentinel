import os
import re

routes_dir = "app/routes"

def patch_file(filename):
    path = os.path.join(routes_dir, filename)
    with open(path, "r") as f:
        content = f.read()
    
    # Check if helpers import exists
    if "from app.utils.helpers import " not in content:
        content = "from app.utils.helpers import parse_prediction_id\n" + content
    elif "parse_prediction_id" not in content:
        content = content.replace("from app.utils.helpers import ", "from app.utils.helpers import parse_prediction_id, ")
    
    # Replace prediction_id = request.args.get("prediction_id") 
    # and prediction_id = args.get("prediction_id")
    # with parse_prediction_id(request.args.get("prediction_id"))
    content = re.sub(
        r"prediction_id = args\.get\([\"']prediction_id[\"']\)",
        r"prediction_id = parse_prediction_id(args.get('prediction_id'))",
        content
    )
    content = re.sub(
        r"prediction_id = request\.args\.get\([\"']prediction_id[\"']\)",
        r"prediction_id = parse_prediction_id(request.args.get('prediction_id'))",
        content
    )
    
    with open(path, "w") as f:
        f.write(content)
    print(f"Patched {filename}")

for f in ["explorer.py", "alerts.py", "models.py", "scenarios.py", "overview.py"]:
    patch_file(f)

print("All routes patched.")
