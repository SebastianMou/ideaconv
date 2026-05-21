import json

with open('syscap_export.json', 'r') as f:
    data = json.load(f)

for inv in data['investors']:
    if 'Carlos Ricardo' in inv.get('full_name', ''):
        print(f"Name: {inv.get('full_name')}")
        print(f"Email: {inv.get('email')}")
        print(f"Has addresses: {len(inv.get('addresses', []))}")
        print(f"Has contacts: {len(inv.get('contacts', []))}")
        print(f"Has bank_accounts: {len(inv.get('bank_accounts', []))}")
        print(f"Has fiscal_addresses: {len(inv.get('fiscal_addresses', []))}")
        
        if inv.get('contacts'):
            print(f"\nContact data: {inv['contacts'][0]}")
        if inv.get('fiscal_addresses'):
            print(f"\nFiscal data: {inv['fiscal_addresses'][0]}")
        break