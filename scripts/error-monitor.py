#!/usr/bin/env python3
"""Neura v2 Error Monitor — парсит journalctl и собирает ошибки по капсулам.
Run: python3 scripts/error-monitor.py [--since "1 hour ago"] [--output /path/to/report.md]
"""
import subprocess, re, sys, json
from datetime import datetime
from collections import defaultdict

since = "1 hour ago"
output = None
for i, arg in enumerate(sys.argv[1:], 1):
    if arg == "--since" and i < len(sys.argv) - 1:
        since = sys.argv[i + 1]
    elif arg == "--output" and i < len(sys.argv) - 1:
        output = sys.argv[i + 1]

# Get logs
result = subprocess.run(
    ["journalctl", "-u", "neura-v2", "--no-pager", f"--since={since}"],
    capture_output=True, text=True
)

lines = result.stdout.splitlines()
errors = defaultdict(list)
warnings = defaultdict(list)
requests = defaultdict(int)

for line in lines:
    # Count requests per capsule
    m = re.search(r'capsule=(\w+)', line)
    if m:
        requests[m.group(1)] += 1

    # Errors
    if "ERROR" in line or "error" in line.lower():
        # Try to extract capsule
        cap = "unknown"
        m = re.search(r'capsule[=:](\w+)', line)
        if m:
            cap = m.group(1)
        errors[cap].append(line.strip()[-200:])

    # Warnings
    if "WARNING" in line or "WARN" in line:
        cap = "unknown"
        m = re.search(r'capsule[=:](\w+)', line)
        if m:
            cap = m.group(1)
        warnings[cap].append(line.strip()[-200:])

# Build report
now = datetime.now().strftime("%Y-%m-%d %H:%M")
report = f"# Neura v2 Error Monitor — {now}\n"
report += f"> Period: since {since}\n\n"

total_err = sum(len(v) for v in errors.values())
total_warn = sum(len(v) for v in warnings.values())
total_req = sum(requests.values())

report += f"## Summary\n"
report += f"- Requests: {total_req}\n"
report += f"- Errors: {total_err}\n"
report += f"- Warnings: {total_warn}\n\n"

if errors:
    report += "## Errors by capsule\n"
    for cap, errs in sorted(errors.items()):
        report += f"\n### {cap} ({len(errs)} errors)\n"
        for e in errs[-5:]:  # Last 5
            report += f"```\n{e}\n```\n"

if not errors and not warnings:
    report += "## ✅ No errors or warnings found\n"

report += f"\n## Requests per capsule\n"
for cap, cnt in sorted(requests.items(), key=lambda x: -x[1]):
    report += f"- {cap}: {cnt}\n"

if output:
    with open(output, "w") as f:
        f.write(report)
    print(f"Report saved to {output}")
else:
    print(report)
