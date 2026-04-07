#!/bin/bash
# Hourly error check — saves report + alerts if errors found
REPORT="/opt/neura-v2/logs/error-report-$(date +%Y-%m-%d_%H).md"
mkdir -p /opt/neura-v2/logs/

python3 /opt/neura-v2/scripts/error-monitor.py --since "1 hour ago" --output "$REPORT"

# Count errors
ERRORS=$(grep -c "^- Errors:" "$REPORT" 2>/dev/null | head -1)
ERROR_COUNT=$(grep "^- Errors:" "$REPORT" 2>/dev/null | grep -oP '\d+')

if [ "$ERROR_COUNT" -gt "0" ] 2>/dev/null; then
    # Alert to HQ
    python3 ${NEURA_BASE:-/opt/neura-v2}/scripts/tg-send.py hq "⚠️ Neura v2 Error Report (last hour): $ERROR_COUNT errors. See $REPORT" 2>/dev/null
fi
