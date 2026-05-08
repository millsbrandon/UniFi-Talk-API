#!/usr/bin/env python3
"""
sanitize_capture.py — scrub private capture files before promoting into tracked docs/data.

Usage:
    python3 scripts/sanitize_capture.py \
      --input private_captures/ws_events_focus.jsonl \
      --output analysis/sanitized/ws_events_focus.sanitized.jsonl

Supports JSON and JSONL inputs. Applies key-based anonymization plus regex scrubbing
for phone numbers, emails, MACs, IP addresses, and UUIDs.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SENSITIVE_KEY_SUBS = {
    "name": "Example Name",
    "first_name": "Example",
    "last_name": "User",
    "email": "user@example.com",
    "phone_number": "+15551234567",
    "number": "+15551234567",
    "address": "123 Example St",
    "city": "Example City",
    "state": "EX",
    "zip": "12345",
    "postal_code": "12345",
    "username": "example-user",
    "display_name": "Example User",
    "caller_name": "Example Caller",
    "callee_name": "Example Callee",
    "serial": "EXAMPLE-SERIAL",
    "mac": "00:11:22:33:44:55",
    "hostname": "example-host",
}

REGEX_REPLACEMENTS = [
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), "00000000-0000-0000-0000-000000000000"),
    (re.compile(r"(?<!\w)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\w)"), "+15551234567"),
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "user@example.com"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "192.0.2.1"),
    (re.compile(r"\b[0-9a-f]{2}(?::[0-9a-f]{2}){5}\b", re.I), "00:11:22:33:44:55"),
    (re.compile(r"(?<![0-9a-f-])[0-9a-f]{12}(?![0-9a-f-])", re.I), "001122334455"),
]


def scrub_string(value: str) -> str:
    out = value
    for pattern, replacement in REGEX_REPLACEMENTS:
        out = pattern.sub(replacement, out)
    return out


def scrub_obj(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            key = str(k).lower()
            if key in SENSITIVE_KEY_SUBS:
                out[k] = SENSITIVE_KEY_SUBS[key]
            else:
                out[k] = scrub_obj(v)
        return out
    if isinstance(value, list):
        return [scrub_obj(item) for item in value]
    if isinstance(value, str):
        return scrub_string(value)
    return value


def process_json(input_path: Path, output_path: Path) -> int:
    data = json.loads(input_path.read_text())
    cleaned = scrub_obj(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(cleaned, indent=2))
    return 1


def process_jsonl(input_path: Path, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with input_path.open() as src, output_path.open("w") as dst:
        for line in src:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            cleaned = scrub_obj(row)
            dst.write(json.dumps(cleaned) + "\n")
            count += 1
    return count


def main() -> None:
    ap = argparse.ArgumentParser(description="Sanitize private UniFi Talk captures")
    ap.add_argument("--input", required=True, help="Path to input JSON/JSONL file")
    ap.add_argument("--output", required=True, help="Path to sanitized output JSON/JSONL file")
    args = ap.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    if input_path.suffix.lower() == ".jsonl":
        count = process_jsonl(input_path, output_path)
    else:
        count = process_json(input_path, output_path)

    print(f"Sanitized {count} record(s): {input_path} -> {output_path}")


if __name__ == "__main__":
    main()
