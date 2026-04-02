#!/bin/bash
# lighthouse-audit.sh — Run Lighthouse against a URL, output JSON scores
# Usage: bash lighthouse-audit.sh https://example.com

URL="$1"
if [ -z "$URL" ]; then
    echo '{"error": "No URL provided"}' >&2
    exit 1
fi

export CHROME_PATH=/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome
OUTFILE="/tmp/lighthouse-audit-$(date +%s).json"

timeout 90 lighthouse "$URL" \
    --output=json \
    --output-path="$OUTFILE" \
    --chrome-flags="--headless --no-sandbox --disable-gpu --disable-dev-shm-usage" \
    --max-wait-for-load=30000 \
    --only-categories=performance,accessibility,best-practices,seo \
    --quiet 2>/dev/null

if [ $? -ne 0 ]; then
    echo '{"error": "Lighthouse failed or timed out"}' >&2
    exit 1
fi

node -e "
const r = require('$OUTFILE');
const s = r.categories;
const a = r.audits;
console.log(JSON.stringify({
    performance: Math.round(s.performance.score * 100),
    accessibility: Math.round(s.accessibility.score * 100),
    best_practices: Math.round(s['best-practices'].score * 100),
    seo: Math.round(s.seo.score * 100),
    lcp_ms: Math.round(a['largest-contentful-paint']?.numericValue || 0),
    cls: parseFloat((a['cumulative-layout-shift']?.numericValue || 0).toFixed(3)),
    fcp_ms: Math.round(a['first-contentful-paint']?.numericValue || 0),
    tbt_ms: Math.round(a['total-blocking-time']?.numericValue || 0),
    total_weight_kb: Math.round((a['total-byte-weight']?.numericValue || 0) / 1024),
    report_path: '$OUTFILE'
}, null, 2));
"
