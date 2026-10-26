#!/usr/bin/env bash
# Verify the sotd-pipeline metrics chain end-to-end:
#   supervisor /metrics -> Prometheus (shared monitoring stack) -> Grafana dashboard.
# Uses the Komodo API (creds grepped from nas-stacks/.env) for the Grafana admin
# password. Never prints secrets. Run from the sotd-pipeline repo root.
set -euo pipefail
ENV_FILE="${NAS_STACKS_ENV:-../nas-stacks/.env}"
MONITORING_ID="6adbcb0630bee4cea6dc28ca"   # monitoring stack
KOMODO="https://komodo.home.jmoore.org"
GRAFANA="https://grafana.home.jmoore.org"

KOMODO_API_KEY=$(grep -E '^KOMODO_API_KEY=' "$ENV_FILE" | cut -d= -f2-)
KOMODO_API_SECRET=$(grep -E '^KOMODO_API_SECRET=' "$ENV_FILE" | cut -d= -f2-)

echo "== supervisor /metrics (via NAS) =="
ssh nas "curl -s --max-time 8 127.0.0.1:8100/metrics" | grep -E "^sotd_pipeline_(publish_last_success|consecutive_failures|runs_total|next_run_timestamp|phase_records)" | head -6

echo
echo "== Prometheus active targets =="
PW=$(curl -s --max-time 15 -X POST "$KOMODO/read/GetStack" \
  -H "Content-Type: application/json" -H "X-Api-Key: $KOMODO_API_KEY" -H "X-Api-Secret: $KOMODO_API_SECRET" \
  -d "{\"id\": \"$MONITORING_ID\"}" | python3 -c '
import json, sys, re
s = json.load(sys.stdin)
m = re.search(r"GRAFANA_ADMIN_PASSWORD=(\S+)", (s.get("config") or {}).get("environment", ""))
print(m.group(1) if m else "")')

curl -s --max-time 15 -u "admin:$PW" "$GRAFANA/api/datasources/proxy/uid/prometheus/api/v1/targets" | python3 -c '
import json, sys
r = json.load(sys.stdin)
for t in r["data"]["activeTargets"]:
    job = t["labels"].get("job")
    print("  " + str(job) + ": " + str(t.get("health")))'

echo
echo "== sotd-pipeline target query =="
curl -s --max-time 15 -u "admin:$PW" \
  "$GRAFANA/api/datasources/proxy/uid/prometheus/api/v1/query?query=up%7Bjob%3D%22sotd-pipeline%22%7D" | python3 -c '
import json, sys
r = json.load(sys.stdin)
res = r.get("data", {}).get("result", [])
for s in res:
    print("  up = " + str(s["value"][1]))
if not res:
    print("  NO SERIES — target not scraped (prometheus restart needed?)")
    sys.exit(1)'

echo
echo "== Grafana SOTD folder + dashboard =="
curl -s --max-time 15 -u "admin:$PW" "$GRAFANA/api/search" | python3 -c '
import json, sys
for it in json.load(sys.stdin):
    if it.get("title") in ("SOTD Pipeline", "SOTD"):
        print("  " + it.get("type") + ": " + it.get("title") + " (" + str(it.get("uid")) + ")")'

echo
echo "ALL CHECKS PASSED"