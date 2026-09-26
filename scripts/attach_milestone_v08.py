import json
import os
import subprocess
import time
import urllib.error
import urllib.request


def get_token():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        res = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            token = res.stdout.strip()
    return token


def main():
    token = get_token()
    if not token:
        print("No token")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Midgley-Bot",
        "Content-Type": "application/json",
    }

    v08_ms_id = None
    for i in range(1, 25):
        url = f"https://api.github.com/repos/KoshiirRa/midgley/milestones/{i}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                title = data.get("title", "")
                print(f"Milestone #{i}: '{title}' ({data.get('state')})")
                if "0.8" in title:
                    v08_ms_id = i
        except Exception:
            pass

    print(f"Target milestone v0.8 ID: {v08_ms_id}")
    if not v08_ms_id:
        return

    for num in range(443, 454):
        issue_url = f"https://api.github.com/repos/KoshiirRa/midgley/issues/{num}"
        patch_data = json.dumps({"milestone": v08_ms_id}).encode("utf-8")
        req = urllib.request.Request(issue_url, data=patch_data, headers=headers, method="PATCH")
        try:
            with urllib.request.urlopen(req) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                ms_title = res.get("milestone", {}).get("title") if res.get("milestone") else None
                print(f"Updated Issue #{num} with milestone: {ms_title}")
        except Exception as e:
            print(f"Failed to update Issue #{num}: {e}")
        time.sleep(0.3)


if __name__ == "__main__":
    main()
