#!/usr/bin/env python3
"""
ws_monitor.py — Connect to UniFi Talk WebSocket and monitor real-time events.

Usage:
    # Authenticate first (or pass an existing token):
    python3 scripts/ws_monitor.py --host 192.168.1.1 --username admin --password yourpass

    # Or pass a token you've already captured:
    python3 scripts/ws_monitor.py --host 192.168.1.1 --token eyJ...

Output:
    Prints JSON events to stdout and appends them to captures/ws_events.jsonl
"""

import argparse
import base64
import json
import ssl
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

try:
    import websocket  # websocket-client library
except ImportError:
    print("Install websocket-client: pip3 install websocket-client requests")
    sys.exit(1)

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    print("Install requests: pip3 install requests")
    sys.exit(1)

CAPTURES_DIR = Path(__file__).parent.parent / "captures"

# WebSocket paths/URLs to try (in order of probability)
# JS bundle: talk_ws_url = `wss://${hostname}:3419`  (backend listens on 3419, localhost-only)
# CONFIRMED (2026-05-07): wss://<host>/proxy/talk/ws — nginx proxy forwards to localhost:3419
# Port 3419 is firewalled from LAN clients; must use the nginx proxy path.
WS_ENTRIES = [
    # Direct backend on port 3419 (firewalled — will be refused from LAN)
    ("direct", "wss://{host}:3419"),              # refused from LAN
    ("direct", "wss://{host}:3419/wss"),          # refused from LAN
    ("direct", "wss://{host}:3419/ws"),           # refused from LAN
    ("direct", "wss://{host}:3419/events"),       # refused from LAN
    # Nginx reverse-proxy paths (host:443) — CONFIRMED working:
    ("proxy",  "wss://{host}/proxy/talk/ws"),     # ✅ CONFIRMED
    ("proxy",  "wss://{host}/proxy/talk/wss"),
    ("proxy",  "wss://{host}/proxy/talk/wss/s/default/events"),
]


def login(host: str, username: str, password: str):  # -> tuple[str, str]
    """Authenticate with UniFi OS. Returns (token, csrf_token)."""
    url = f"https://{host}/api/auth/login"
    payload = {"username": username, "password": password, "rememberMe": False}
    r = requests.post(url, json=payload, verify=False, timeout=10)
    if r.status_code not in (200, 201):
        print(f"[-] Login failed: HTTP {r.status_code} — {r.text[:200]}")
        sys.exit(1)

    token = r.cookies.get("TOKEN", "")
    # CSRF from JSON body is always empty string — extract from JWT payload instead
    csrf = ""
    if token:
        try:
            payload_b64 = token.split(".")[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.b64decode(payload_b64))
            csrf = payload.get("csrfToken", "")
        except Exception:
            pass
    csrf = csrf or r.headers.get("x-updated-csrf-token", "") or r.json().get("csrf_token", "")
    if not token:
        print("[-] No TOKEN cookie in login response")
        sys.exit(1)
    print(f"[+] Authenticated. Token (first 20 chars): {token[:20]}...")
    return token, csrf


def on_message(ws, message):
    ts = datetime.now(tz=timezone.utc).isoformat()
    try:
        parsed = json.loads(message)
        pretty = json.dumps(parsed, indent=2)
        event_type = parsed.get("type") or parsed.get("meta", {}).get("message", "?")
        print(f"\n[{ts}] EVENT: {event_type}")
        print(pretty[:2000])
    except json.JSONDecodeError:
        print(f"\n[{ts}] RAW: {message[:500]}")
        parsed = {"raw": message}

    record = {"ts": ts, "data": parsed if isinstance(parsed, dict) else message}
    log_file = CAPTURES_DIR / "ws_events.jsonl"
    CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a") as f:
        f.write(json.dumps(record) + "\n")


def on_error(ws, error):
    print(f"[WS ERROR] {error}")


def on_close(ws, close_status_code, close_msg):
    print(f"[WS CLOSED] {close_status_code} — {close_msg}")


def on_open(ws):
    print("[WS OPEN] Connected! Listening for events...")


def try_connect(url: str, token: str, csrf: str) -> bool:
    print(f"[*] Trying {url}")

    # NOTE: Do NOT add 'Upgrade' header manually — websocket-client adds it automatically.
    # Adding it twice causes nginx to return 400 Bad Request.
    headers = [
        f"Cookie: TOKEN={token}",
        f"X-CSRF-Token: {csrf}",
    ]

    ssl_opts = {"cert_reqs": ssl.CERT_NONE}
    connected_ok = False

    def _on_open(ws):
        nonlocal connected_ok
        connected_ok = True
        on_open(ws)

    ws = websocket.WebSocketApp(
        url,
        header=headers,
        on_open=_on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    try:
        ws.run_forever(sslopt=ssl_opts, ping_interval=30, ping_timeout=10)
    except Exception as e:
        print(f"  [-] Exception: {e}")

    return connected_ok


def main():
    parser = argparse.ArgumentParser(description="Monitor UniFi Talk WebSocket events")
    parser.add_argument("--host", required=True, help="UDM IP or hostname")
    parser.add_argument("--username", "-u", help="UniFi OS username")
    parser.add_argument("--password", "-p", help="UniFi OS password")
    parser.add_argument("--token", help="Existing TOKEN cookie value")
    parser.add_argument("--csrf", default="", help="CSRF token (if known)")
    parser.add_argument("--url", help="Specific WebSocket URL to try (skips auto-discovery)")
    args = parser.parse_args()

    if args.token:
        token, csrf = args.token, args.csrf
    elif args.username and args.password:
        token, csrf = login(args.host, args.username, args.password)
    else:
        parser.error("Provide either --token or both --username and --password")

    if args.url:
        entries = [("manual", args.url)]
    else:
        entries = [(kind, url.format(host=args.host)) for kind, url in WS_ENTRIES]

    for kind, url in entries:
        print(f"\n{'='*60}")
        ok = try_connect(url, token, csrf)
        if ok:
            print(f"[+] Connected successfully on {url}")
            break
        print(f"  [-] {url} did not connect ({kind}), trying next...")
        time.sleep(1)


if __name__ == "__main__":
    main()
