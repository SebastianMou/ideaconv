import json

with open('syscap_export.json', 'r') as f:
    data = json.load(f)

for inv in data['investors']:
    if 'Eugenio Rico' in inv.get('full_name', ''):
        print(f"Name: {inv.get('full_name')}")
        print(f"Email from main: {inv.get('email')}")
        print(f"Contacts array: {inv.get('contacts')}")
        print(f"Has contacts: {len(inv.get('contacts', []))}")
        
        # Show the full investor object
        print("\n--- Full investor data ---")
        import json
        print(json.dumps(inv, indent=2))
        break