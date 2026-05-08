#!/usr/bin/env python3
"""
analyze_captures.py — Summarize and browse traffic captured by mitm_addon.py

Usage:
    # Show all unique endpoints captured (new or known)
    python3 scripts/analyze_captures.py

    # Show only mutation operations (POST/PUT/DELETE/PATCH)
    python3 scripts/analyze_captures.py --mutations

    # Show full request+response for a specific path substring
    python3 scripts/analyze_captures.py --filter ring_flow

        # Show WebSocket frames
        python3 scripts/analyze_captures.py --websocket

        # Analyze no-proxy CDP capture files
        python3 scripts/analyze_captures.py --input private_captures/cdp_requests.jsonl \
            --ws-input private_captures/cdp_websocket.jsonl --websocket

    # Export newly-discovered endpoints as markdown table
    python3 scripts/analyze_captures.py --markdown
"""

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
CAPTURES_DIR = Path(os.environ.get("UNIFI_CAPTURE_DIR", str(PROJECT_DIR / "private_captures")))
JSONL_PATH = CAPTURES_DIR / "requests.jsonl"
WS_PATH = CAPTURES_DIR / "websocket.jsonl"

MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def print_summary(records: list[dict], mutations_only: bool = False):
    seen: dict[str, dict] = {}  # pattern → first record
    for r in records:
        method = r.get("method", "?")
        if mutations_only and method not in MUTATION_METHODS:
            continue
        path = r.get("path", "?")
        status = r.get("status", "?")
        key = f"{method} {path}"
        if key not in seen:
            seen[key] = r

    if not seen:
        print("No records found." + (" (no mutation operations captured yet)" if mutations_only else ""))
        return

    title = "Mutation Operations" if mutations_only else "All Captured Endpoints"
    print(f"\n{'━'*60}")
    print(f"  {title} ({len(seen)} unique patterns)")
    print(f"{'━'*60}")
    for key, r in sorted(seen.items()):
        status = r.get("status", "?")
        ts = r.get("ts", "")[:19].replace("T", " ")
        print(f"  {r['method']:6}  {status:>3}  {r['path']}  [{ts}]")
    print()


def print_detail(records: list[dict], filter_str: str):
    matches = [r for r in records if filter_str.lower() in r.get("path", "").lower()]
    if not matches:
        print(f"No records matching '{filter_str}'")
        return

    print(f"\n{'━'*60}")
    print(f"  {len(matches)} records matching '{filter_str}'")
    print(f"{'━'*60}")
    for r in matches:
        print(f"\n[{r.get('ts','')}]  {r.get('method')}  {r.get('path')}  →  HTTP {r.get('status')}")
        if r.get("query"):
            print(f"  Query:   {json.dumps(r['query'])}")
        req_body = r.get("req_body")
        if req_body:
            print(f"  Request body:")
            if isinstance(req_body, (dict, list)):
                print("    " + json.dumps(req_body, indent=2).replace("\n", "\n    "))
            else:
                print(f"    {str(req_body)[:500]}")
        resp_body = r.get("resp_body")
        if resp_body:
            print(f"  Response body:")
            try:
                parsed = json.loads(resp_body) if isinstance(resp_body, str) else resp_body
                print("    " + json.dumps(parsed, indent=2).replace("\n", "\n    ")[:2000])
            except Exception:
                print(f"    {str(resp_body)[:500]}")
    print()


def print_websocket(records: list[dict]):
    if not records:
        print("No WebSocket frames captured.")
        return
    print(f"\n{'━'*60}")
    print(f"  WebSocket Frames ({len(records)} total)")
    print(f"{'━'*60}")
    for r in records:
        direction = r.get("direction", "?")
        ts = r.get("ts", "")[:19].replace("T", " ")
        content = r.get("content", "")
        try:
            parsed = json.loads(content)
            preview = json.dumps(parsed)[:200]
        except Exception:
            preview = str(content)[:200]
        print(f"  [{ts}]  {direction:20}  {preview}")
    print()


def print_markdown(records: list[dict]):
    seen: dict[str, dict] = {}
    for r in records:
        path = r.get("path", "?")
        method = r.get("method", "?")
        key = f"{method} {path}"
        if key not in seen:
            seen[key] = r

    mutations = {k: v for k, v in seen.items() if v.get("method") in MUTATION_METHODS}

    print("\n## Newly Captured Endpoints (from mitmproxy session)\n")
    print("| Method | Path | Status | Notes |")
    print("|---|---|---|---|")
    for key, r in sorted(seen.items()):
        method = r.get("method", "?")
        path = r.get("path", "?")
        status = r.get("status", "?")
        tag = "⚠️ mutates data" if method in MUTATION_METHODS else ""
        print(f"| `{method}` | `{path}` | {status} | {tag} |")
    print()

    if mutations:
        print("\n## Mutation Request Bodies\n")
        for key, r in sorted(mutations.items()):
            print(f"### {r['method']} `{r['path']}`\n")
            req_body = r.get("req_body")
            if req_body:
                body_str = json.dumps(req_body, indent=2) if isinstance(req_body, (dict, list)) else str(req_body)
                print(f"```json\n{body_str}\n```\n")
            else:
                print("*(no request body)*\n")


def main():
    parser = argparse.ArgumentParser(description="Analyze UniFi Talk proxy captures")
    parser.add_argument("--mutations", action="store_true", help="Show only POST/PUT/DELETE/PATCH")
    parser.add_argument("--filter", metavar="STR", help="Show full detail for paths containing STR")
    parser.add_argument("--websocket", action="store_true", help="Show WebSocket frames")
    parser.add_argument("--ws-input", metavar="FILE", help=f"WebSocket JSONL file to analyze (default: {WS_PATH})")
    parser.add_argument("--markdown", action="store_true", help="Output as markdown table")
    parser.add_argument("--input", metavar="FILE", help=f"JSONL file to analyze (default: {JSONL_PATH})")
    args = parser.parse_args()

    path = Path(args.input) if args.input else JSONL_PATH

    ws_path = Path(args.ws_input) if args.ws_input else WS_PATH

    if args.websocket:
        ws_records = load_records(ws_path)
        print_websocket(ws_records)
        return

    records = load_records(path)
    if not records and not args.websocket:
        print(f"No captured traffic found at: {path}")
        print(f"Run: ./scripts/capture_browser.sh --host 192.168.1.1")
        sys.exit(0)

    if args.filter:
        print_detail(records, args.filter)
    elif args.markdown:
        print_markdown(records)
    else:
        print_summary(records, mutations_only=args.mutations)

    print(f"  Source: {path}  ({os.path.getsize(path) // 1024} KB)")


if __name__ == "__main__":
    main()
