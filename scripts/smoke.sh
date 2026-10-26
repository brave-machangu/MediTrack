#!/usr/bin/env bash
# End-to-end smoke test against a running stack (MT-030, OPS-01, AC-30).
#
#   ./scripts/smoke.sh [--wait-only] [BASE_URL]        BASE_URL defaults to http://localhost:8080
#
# 1. Waits up to SMOKE_TIMEOUT seconds (default 120) for GET /readyz to return 200.
#    With --wait-only it stops here (`make up` uses this).
# 2. If SMOKE_EXPECT_PATIENT is set, checks that this patient from an earlier run still exists
#    (AC-30: data survives a backend restart).
# 3. Creates a synthetic patient, medication and schedule, finds the dose in today's day view,
#    records it as taken, and checks that the day view then shows it as taken.
#
# The last line of output is `patient_id=<uuid>`. Synthetic data only. Needs bash, curl and python3.
# Python output goes through `tr -d '\r'` so the script also works in Git Bash on Windows.
set -euo pipefail

wait_only=false
if [[ "${1:-}" == "--wait-only" ]]; then
  wait_only=true
  shift
fi
base="${1:-http://localhost:8080}"
base="${base%/}"
timeout="${SMOKE_TIMEOUT:-120}"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

# request METHOD PATH EXPECTED_STATUS [JSON_BODY]: prints the response body, fails on any other status.
request() {
  local method=$1 path=$2 expected=$3 body=${4:-} out status
  out=$(mktemp)
  local args=(-sS -o "$out" -w '%{http_code}' -X "$method")
  if [[ -n "$body" ]]; then
    args+=(-H 'Content-Type: application/json' --data "$body")
  fi
  status=$(curl "${args[@]}" "$base$path") || status="000"
  if [[ "$status" != "$expected" ]]; then
    echo "FAIL: $method $path returned $status, expected $expected" >&2
    cat "$out" >&2
    echo >&2
    rm -f "$out"
    exit 1
  fi
  cat "$out"
  rm -f "$out"
}

# field PATH: prints one value from the JSON on stdin, e.g. `field id` or `field doses.0.status`.
field() {
  python3 -c '
import json, sys
value = json.load(sys.stdin)
for key in sys.argv[1].split("."):
    value = value[int(key)] if isinstance(value, list) else value[key]
print(value)' "$1" | tr -d '\r'
}

echo "Waiting up to ${timeout}s for $base/readyz"
deadline=$((SECONDS + timeout))
until [[ "$(curl -s -o /dev/null -w '%{http_code}' "$base/readyz" || true)" == "200" ]]; do
  ((SECONDS < deadline)) || fail "/readyz did not return 200 within ${timeout}s"
  sleep 2
done
echo "ok   GET /readyz 200"
if $wait_only; then
  exit 0
fi

[[ "$(request GET /healthz 200 | field status)" == "ok" ]] || fail "/healthz status is not ok"
echo "ok   GET /healthz status ok"

if [[ -n "${SMOKE_EXPECT_PATIENT:-}" ]]; then
  request GET "/api/v1/patients/$SMOKE_EXPECT_PATIENT" 200 >/dev/null
  echo "ok   patient from the earlier run still exists (AC-30)"
fi

# The patient is in UTC, and the dose is 5 minutes from now, so it can be recorded now: either early
# (window opens 60 minutes before) or, just before midnight, late on today's date (window: 24 hours).
read -r today dose_time < <(python3 -c '
from datetime import datetime, timedelta, timezone
now = datetime.now(timezone.utc)
print(now.date().isoformat(), (now + timedelta(minutes=5)).strftime("%H:%M"))' | tr -d '\r')

patient_id=$(request POST /api/v1/patients 201 \
  '{"display_name": "Smoke Test Patient", "timezone": "UTC"}' | field id)
echo "ok   POST /api/v1/patients 201"

medication_id=$(request POST "/api/v1/patients/$patient_id/medications" 201 \
  '{"name": "Smoke Med Alpha", "dosage_label": "1 tablet"}' | field id)
echo "ok   POST /api/v1/patients/{id}/medications 201"

schedule_id=$(request POST "/api/v1/medications/$medication_id/schedules" 201 \
  "{\"times_of_day\": [\"$dose_time\"], \"days_of_week\": [1, 2, 3, 4, 5, 6, 7], \"start_date\": \"$today\"}" | field id)
echo "ok   POST /api/v1/medications/{id}/schedules 201 (dose at $dose_time UTC)"

day=$(request GET "/api/v1/patients/$patient_id/doses?date=$today" 200)
scheduled_for=$(python3 -c '
import json, sys
doses = [d for d in json.load(sys.stdin)["doses"] if d["schedule_id"] == sys.argv[1]]
print(doses[0]["scheduled_for"] if len(doses) == 1 else "")' "$schedule_id" <<<"$day" | tr -d '\r')
[[ -n "$scheduled_for" ]] || fail "today's day view does not contain exactly one dose for the new schedule"
echo "ok   GET /api/v1/patients/{id}/doses 200 (planned for $scheduled_for)"

request POST /api/v1/dose-logs 201 \
  "{\"schedule_id\": \"$schedule_id\", \"scheduled_for\": \"$scheduled_for\", \"status\": \"taken\"}" >/dev/null
echo "ok   POST /api/v1/dose-logs 201"

status=$(request GET "/api/v1/patients/$patient_id/doses?date=$today" 200 | python3 -c '
import json, sys
print(next(d["status"] for d in json.load(sys.stdin)["doses"] if d["schedule_id"] == sys.argv[1]))' "$schedule_id" | tr -d '\r')
[[ "$status" == "taken" ]] || fail "the dose shows status '$status' after recording, expected 'taken'"
echo "ok   dose shows as taken"

echo "Smoke test passed against $base"
echo "patient_id=$patient_id"
