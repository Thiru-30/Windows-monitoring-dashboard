
import csv
import os
import re
import requests
from bs4 import BeautifulSoup

# ==========================================
# FILE PATHS
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_FILE = os.path.join(BASE_DIR, "installed_applications.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "application_compliance.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0 WindowsComplianceProject/1.0"
}

# ==========================================
# FOUR APPLICATIONS
# ==========================================

MONITORED_APPS = [
    "Google Chrome",
    "Microsoft Edge",
    "Proton VPN",
    "WinRAR"
]


# ==========================================
# COMMON FUNCTIONS
# ==========================================

def get_page(url):

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20
    )

    response.raise_for_status()
    return response.text


def normalize_name(name):

    name = (name or "").lower().strip()
    name = re.sub(r"\s+", " ", name)

    return re.sub(r"[^a-z0-9]", "", name)


def version_key(version):

    return tuple(
        int(n) for n in re.findall(r"\d+", version or "")
    )


def compare_versions(installed, latest):

    old = version_key(installed)
    new = version_key(latest)

    if not old or not new:
        return "Version Unknown"

    length = max(len(old), len(new))

    old += (0,) * (length - len(old))
    new += (0,) * (length - len(new))

    return "Up to Date" if old >= new else "Outdated"


def find_installed_app(monitored_name, installed_apps):

    target = normalize_name(monitored_name)

    matches = [
        app for app in installed_apps
        if (
            normalize_name(app["Application"]) == target
            or normalize_name(app["Application"]).startswith(target)
        )
    ]

    if not matches:
        return None

    matches.sort(
        key=lambda app: (
            normalize_name(app["Application"]) != target,
            len(normalize_name(app["Application"])),
            tuple(-n for n in version_key(app["Version"]))
        )
    )

    return matches[0]


# ==========================================
# 1. GOOGLE CHROME
# ==========================================

def get_chrome_version():

    url = (
        "https://versionhistory.googleapis.com/v1/"
        "chrome/platforms/win/channels/stable/versions"
        "?order_by=version%20desc&pageSize=1"
    )

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20
    )

    response.raise_for_status()

    versions = response.json().get("versions", [])

    return versions[0].get("version") if versions else None


# ==========================================
# 2. MICROSOFT EDGE
# ==========================================

def get_edge_version():

    url = (
        "https://edgeupdates.microsoft.com/"
        "api/products?view=enterprise"
    )

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20
    )

    response.raise_for_status()

    products = response.json()
    versions = []

    for product in products:

        if product.get("Product", "").lower() != "stable":
            continue

        for release in product.get("Releases", []):

            if release.get("Platform", "").lower() != "windows":
                continue

            architecture = release.get(
                "Architecture", ""
            ).lower()

            if architecture and architecture != "x64":
                continue

            version = release.get("ProductVersion")

            if version:
                versions.append(version)

    return max(versions, key=version_key) if versions else None


# ==========================================
# 3. PROTON VPN
# ==========================================

def get_proton_version():

    url = "https://protonvpn.com/support/release-notes-windows"

    soup = BeautifulSoup(
        get_page(url),
        "html.parser"
    )

    text = soup.get_text(" ", strip=True)

    match = re.search(
        r"Latest stable release.{0,200}?Version\s*"
        r"([0-9]+(?:\.[0-9]+)+)",
        text,
        re.IGNORECASE
    )

    return match.group(1) if match else None


# ==========================================
# 4. WINRAR
# ==========================================

def get_winrar_version():

    url = "https://www.rarlab.com/download.htm"

    soup = BeautifulSoup(
        get_page(url),
        "html.parser"
    )

    text = soup.get_text(" ", strip=True)

    section = re.search(
        r"English WinRAR and RAR release(.*?)(?:Localized WinRAR versions)",
        text,
        re.IGNORECASE
    )

    if not section:
        return None

    match = re.search(
        r"WinRAR\s+64-bit\s+(\d+(?:\.\d+)+)",
        section.group(1),
        re.IGNORECASE
    )

    return match.group(1) if match else None


