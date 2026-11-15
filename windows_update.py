
import subprocess
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


def collect_update_history():
    print("\nCollecting Windows Update history...")

    command = r"""
    $session = New-Object -ComObject Microsoft.Update.Session
    $searcher = $session.CreateUpdateSearcher()
    $count = $searcher.GetTotalHistoryCount()
    $history = $searcher.QueryHistory(0, $count)

    $report = foreach ($item in $history) {
        $kb = [regex]::Match($item.Title, 'KB\d+').Value

        $status = switch ($item.ResultCode) {
            2 { "Succeeded" }
            3 { "Succeeded With Errors" }
            4 { "Failed" }
            5 { "Aborted" }
            default { "Unknown" }
        }

        $type = if ($item.Title -match "Defender") {
            "Defender Update"
        }
        elseif ($item.Title -match "Security") {
            "Security Update"
        }
        elseif ($item.Title -match "Preview") {
            "Preview Update"
        }
        else {
            "Other Update"
        }

        [PSCustomObject]@{
            Title = $item.Title
            KBNumber = $kb
            InstalledOn = $item.Date
            UpdateType = $type
            Status = $status
        }
    }

    $report | ConvertTo-Json -Depth 3 -Compress
    """

    output = run_powershell(command)

    data = __import__("json").loads(output) if output.strip() else []
    if isinstance(data, dict):
        data = [data]

    path = os.path.join(BASE_DIR, "windows_update_history.csv")

    fields = ["Title", "KBNumber", "InstalledOn", "UpdateType", "Status"]

    with open(path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)

    print("Update history records:", len(data))
    print("Saved:", path)


def collect_pending_updates():
    print("\nScanning for pending Windows Updates...")

    command = r"""
    $session = New-Object -ComObject Microsoft.Update.Session
    $searcher = $session.CreateUpdateSearcher()
    $result = $searcher.Search("IsInstalled=0 and IsHidden=0 and Type='Software'")

    $updates = foreach ($item in $result.Updates) {
        $categories = @(
            foreach ($category in $item.Categories) {
                $category.Name
            }
        ) -join ", "

        [PSCustomObject]@{
            Title = $item.Title
            KBNumber = $item.KBArticleIDs -join ", "
            UpdateType = $categories
            SecuritySeverity = $item.MsrcSeverity
            IsDownloaded = $item.IsDownloaded
            Status = "Pending"
        }
    }

    [PSCustomObject]@{
        ScanResultCode = $result.ResultCode
        Updates = @($updates)
    } | ConvertTo-Json -Depth 4 -Compress
    """

    output = run_powershell(command)
    result = __import__("json").loads(output)

    updates = result.get("Updates", [])
    if isinstance(updates, dict):
        updates = [updates]

    path = os.path.join(BASE_DIR, "pending_windows_updates.csv")

    fields = [
        "Title", "KBNumber", "UpdateType",
        "SecuritySeverity", "IsDownloaded", "Status"
    ]

    with open(path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(updates)

    print("Scan Result Code:", result.get("ScanResultCode"))
    print("Pending Updates:", len(updates))
    print("Saved:", path)


if __name__ == "__main__":
    try:
        collect_update_history()
        collect_pending_updates()
        print("\nWindows Update monitoring completed successfully.")

    except Exception as error:
        print("\nWindows Update monitoring failed:", error)
