#!/usr/bin/env python3
"""
analyze_ws_call_control.py — summarize call-control-related websocket events.

This is intended for outbound-call and recording investigations. Feed it the raw
private capture from ws_monitor and it will extract candidate signals for:
- call start/initiate
- hangup/end/terminate
- recording/voicemail transitions

Usage:
    python3 scripts/analyze_ws_call_control.py \
      --input private_captures/ws_events.jsonl \
      --output private_captures/ws_call_control_summary.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

INTERESTING = (
    "call",
    "record",
    "voicemail",
    "hangup",
    "hang_up",
    "terminate",
    "end_call",
    "dial",
    "outbound",
    "initiate",
    "start",
)


def flatten(obj: Any) -> str:
    try:
        return json.dumps(obj, default=str).lower()
    except Exception:
        return str(obj).lower()


def classify_event_name(data: dict[str, Any]) -> str:
    return str(
        data.get("event")
        or data.get("type")
        or data.get("meta", {}).get("message")
        or "unknown"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Summarize call-control websocket events")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    type_counts: Counter[str] = Counter()
    call_event_counts: Counter[str] = Counter()
    call_status_counts: Counter[str] = Counter()
    call_direction_counts: Counter[str] = Counter()
    keyword_hits: Counter[str] = Counter()
    samples: list[dict[str, Any]] = []
    call_event_samples: list[dict[str, Any]] = []

    with input_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            data = row.get("data", {})
            event_type = classify_event_name(data)
            type_counts[str(event_type)] += 1

            # CALL_LOG_UPDATED embeds granular call lifecycle events.
            if event_type == "CALL_LOG_UPDATED":
                for record in data.get("data", {}).get("records", []):
                    status = str(record.get("status") or "unknown")
                    direction = str(record.get("direction") or "unknown")
                    call_status_counts[status] += 1
                    call_direction_counts[direction] += 1

                    for call_event in record.get("call_events", []):
                        call_name = str(call_event.get("event") or "unknown")
                        call_event_counts[call_name] += 1

                        event_blob = flatten(call_event)
                        if any(k in event_blob for k in INTERESTING) and len(call_event_samples) < 100:
                            call_event_samples.append(
                                {
                                    "ts": call_event.get("time"),
                                    "call_event": call_name,
                                    "status": status,
                                    "direction": direction,
                                    "event_data": call_event.get("event_data", {}),
                                }
                            )

            blob = flatten(row)
            matched = [k for k in INTERESTING if k in blob]
            if matched:
                for k in matched:
                    keyword_hits[k] += 1
                if len(samples) < 100:
                    samples.append(
                        {
                            "ts": row.get("ts"),
                            "scenario": row.get("scenario", ""),
                            "event_type": event_type,
                            "matched": sorted(set(matched)),
                            "data": data,
                        }
                    )

    summary = {
        "input": str(input_path),
        "events_total": sum(type_counts.values()),
        "event_types": dict(type_counts.most_common()),
        "call_log_statuses": dict(call_status_counts.most_common()),
        "call_log_directions": dict(call_direction_counts.most_common()),
        "call_event_types": dict(call_event_counts.most_common()),
        "keyword_hits": dict(keyword_hits.most_common()),
        "candidate_events": samples,
        "candidate_call_events": call_event_samples,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, default=str))
    print(f"Wrote websocket call-control summary: {out}")
    print(f"Total events: {summary['events_total']}")


if __name__ == "__main__":
    main()
