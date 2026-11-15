
import csv
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

from winotify import Notification

BASE_DIR = Path(__file__).resolve().parent
STATE_FILE = BASE_DIR / "notification_state.json"


def read_csv(filename):
    path = BASE_DIR / filename

    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def send_notification(title, message):
    toast = Notification(
        app_id="Endpoint Compliance Monitor",
        title=title,
        msg=message,
        duration="long"
    )
    toast.show()


def run_monitoring():
    print("Starting daily endpoint monitoring...")

    result = subprocess.run(
        [sys.executable, str(BASE_DIR / "run_all.py")],
        cwd=str(BASE_DIR)
    )

    if result.returncode != 0:
        send_notification(
            "Endpoint Monitoring Alert",
            "Monitoring scan failed. Please check the project reports."
        )
        return False

    apps = read_csv("application_compliance.csv")
    pending = read_csv("pending_windows_updates.csv")
    drivers = read_csv("driver_health.csv")

    outdated = [
        app for app in apps
        if app.get("Status", "").strip().lower() == "outdated"
    ]

    pending_count = len(pending)
    driver_errors = len(drivers)

    with open(BASE_DIR / "scan_summary.json", "r", encoding="utf-8") as file:
        summary = json.load(file)

    failed_modules = summary.get("failed_modules", [])

    issues = []

    if outdated:
        names = ", ".join(
            app.get("Application", "Unknown")
            for app in outdated[:3]
        )
        issues.append(f"Outdated apps: {names}")

    if pending_count:
        issues.append(f"Pending Windows updates: {pending_count}")

    if driver_errors:
        issues.append(f"Driver errors: {driver_errors}")

    if failed_modules:
        issues.append(f"Failed modules: {len(failed_modules)}")

    if issues:
        message = " | ".join(issues)
        send_notification("Endpoint Compliance Alert", message)
    else:
        send_notification(
            "Endpoint Compliance Report",
            "All monitoring checks completed. No detected issues."
        )

    return True


def main():
    today = datetime.now().astimezone().date().isoformat()

    if "--test" in sys.argv:
        send_notification(
            "Endpoint Monitor Test",
            "Windows desktop notifications are working!"
        )
        print("Test notification sent.")
        return

    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if state.get("notification_date") == today:
                print("Today's notification already sent. Skipping.")
                return
        except (json.JSONDecodeError, OSError):
            pass

    success = run_monitoring()

    if success:
        STATE_FILE.write_text(
            json.dumps({"notification_date": today}, indent=4),
            encoding="utf-8"
        )


if __name__ == "__main__":
    main()