# ==========================================
# VERSION CHECK CONFIGURATION
# ==========================================

VERSION_CHECKS = {
    "Google Chrome": get_chrome_version,
    "Microsoft Edge": get_edge_version,
    "Proton VPN": get_proton_version,
    "WinRAR": get_winrar_version
}


# ==========================================
# MAIN COMPLIANCE CHECK
# ==========================================

def check_applications():

    if not os.path.exists(INPUT_FILE):

        print("ERROR: Inventory CSV not found.")
        return

    with open(
        INPUT_FILE,
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        rows = list(csv.DictReader(file))

    if not rows:

        print("ERROR: Inventory CSV is empty.")
        return

    columns = rows[0].keys()

    app_column = next(
        (c for c in columns
         if c.lower() in ["application", "name", "displayname"]),
        None
    )

    version_column = next(
        (c for c in columns
         if c.lower() in ["version", "installedversion", "displayversion"]),
        None
    )

    publisher_column = next(
        (c for c in columns
         if c.lower() in ["publisher", "manufacturer"]),
        None
    )

    if not app_column or not version_column:

        print("ERROR: Required CSV columns are missing.")
        return

    installed_apps = []

    for row in rows:

        installed_apps.append({

            "Application": row.get(
                app_column, ""
            ).strip(),

            "Version": row.get(
                version_column, ""
            ).strip(),

            "Publisher": (
                row.get(publisher_column, "").strip()
                if publisher_column else ""
            )
        })

    results = []

    print("\nStarting 4-application compliance check...\n")

    for app_name in MONITORED_APPS:

        matched = find_installed_app(
            app_name,
            installed_apps
        )

        if not matched:

            result = {
                "Application": app_name,
                "Installed": "No",
                "InstalledVersion": "",
                "Publisher": "",
                "LatestVersion": "",
                "Status": "Not Installed"
            }

        else:

            installed_version = matched["Version"]
            latest_version = ""
            status = "Version Unknown"

            try:

                latest_version = (
                    VERSION_CHECKS[app_name]() or ""
                )

                if latest_version and installed_version:

                    status = compare_versions(
                        installed_version,
                        latest_version
                    )

                if not latest_version:

                    print(
                        "WARNING: Latest version not detected for",
                        app_name
                    )

            except Exception as error:

                print(
                    f"ERROR checking {app_name}: {error}"
                )

            result = {
                "Application": app_name,
                "Installed": "Yes",
                "InstalledVersion": installed_version,
                "Publisher": matched["Publisher"],
                "LatestVersion": latest_version,
                "Status": status
            }

        results.append(result)

        print(
            f"{app_name}: {result['Status']}"
        )

    # ======================================
    # SAVE REPORT
    # ======================================

    fieldnames = [
        "Application",
        "Installed",
        "InstalledVersion",
        "Publisher",
        "LatestVersion",
        "Status"
    ]

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(results)

    # ======================================
    # SUMMARY
    # ======================================

    total = len(results)

    up_to_date = sum(
        r["Status"] == "Up to Date" for r in results
    )

    outdated = sum(
        r["Status"] == "Outdated" for r in results
    )

    unknown = sum(
        r["Status"] == "Version Unknown" for r in results
    )

    not_installed = sum(
        r["Status"] == "Not Installed" for r in results
    )

    print("\n----------------------------------")
    print("APPLICATION COMPLIANCE SUMMARY")
    print("----------------------------------")

    print("Total monitored applications:", total)
    print("Up to Date:", up_to_date)
    print("Outdated:", outdated)
    print("Version Unknown:", unknown)
    print("Not Installed:", not_installed)

    print("----------------------------------")
    print("Report saved:", OUTPUT_FILE)


if __name__ == "__main__":
    check_applications()
