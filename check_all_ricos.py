# check_all_ricos.py
import json

with open('syscap_export.json', 'r') as f:
    data = json.load(f)

print("Searching for 'Rico' in all investors:\n")
for inv in data['investors']:
    if 'Rico' in inv.get('full_name', ''):
        print(f"Found: {inv.get('full_name')}")
        print(f"  Email: {inv.get('email')}")
        print(f"  Contacts: {len(inv.get('contacts', []))} items")
        print()