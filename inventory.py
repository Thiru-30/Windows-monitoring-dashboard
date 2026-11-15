
import winreg
import csv
import os

# Windows registry locations containing installed applications
REGISTRY_PATHS = [
    (winreg.HKEY_LOCAL_MACHINE,
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE,
     r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER,
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
]


def get_installed_applications():
    applications = []

    for root, path in REGISTRY_PATHS:
        try:
            with winreg.OpenKey(root, path) as registry:
                total = winreg.QueryInfoKey(registry)[0]

                for i in range(total):
                    try:
                        subkey_name = winreg.EnumKey(registry, i)

                        with winreg.OpenKey(registry, subkey_name) as app:
                            def get_value(name):
                                try:
                                    return winreg.QueryValueEx(app, name)[0]
                                except OSError:
                                    return ""

                            name = get_value("DisplayName")

                            if not name:
                                continue

                            applications.append({
                                "Application": name,
                                "Version": get_value("DisplayVersion"),
                                "Publisher": get_value("Publisher"),
                                "InstallDate": get_value("InstallDate")
                            })

                    except OSError:
                        continue

        except OSError:
            continue

    # Remove duplicate application entries
    unique_apps = {}
    for app in applications:
        key = (app["Application"].lower(), app["Version"])
        unique_apps[key] = app

    return list(unique_apps.values())


if __name__ == "__main__":
    apps = get_installed_applications()

    output_file = "installed_applications.csv"

    with open(output_file, "w", newline="", encoding="utf-8-sig") as file:
        columns = ["Application", "Version", "Publisher", "InstallDate"]
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(apps)

    print("Application inventory completed!")
    print("Total applications found:", len(apps))
    print("Report saved to:", os.path.abspath(output_file))
