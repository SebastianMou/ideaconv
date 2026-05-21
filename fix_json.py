import json

with open("django_fixtures.json", "r") as f:
    data = json.load(f)

# Replace empty strings with None for unique fields
for record in data:
    if record.get("model") == "inversiones.inversionista":
        fields = record["fields"]
        if fields.get("rfc") == "":
            fields["rfc"] = None
        if fields.get("curp") == "":
            fields["curp"] = None

with open("django_fixtures.json", "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("✅ Fixed empty RFC/CURP to null")
