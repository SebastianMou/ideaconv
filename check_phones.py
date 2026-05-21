# check_phones.py
import json

with open('syscap_export.json', 'r') as f:
    data = json.load(f)

print("Checking phone data across all investors:\n")

has_phone_main = 0
has_phone_contact = 0
total = len(data['investors'])

for inv in data['investors']:
    # Check main investor object
    if inv.get('phone') or inv.get('mobile_phone') or inv.get('mobile_number'):
        has_phone_main += 1
        print(f"✅ {inv.get('full_name')}")
        print(f"   Phone: {inv.get('phone')}")
        print(f"   Mobile: {inv.get('mobile_phone') or inv.get('mobile_number')}")
        print()
    
    # Check contacts array
    contacts = inv.get('contacts', [])
    for contact in contacts:
        if contact.get('phone') or contact.get('mobile_phone'):
            has_phone_contact += 1
            print(f"✅ {inv.get('full_name')} (from contacts)")
            print(f"   Contact: {contact}")
            print()
            break

print(f"\n📊 Summary:")
print(f"Total investors: {total}")
print(f"With phone in main object: {has_phone_main}")
print(f"With phone in contacts: {has_phone_contact}")
print(f"Missing phone data: {total - has_phone_main}")
