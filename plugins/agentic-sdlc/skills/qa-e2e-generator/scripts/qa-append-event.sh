#!/usr/bin/env bash
#
# qa-append-event.sh — record one progress event for a QA generation run.
#
# Appends a single compact JSON object to <output_dir>/events.jsonl. The log is
# an append-only JSONL stream: one self-contained object per line. Each line
# carries a numeric phase, a step name, a UTC timestamp, a status, and any
# caller-supplied extra fields merged on top.
#
# Usage: qa-append-event.sh <output_dir> <phase> <name> <status> [extra_json]
#   output_dir  directory that holds the run's events.jsonl (created if absent)
#   phase       numeric phase, emitted as a raw JSON number (not a string)
#   name        step label (string)
#   status      step status (string)
#   extra_json  optional JSON object; its keys are merged in and win on clash;
#               defaults to {} when omitted or empty
#
# Requires: jq. Exit 0 on success, 1 on a usage error; jq's nonzero status
# aborts the run (strict mode) when phase or extra_json are not valid JSON.

set -o errexit
set -o nounset
set -o pipefail

if (( $# < 4 )); then
    printf 'Usage: %s <output_dir> <phase> <name> <status> [extra_json]\n' \
        "$(basename "$0")" >&2
    exit 1
fi

run_dir=$1
phase_number=$2
step_name=$3
step_status=$4
extra_object=${5:-}

# An absent or blank extra argument collapses to an empty object.
if [[ -z "$extra_object" ]]; then
    extra_object='{}'
fi

# Base fields first, then a shallow merge (+) of the extra object so callers can
# override any base key. `now | todate` yields an ISO-8601 UTC instant.
event_line=$(
    jq -cn \
        --argjson phase "$phase_number" \
        --arg name "$step_name" \
        --arg status "$step_status" \
        --argjson extra "$extra_object" \
        '{phase: $phase, name: $name, timestamp: (now | todate), status: $status} + $extra'
)

mkdir -p "$run_dir"
printf '%s\n' "$event_line" >> "$run_dir/events.jsonl"
