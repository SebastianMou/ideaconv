import json
from syscap_migration import SyscapMigration

# Load the already-fetched data
with open("syscap_export.json", "r") as f:
    raw_data = json.load(f)

# Create migration instance and load the data
migration = SyscapMigration()
migration.raw_data = raw_data

# Run just the transformations
print("="*60)
print("TRANSFORMING DATA")
print("="*60 + "\n")

migration.transform_promoters()
migration.transform_investors()
migration.transform_promissory_notes()
migration.transform_transactions()
migration.transform_prospects()
migration.transform_statements_and_payments()

# Save fixtures
with open("django_fixtures.json", "w", encoding="utf-8") as f:
    json.dump(migration.django_data, f, indent=2, ensure_ascii=False)

print("✅ Django fixtures saved!")
print(f"📊 Total records: {len(migration.django_data)}")
