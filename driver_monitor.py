
import subprocess
import json
import csv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_powershell(command):
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-Command", command
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "PowerShell command failed")

    return result.stdout


def save_csv(filename, records, fields):
    path = os.path.join(BASE_DIR, filename)

    with open(path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    print("Saved:", path)


def collect_driver_inventory():
    print("\nCollecting installed driver inventory...")

    command = r"""
    $drivers = @(Get-CimInstance Win32_PnPSignedDriver |
        Select-Object DeviceName, DriverProviderName,
                      DriverVersion, DriverDate, InfName)

    [PSCustomObject]@{
        Drivers = $drivers
    } | ConvertTo-Json -Depth 4 -Compress
    """

    output = run_powershell(command)
    result = json.loads(output)
    drivers = result.get("Drivers") or []

    if isinstance(drivers, dict):
        drivers = [drivers]

    fields = [
        "DeviceName",
        "DriverProviderName",
        "DriverVersion",
        "DriverDate",
        "InfName"
    ]

    save_csv("driver_inventory.csv", drivers, fields)
    print("Total drivers collected:", len(drivers))


def check_driver_health():
    print("\nChecking device driver health...")

    command = r"""
    $problems = @(Get-CimInstance Win32_PnPEntity |
        Where-Object { $_.ConfigManagerErrorCode -ne 0 } |
        Select-Object Name, PNPClass,
                      ConfigManagerErrorCode, Status)

    [PSCustomObject]@{
        Problems = $problems
    } | ConvertTo-Json -Depth 4 -Compress
    """

    output = run_powershell(command)
    result = json.loads(output)
    problems = result.get("Problems") or []

    if isinstance(problems, dict):
        problems = [problems]

    fields = [
        "Name",
        "PNPClass",
        "ConfigManagerErrorCode",
        "Status"
    ]

    save_csv("driver_health.csv", problems, fields)

    print("Devices with driver errors:", len(problems))

    if problems:
        for device in problems:
            print(
                device.get("Name"),
                "| Error:",
                device.get("ConfigManagerErrorCode")
            )
    else:
        print("No device driver errors detected.")


if __name__ == "__main__":
    try:
        collect_driver_inventory()
        check_driver_health()

        print("\nDriver monitoring completed successfully.")

    except Exception as error:
        print("\nDriver monitoring failed:", error)
