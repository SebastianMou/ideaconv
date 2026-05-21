# Create check_raw.py in VS Code:
import json

with open('syscap_export.json', 'r') as f:
    data = json.load(f)

for inv in data['investors']:
    if 'Carlos Ricardo' in inv.get('full_name', ''):
        print(json.dumps(inv, indent=2))
        break