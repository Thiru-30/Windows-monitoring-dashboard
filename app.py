
from flask import Flask, render_template_string
import psutil
import platform
import socket
import os
import csv
import json
from datetime import datetime

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INVENTORY_FILE = os.path.join(BASE_DIR, "installed_applications.csv")
COMPLIANCE_FILE = os.path.join(BASE_DIR, "application_compliance.csv")
UPDATE_HISTORY_FILE = os.path.join(BASE_DIR, "windows_update_history.csv")
PENDING_UPDATE_FILE = os.path.join(BASE_DIR, "pending_windows_updates.csv")
DRIVER_INVENTORY_FILE = os.path.join(BASE_DIR, "driver_inventory.csv")
DRIVER_HEALTH_FILE = os.path.join(BASE_DIR, "driver_health.csv")
SUMMARY_FILE = os.path.join(BASE_DIR, "scan_summary.json")


def read_csv(file_path):
    records = []

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
            records = list(csv.DictReader(file))

    return records


def read_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except (json.JSONDecodeError, OSError):
            pass

    return {}


def get_system_info():
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")

    return {
        "hostname": socket.gethostname(),
        "os": platform.system() + " " + platform.release(),
        "processor": platform.processor() or "Not Available",
        "cpu": psutil.cpu_percent(interval=0.5),
        "ram": memory.percent,
        "ram_total": round(memory.total / (1024 ** 3), 2),
        "disk": disk.percent,
        "disk_total": round(disk.total / (1024 ** 3), 2),
        "boot_time": datetime.fromtimestamp(
            psutil.boot_time()
        ).strftime("%d-%m-%Y %H:%M:%S")
    }


def get_dashboard_data():
    inventory = read_csv(INVENTORY_FILE)
    applications = read_csv(COMPLIANCE_FILE)

    counts = {
        "total": len(applications),
        "up_to_date": 0,
        "outdated": 0,
        "not_installed": 0,
        "unknown": 0
    }

    for item in applications:
        status = item.get("Status", "").strip().lower()

        if status == "up to date":
            counts["up_to_date"] += 1
        elif status == "outdated":
            counts["outdated"] += 1
        elif status == "not installed":
            counts["not_installed"] += 1
        else:
            counts["unknown"] += 1

    app_percentage = (
        round(counts["up_to_date"] / counts["total"] * 100, 2)
        if counts["total"] else 0
    )

    update_history = read_csv(UPDATE_HISTORY_FILE)
    pending_updates = read_csv(PENDING_UPDATE_FILE)
    driver_inventory = read_csv(DRIVER_INVENTORY_FILE)
    driver_health = read_csv(DRIVER_HEALTH_FILE)
    scan_summary = read_json(SUMMARY_FILE)

    monitoring = {
        "update_history": len(update_history),
        "pending_updates": len(pending_updates),
        "drivers": len(driver_inventory),
        "driver_errors": len(driver_health),
        "app_percentage": app_percentage,
        "update_status": (
            "No pending updates found"
            if os.path.exists(PENDING_UPDATE_FILE)
            and len(pending_updates) == 0
            else "Pending updates detected"
        ),
        "driver_status": (
            "No device errors detected"
            if os.path.exists(DRIVER_HEALTH_FILE)
            and len(driver_health) == 0
            else "Device errors detected"
        )
    }

    return (
        len(inventory),
        applications,
        counts,
        update_history,
        pending_updates,
        driver_inventory,
        driver_health,
        monitoring,
        scan_summary
    )


HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Windows Compliance Monitoring Dashboard</title>
    <meta http-equiv="refresh" content="60">

    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f3f5f9;
            margin: 0;
            padding: 25px;
            color: #222;
        }

        h1, h2 {
            color: #17365d;
        }

        .subtitle {
            color: #666;
        }

        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }

        .card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 8px #00000012;
        }

        .card h3 {
            margin: 0 0 12px;
            color: #555;
            font-size: 15px;
        }

        .value {
            font-size: 28px;
            font-weight: bold;
            color: #17365d;
        }

        .click-card {
            width: 100%;
            border: none;
            text-align: left;
            cursor: pointer;
            font-family: inherit;
        }

        .click-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px #00000020;
        }

        .click-card:focus {
            outline: 2px solid #17365d;
        }

        .good { color: #16803c; }
        .bad { color: #d62828; }
        .warning { color: #b77900; }

        .section {
            background: white;
            padding: 20px;
            margin-top: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 8px #00000012;
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }

        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }

        th {
            background: #17365d;
            color: white;
        }

        .status { font-weight: bold; }

        .system-info p { margin: 10px 0; }

        #result-section { display: none; }

        .close-button {
            background: #17365d;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 9px 15px;
            cursor: pointer;
        }

        footer {
            margin-top: 25px;
            color: #777;
            font-size: 13px;
        }
    </style>
</head>

<body>

    <h1>Windows Compliance Monitoring Dashboard</h1>

    <p class="subtitle">
        Automated Windows Update and Application Compliance Monitoring System
    </p>

    <div class="section">
        <h2>Monitoring Summary</h2>

        <div class="cards">
            <div class="card">
                <h3>Application Compliance</h3>
                <div class="value">{{ monitoring.app_percentage }}%</div>
                <small>Based on monitored applications</small>
            </div>

            <div class="card">
                <h3>Windows Update Status</h3>
                <div class="value {% if monitoring.pending_updates == 0 %}good{% else %}warning{% endif %}">
                    {{ monitoring.pending_updates }}
                </div>
                <small>{{ monitoring.update_status }}</small>
            </div>

            <div class="card">
                <h3>Driver Health</h3>
                <div class="value {% if monitoring.driver_errors == 0 %}good{% else %}bad{% endif %}">
                    {{ monitoring.driver_errors }}
                </div>
                <small>{{ monitoring.driver_status }}</small>
            </div>

            <div class="card">
                <h3>Last Scan Status</h3>
                <div class="value {% if scan_summary.get('overall_status') == 'Success' %}good{% else %}warning{% endif %}">
                    {{ scan_summary.get('overall_status', 'Not Available') }}
                </div>
                <small>{{ scan_summary.get('last_scan', 'No scan recorded') }}</small>
            </div>
        </div>

        <p>
            <b>Successful modules:</b>
            {{ scan_summary.get('successful_scripts', 'N/A') }}
            &nbsp; | &nbsp;
            <b>Failed modules:</b>
            {{ scan_summary.get('failed_scripts', 'N/A') }}
            &nbsp; | &nbsp;
            <b>Execution time:</b>
            {{ scan_summary.get('duration_seconds', 'N/A') }} seconds
        </p>
    </div>

    <div class="section system-info">
        <h2>System Information</h2>
        <p><b>Computer Name:</b> {{ system.hostname }}</p>
        <p><b>Operating System:</b> {{ system.os }}</p>
        <p><b>Processor:</b> {{ system.processor }}</p>
        <p><b>Total RAM:</b> {{ system.ram_total }} GB</p>
        <p><b>Total Disk:</b> {{ system.disk_total }} GB</p>
        <p><b>Last Boot Time:</b> {{ system.boot_time }}</p>
    </div>

    <h2>System Health</h2>

    <div class="cards">
        <div class="card">
            <h3>CPU Usage</h3>
            <div class="value">{{ system.cpu }}%</div>
        </div>

        <div class="card">
            <h3>RAM Usage</h3>
            <div class="value">{{ system.ram }}%</div>
        </div>

        <div class="card">
            <h3>Disk Usage</h3>
            <div class="value">{{ system.disk }}%</div>
        </div>
    </div>

    <h2>Application Inventory</h2>

    <div class="cards">
        <div class="card">
            <h3>Total Installed Applications</h3>
            <div class="value">{{ inventory_count }}</div>
        </div>

        <div class="card">
            <h3>Monitored Applications</h3>
            <div class="value">{{ counts.total }}</div>
        </div>
    </div>

    <h2>Application Compliance</h2>

    <div class="cards">

        <button class="card click-card" onclick="showApplications('Up to Date')">
            <h3>Up to Date</h3>
            <div class="value good">{{ counts.up_to_date }}</div>
            <small>Click to view applications</small>
        </button>

        <button class="card click-card" onclick="showApplications('Outdated')">
            <h3>Outdated</h3>
            <div class="value bad">{{ counts.outdated }}</div>
            <small>Click to view applications</small>
        </button>

        <button class="card click-card" onclick="showApplications('Not Installed')">
            <h3>Not Installed</h3>
            <div class="value warning">{{ counts.not_installed }}</div>
            <small>Click to view applications</small>
        </button>

        <button class="card click-card" onclick="showApplications('Version Unknown')">
            <h3>Version Unknown</h3>
            <div class="value warning">{{ counts.unknown }}</div>
            <small>Click to view applications</small>
        </button>

    </div>

    <h2>Windows Update Monitoring</h2>

    <div class="cards">

        <button class="card click-card" onclick="showTable('Windows Update History')">
            <h3>Installed Update History</h3>
            <div class="value">{{ monitoring.update_history }}</div>
            <small>Click to view update history</small>
        </button>

        <button class="card click-card" onclick="showTable('Pending Windows Updates')">
            <h3>Pending Updates</h3>
            <div class="value {% if monitoring.pending_updates == 0 %}good{% else %}warning{% endif %}">
                {{ monitoring.pending_updates }}
            </div>
            <small>Click to view pending updates</small>
        </button>

    </div>

    <h2>Driver Monitoring</h2>

    <div class="cards">

        <button class="card click-card" onclick="showTable('Driver Inventory')">
            <h3>Installed Drivers</h3>
            <div class="value">{{ monitoring.drivers }}</div>
            <small>Click to view drivers</small>
        </button>

        <button class="card click-card" onclick="showTable('Driver Health')">
            <h3>Driver Errors</h3>
            <div class="value {% if monitoring.driver_errors == 0 %}good{% else %}bad{% endif %}">
                {{ monitoring.driver_errors }}
            </div>
            <small>Click to view device errors</small>
        </button>

    </div>

    <div class="section" id="result-section">
        <h2 id="result-title">Details</h2>

        <button class="close-button" onclick="closeResults()">
            Close Details
        </button>

        <div id="result-table-container"></div>

        <p id="no-results" style="display:none;">
            No records found.
        </p>
    </div>

    <footer>
        Dashboard refreshes every 60 seconds.
        Run python run_all.py to generate fresh reports.
    </footer>

    <script>
        const applications = {{ applications | tojson }};
        const updateHistory = {{ update_history | tojson }};
        const pendingUpdates = {{ pending_updates | tojson }};
        const driverInventory = {{ driver_inventory | tojson }};
        const driverHealth = {{ driver_health | tojson }};

        function displayTable(title, records, columns) {
            const section = document.getElementById("result-section");
            const heading = document.getElementById("result-title");
            const container = document.getElementById("result-table-container");
            const noResults = document.getElementById("no-results");

            heading.textContent = title;
            container.innerHTML = "";

            if (!records || records.length === 0) {
                noResults.style.display = "block";
                section.style.display = "block";
                section.scrollIntoView({ behavior: "smooth" });
                return;
            }

            noResults.style.display = "none";

            const table = document.createElement("table");
            const thead = document.createElement("thead");
            const headerRow = document.createElement("tr");

            columns.forEach(column => {
                const th = document.createElement("th");
                th.textContent = column.label;
                headerRow.appendChild(th);
            });

            thead.appendChild(headerRow);
            table.appendChild(thead);

            const tbody = document.createElement("tbody");

            records.forEach(record => {
                const row = document.createElement("tr");

                columns.forEach(column => {
                    const td = document.createElement("td");
                    td.textContent = record[column.key] || "N/A";
                    row.appendChild(td);
                });

                tbody.appendChild(row);
            });

            table.appendChild(tbody);
            container.appendChild(table);

            section.style.display = "block";
            section.scrollIntoView({ behavior: "smooth" });
        }

        function showApplications(selectedStatus) {
            const filtered = applications.filter(item =>
                (item.Status || "").trim().toLowerCase() ===
                selectedStatus.toLowerCase()
            );

            displayTable(selectedStatus + " Applications", filtered, [
                {key: "Application", label: "Application"},
                {key: "InstalledVersion", label: "Installed Version"},
                {key: "LatestVersion", label: "Latest Version"},
                {key: "Status", label: "Status"}
            ]);
        }

        function showTable(type) {
            const configs = {
                "Windows Update History": {
                    records: updateHistory,
                    columns: [
                        {key: "Title", label: "Update"},
                        {key: "KBNumber", label: "KB Number"},
                        {key: "InstalledOn", label: "Installed On"},
                        {key: "UpdateType", label: "Update Type"},
                        {key: "Status", label: "Status"}
                    ]
                },

                "Pending Windows Updates": {
                    records: pendingUpdates,
                    columns: [
                        {key: "Title", label: "Update"},
                        {key: "KBNumber", label: "KB Number"},
                        {key: "UpdateType", label: "Update Type"},
                        {key: "SecuritySeverity", label: "Security Severity"},
                        {key: "IsDownloaded", label: "Downloaded"},
                        {key: "Status", label: "Status"}
                    ]
                },

                "Driver Inventory": {
                    records: driverInventory,
                    columns: [
                        {key: "DeviceName", label: "Device"},
                        {key: "DriverProviderName", label: "Provider"},
                        {key: "DriverVersion", label: "Version"},
                        {key: "DriverDate", label: "Driver Date"},
                        {key: "InfName", label: "INF Name"}
                    ]
                },

                "Driver Health": {
                    records: driverHealth,
                    columns: [
                        {key: "Name", label: "Device"},
                        {key: "PNPClass", label: "Device Class"},
                        {key: "ConfigManagerErrorCode", label: "Error Code"},
                        {key: "Status", label: "Status"}
                    ]
                }
            };

            const config = configs[type];
            displayTable(type, config.records, config.columns);
        }

        function closeResults() {
            document.getElementById("result-section").style.display = "none";
        }
    </script>

</body>
</html>
"""


@app.route("/")
def dashboard():
    system = get_system_info()

    (
        inventory_count,
        applications,
        counts,
        update_history,
        pending_updates,
        driver_inventory,
        driver_health,
        monitoring,
        scan_summary
    ) = get_dashboard_data()

    return render_template_string(
        HTML,
        system=system,
        inventory_count=inventory_count,
        applications=applications,
        counts=counts,
        update_history=update_history,
        pending_updates=pending_updates,
        driver_inventory=driver_inventory,
        driver_health=driver_health,
        monitoring=monitoring,
        scan_summary=scan_summary
    )


if __name__ == "__main__":
    app.run(debug=True)
