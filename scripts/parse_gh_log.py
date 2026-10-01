import re
import sys
from datetime import datetime

log_file = sys.argv[1] if len(sys.argv) > 1 else "/tmp/run_36878549928.log"

with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

prev_dt = None
first_dt = None
last_dt = None

for line in lines:
    m = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(\d+)Z", line)
    if not m:
        continue
    dt_str = m.group(1)
    dt = datetime.fromisoformat(dt_str)
    if first_dt is None:
        first_dt = dt
    last_dt = dt

    if (
        "##[group]Run " in line
        or "STEP " in line
        or "EXECUTION COMPLETE" in line
        or "Running pytest" in line
        or "Starting " in line
        or "Finished " in line
        or "Job duration" in line
    ):
        delta = (dt - prev_dt).total_seconds() if prev_dt else 0
        prev_dt = dt
        print(f"[{dt_str}] (+{delta:6.1f}s) {line.strip()[:120]}")

if first_dt and last_dt:
    dur_min = (last_dt - first_dt).total_seconds() / 60.0
    print(f"\nTotal Run Duration: {dur_min:.2f} minutes")
