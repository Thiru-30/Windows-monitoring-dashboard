
import subprocess
import sys
import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SUMMARY_FILE = os.path.join(BASE_DIR, "scan_summary.json")

SCRIPTS = [
    "inventory.py",
    "version_check.py",
    "windows_update.py",
    "driver_monitor.py"
]

start_time = datetime.now()

successful = []
failed = []

print("=" * 55, flush=True)
print(" WINDOWS COMPLIANCE MONITORING SYSTEM", flush=True)
print("=" * 55, flush=True)

for script in SCRIPTS:
    script_path = os.path.join(BASE_DIR, script)

    print(f"\nRunning: {script}", flush=True)
    print("-" * 55, flush=True)

    if not os.path.exists(script_path):
        print(f"ERROR: {script} not found.", flush=True)
        failed.append(script)
        continue

    result = subprocess.run(
        [sys.executable, script_path],
        cwd=BASE_DIR
    )

    if result.returncode == 0:
        print(f"\nSUCCESS: {script}", flush=True)
        successful.append(script)
    else:
        print(f"\nFAILED: {script}", flush=True)
        failed.append(script)

end_time = datetime.now()
duration = round((end_time - start_time).total_seconds(), 2)

overall_status = "Success" if not failed else "Failed"

summary = {
    "scan_started": start_time.strftime("%d-%m-%Y %H:%M:%S"),
    "last_scan": end_time.strftime("%d-%m-%Y %H:%M:%S"),
    "duration_seconds": duration,
    "total_scripts": len(SCRIPTS),
    "successful_scripts": len(successful),
    "failed_scripts": len(failed),
    "successful_modules": successful,
    "failed_modules": failed,
    "overall_status": overall_status
}

with open(SUMMARY_FILE, "w", encoding="utf-8") as file:
    json.dump(summary, file, indent=4)

print("\n" + "=" * 55, flush=True)
print(" MONITORING SUMMARY", flush=True)
print("=" * 55, flush=True)

print("Successful scripts:", len(successful), flush=True)
print("Failed scripts:", len(failed), flush=True)
print("Execution time:", duration, "seconds", flush=True)
print("Last scan:", summary["last_scan"], flush=True)
print("Overall status:", overall_status, flush=True)

if failed:
    print("\nFailed modules:", flush=True)
    for script in failed:
        print("-", script, flush=True)
else:
    print("\nAll monitoring reports generated successfully!", flush=True)

print("\nScan summary saved:", SUMMARY_FILE, flush=True)
print("Dashboard: http://127.0.0.1:5000", flush=True)
print("=" * 55, flush=True)
