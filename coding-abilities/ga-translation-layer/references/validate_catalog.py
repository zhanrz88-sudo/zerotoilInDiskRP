"""Quick validation script for ga-catalog.json."""
import json
from collections import Counter
from pathlib import Path

catalog_path = Path(__file__).parent.parent / "ga-catalog.json"
d = json.load(open(catalog_path))

ops = d["operations"]
print(f"Total operations: {len(ops)}")

# By group
groups = Counter(o["operation_group"] for o in ops)
print("\nBy operation group:")
for g, c in sorted(groups.items(), key=lambda x: -x[1]):
    print(f"  {g}: {c}")

# By environment
envs = Counter(o["environment"] for o in ops)
print("\nBy environment:")
for e, c in sorted(envs.items(), key=lambda x: -x[1]):
    print(f"  {e}: {c}")

# Deprecated
dep = [o for o in ops if o.get("deprecated")]
print(f"\nDeprecated: {len(dep)}")
for o in dep:
    print(f"  {o['id']} -> {o.get('deprecated_use_instead', '?')}")

# Mutating vs read-only
mut = sum(1 for o in ops if o["mutating"])
ro = sum(1 for o in ops if o["read_only"])
print(f"\nMutating: {mut}, Read-only: {ro}")

# Required fields check
required = ["id", "name", "operation_group", "extension", "environment",
            "mutating", "read_only", "parameters", "replaces", "core_action"]
missing = []
for o in ops:
    for f in required:
        if f not in o:
            missing.append(f"{o.get('id', '?')} missing {f}")
if missing:
    print(f"\nMISSING FIELDS: {missing}")
else:
    print("\nAll required fields present: OK")

# Duplicate IDs
ids = [o["id"] for o in ops]
dups = set(i for i in ids if ids.count(i) > 1)
if dups:
    print(f"\nDUPLICATE IDs: {dups}")
else:
    print(f"No duplicate IDs: OK")

# Total keyword mappings
total_kw = sum(len(o["replaces"]) for o in ops)
print(f"Total keyword mappings: {total_kw}")

# Verify all params have name and type
bad_params = []
for o in ops:
    for p in o["parameters"]:
        if "name" not in p or "type" not in p:
            bad_params.append(f"{o['id']}: param missing name/type")
if bad_params:
    print(f"\nBAD PARAMS: {bad_params}")
else:
    print(f"All parameters have name+type: OK")

print("\n=== VALIDATION PASSED ===")
