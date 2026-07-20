import json

# Load your baseline simulation log
with open("bluesim_log_baseline.json", "r") as f:
    log_data = json.load(f)

print(f"--- Validating Simulation Log ({len(log_data)} entries) ---")
passed_count = 0

for entry in log_data:
    reg_name = entry["register"]
    actual = entry["actual"]
    expected = entry["expected"]
    is_passing = entry["pass"]
    
    status = "✓ PASS" if is_passing else "✗ FAIL"
    print(f"[{status}] {reg_name}: actual={actual}, expected={expected}")
    
    if is_passing:
        passed_count += 1

print(f"\nResult: {passed_count}/{len(log_data)} checks passed successfully.")