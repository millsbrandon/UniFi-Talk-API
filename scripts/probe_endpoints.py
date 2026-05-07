#!/usr/bin/env python3
"""
probe_endpoints.py — Exhaustive endpoint prober for UniFi Talk API.

Tries every known and candidate endpoint, records status codes and response
shapes, and writes a structured probe report to analysis/probe_results.json.

Usage:
    python3 scripts/probe_endpoints.py --host 192.168.1.1 -u admin -p yourpass
    python3 scripts/probe_endpoints.py --host 192.168.1.1 --token eyJ...

    # Only re-probe unknowns (skip already-confirmed 200s):
    python3 scripts/probe_endpoints.py --host 192.168.1.1 -u admin -p yourpass --unknowns-only
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    print("Install requests: pip3 install requests")
    sys.exit(1)

OUTPUT_FILE = Path(__file__).parent.parent / "analysis" / "probe_results.json"
CAPTURES_DIR = Path(__file__).parent.parent / "captures" / "api_responses" / "probe"

BASE = "/proxy/talk/api"

# ── Endpoint manifest ─────────────────────────────────────────────────────────
# Format: (method, path, note)
# Paths without leading slash are appended to BASE.
# Paths starting with / are used as-is.
ENDPOINTS = [
    # ── Auth & identity ──────────────────────────────────────────────────────
    ("GET",  "user/info",                         "Current user role/permissions"),
    ("GET",  "info",                              "Talk version, region, feature flags"),
    ("GET",  "info/app_owner",                    "Owner ULP ID"),

    # ── System / install ─────────────────────────────────────────────────────
    ("GET",  "install",                           "Installation & billing status"),
    ("GET",  "setup_complete",                    "Whether onboarding is done"),
    ("GET",  "ucore/system_info",                 "UniFi OS core system info"),
    ("GET",  "dashboard/consolidated_info",       "Dashboard summary"),
    ("GET",  "dashboard/most_active_users",       "Top callers"),
    ("GET",  "service_health",                    "Service health data (candidate)"),
    ("GET",  "peer_consoles",                     "Peer consoles on LAN"),
    ("GET",  "applications",                      "Installed apps"),
    ("GET",  "updates",                           "Available firmware/app updates"),

    # ── Call log ─────────────────────────────────────────────────────────────
    ("GET",  "call_log?page=1&per_page=10",       "Paginated call history"),
    ("GET",  "call_log/countries",                "Countries in call log"),
    ("GET",  "call_recording_rule",               "Call recording rules"),
    ("GET",  "call_center/queue",                 "Call center queue"),

    # ── Voicemail / audio ────────────────────────────────────────────────────
    ("GET",  "setting/voicemail_greeting_file",   "Global voicemail greeting MP3"),
    ("GET",  "setting/hold_music",                "Hold music config"),
    ("GET",  "setting/ringtones",                 "Ringtone list"),
    ("GET",  "exports/audio_data_archive",        "Bulk audio export (500 when idle)"),
    ("POST", "prepare_audio_data",                "Trigger audio export (candidate)"),
    ("GET",  "voicemail/list",                    "Voicemail list (candidate — may 404)"),
    ("GET",  "voicemail",                         "Voicemail root (candidate)"),
    ("GET",  "setting/vm_greeting_info",          "VM greeting metadata (candidate)"),
    ("GET",  "setting/vm_greeting",               "VM greeting config (candidate)"),

    # ── Voicemail download candidates ────────────────────────────────────────
    # Real UUID from confirmed capture — replace with a live one when testing
    ("GET",  "call_log/de8df029-f93e-48b3-a3f5-529c1fff996c/recording",
                                                  "Recording download by call UUID (candidate)"),
    ("GET",  "call_log/de8df029-f93e-48b3-a3f5-529c1fff996c/voicemail",
                                                  "Voicemail download by call UUID (candidate)"),
    ("GET",  "call_log/de8df029-f93e-48b3-a3f5-529c1fff996c/audio",
                                                  "Audio download by call UUID (candidate)"),
    ("GET",  "recording/de8df029-f93e-48b3-a3f5-529c1fff996c",
                                                  "Recording by UUID (candidate)"),
    ("GET",  "voicemail/de8df029-f93e-48b3-a3f5-529c1fff996c",
                                                  "Voicemail by UUID (candidate)"),
    ("GET",  "voicemail/de8df029-f93e-48b3-a3f5-529c1fff996c/audio",
                                                  "Voicemail audio by UUID (candidate)"),
    ("GET",  "media/de8df029-f93e-48b3-a3f5-529c1fff996c",
                                                  "Media by call UUID (candidate)"),

    # ── Devices ──────────────────────────────────────────────────────────────
    ("GET",  "devices",                           "All adopted Talk devices"),
    ("GET",  "device/24h_call_quality",           "24h call quality per device"),
    ("GET",  "drive_status",                      "Drive status"),
    ("GET",  "debug/pcap/status",                 "Packet capture status"),

    # ── Users & numbers ──────────────────────────────────────────────────────
    ("GET",  "users",                             "All Talk users"),
    ("GET",  "number/list",                       "All DIDs with SIP/user data"),
    ("GET",  "number/blocked",                    "Blocked caller IDs"),
    ("GET",  "number/porting/list",               "Number porting list"),
    ("GET",  "number/porting/request_count",      "Number porting request counts"),
    ("GET",  "contact_list",                      "Shared contact directory"),
    ("GET",  "contacts",                          "Contacts (alternate path)"),
    ("GET",  "billing/coupons/balance",           "Billing coupon balance"),

    # ── SMS ──────────────────────────────────────────────────────────────────
    ("GET",  "sms/conversations",                 "SMS conversations"),
    ("GET",  "sms/conversations?page=1",          "SMS conversations paginated (candidate)"),

    # ── Call routing ─────────────────────────────────────────────────────────
    ("GET",  "ring_flow",                         "Ring flow / call routing"),
    ("GET",  "group/list",                        "Ring groups"),
    ("GET",  "queues",                            "Call queues"),
    ("GET",  "queue",                             "Queue alt path (candidate)"),
    ("GET",  "parking_lots",                      "Call parking lots"),
    ("GET",  "switchboard",                       "Switchboard config"),
    ("GET",  "phone_designer",                    "Phone screen layout"),
    ("GET",  "phone_designer/wallpaper/list",     "Phone wallpaper list"),

    # ── Smart attendant / IVR ────────────────────────────────────────────────
    ("GET",  "smart_attendant",                   "Smart attendant config (candidate)"),
    ("GET",  "smart_attendants",                  "Smart attendants list (candidate)"),
    ("GET",  "ivr",                               "IVR config (candidate)"),
    ("GET",  "ivr/list",                          "IVR list (candidate)"),

    # ── SIP / Trunking ───────────────────────────────────────────────────────
    ("GET",  "third_party_sip/gateway_list",      "SIP trunk/gateway list"),
    ("GET",  "sip/gateways",                      "SIP gateways alt (candidate)"),

    # ── Settings ─────────────────────────────────────────────────────────────
    ("GET",  "setting/config",                    "Full system config"),
    ("GET",  "setting/emergency_status",          "E911 status"),
    ("GET",  "setting/default_area_code",         "Default area code"),
    ("GET",  "setting/dialing_country",           "Dialing country"),
    ("GET",  "emergency_address/list",            "E911 address list"),
    ("GET",  "lock/usage",                        "Lock/seat usage"),
    ("GET",  "identity_status",                   "Business profile/KYC status"),
    ("GET",  "regulatory_bundle",                 "Regulatory bundle (A2P/CNAM)"),
    ("GET",  "setting/notifier_settings",         "Notification settings (candidate)"),
    ("GET",  "cnam_lookup",                       "CNAM lookup config (candidate)"),
    ("GET",  "owner_transfer/transfer_state",     "Owner transfer state"),

    # ── Protect / Integrations ───────────────────────────────────────────────
    ("GET",  "protect/cameras",                   "Protect cameras for video calling"),
    ("GET",  "protect/devices",                   "Protect devices (candidate)"),

    # ── AI / Transcription ───────────────────────────────────────────────────
    ("GET",  "ai_call_transcriptions",            "AI call transcription settings (candidate)"),
    ("GET",  "ai_vm_transcriptions",              "AI voicemail transcription settings (candidate)"),
    ("GET",  "transcription",                     "Transcription root (candidate)"),

    # ── Phone designer ───────────────────────────────────────────────────────
    ("GET",  "phone_design",                      "Phone design alt (candidate)"),

    # ── Debug / system ops ───────────────────────────────────────────────────
    ("GET",  "debug/pcap/status",                 "PCAP capture status"),
    ("GET",  "syslog",                            "System log (candidate)"),
    ("GET",  "system_settings",                   "System settings alt (candidate)"),
    ("GET",  "cloud_urls",                        "Cloud URLs (candidate)"),
    ("GET",  "cloud_env",                         "Cloud environment (candidate)"),

    # ── Calling status / trunking ────────────────────────────────────────────
    ("GET",  "calling/status",                    "Calling service status (candidate)"),
    ("GET",  "trunking",                          "Trunking config (candidate)"),
    ("GET",  "international",                     "International calling config (candidate)"),

    # ── Insights / analytics ─────────────────────────────────────────────────
    ("GET",  "insights",                          "Insights summary (candidate)"),
    ("GET",  "insights/calls",                    "Call insights (candidate)"),
    ("GET",  "insights/sms",                      "SMS insights (candidate)"),
    ("GET",  "insights/ai",                       "AI insights (candidate)"),

    # ── WebSocket probe (HTTP upgrade — will 400/101) ─────────────────────────
    # Probed separately in ws_monitor.py
]

# Already confirmed 200 — skip in --unknowns-only mode
CONFIRMED_OK = {
    "user/info", "info", "info/app_owner", "install", "setup_complete",
    "ucore/system_info", "dashboard/consolidated_info", "dashboard/most_active_users",
    "peer_consoles", "applications", "updates",
    "call_log?page=1&per_page=10", "call_log/countries", "call_recording_rule",
    "call_center/queue", "setting/voicemail_greeting_file", "setting/hold_music",
    "setting/ringtones", "devices", "device/24h_call_quality", "drive_status",
    "debug/pcap/status", "users", "number/list", "number/blocked",
    "number/porting/list", "number/porting/request_count", "contact_list", "contacts",
    "billing/coupons/balance", "sms/conversations", "ring_flow", "group/list",
    "queues", "parking_lots", "switchboard", "phone_designer",
    "phone_designer/wallpaper/list", "third_party_sip/gateway_list",
    "setting/config", "setting/emergency_status", "setting/default_area_code",
    "setting/dialing_country", "emergency_address/list", "lock/usage",
    "identity_status", "regulatory_bundle", "owner_transfer/transfer_state",
    "protect/cameras", "billing/coupons/balance",
}


# ── Auth ──────────────────────────────────────────────────────────────────────

def login(host: str, username: str, password: str):
    url = f"https://{host}/api/auth/login"
    r = requests.post(
        url,
        json={"username": username, "password": password, "rememberMe": False},
        verify=False,
        timeout=10,
    )
    if r.status_code not in (200, 201):
        print(f"[-] Login failed: HTTP {r.status_code} — {r.text[:200]}")
        sys.exit(1)
    token = r.cookies.get("TOKEN", "")
    csrf = r.headers.get("x-updated-csrf-token") or r.json().get("csrf_token") or ""
    if not csrf:
        # Decode from JWT payload
        try:
            import base64
            payload_b64 = token.split(".")[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.b64decode(payload_b64))
            csrf = payload.get("csrfToken", "")
        except Exception:
            pass
    print(f"[+] Authenticated. CSRF: {csrf[:20]}...")
    return token, csrf


# ── Probing ───────────────────────────────────────────────────────────────────

def probe(host: str, token: str, csrf: str, unknowns_only: bool = False):
    session = requests.Session()
    session.verify = False
    session.cookies.set("TOKEN", token)
    session.headers.update({
        "X-CSRF-Token": csrf,
        "Accept": "application/json",
    })

    results = {"200": [], "401_403": [], "404": [], "500": [], "other": [], "error": []}
    total = len(ENDPOINTS)

    print(f"\n[*] Probing {total} endpoints against https://{host}")
    print(f"    Base: {BASE}\n")

    for i, (method, path, note) in enumerate(ENDPOINTS, 1):
        if unknowns_only and path in CONFIRMED_OK:
            continue

        full_path = f"{BASE}/{path}" if not path.startswith("/") else path
        url = f"https://{host}{full_path}"

        try:
            if method == "GET":
                resp = session.get(url, timeout=10)
            elif method == "POST":
                resp = session.post(url, json={}, timeout=10)
            elif method == "PUT":
                resp = session.put(url, json={}, timeout=10)
            elif method == "DELETE":
                resp = session.delete(url, timeout=10)
            else:
                continue

            status = resp.status_code
            ct = resp.headers.get("content-type", "")
            size = len(resp.content)

            body_snippet = ""
            body_parsed = None
            if "json" in ct:
                try:
                    body_parsed = resp.json()
                    body_snippet = json.dumps(body_parsed)[:200]
                except Exception:
                    body_snippet = resp.text[:200]
            else:
                body_snippet = resp.text[:200]

            icon = {200: "✅", 201: "✅", 401: "🔐", 403: "🔐", 404: "❌", 500: "⚠️"}.get(status, "❓")
            print(f"  [{i:3}/{total}] {icon} {method:6} {full_path}  →  {status}  ({size}B)  {note}")

            record = {
                "method": method,
                "path": full_path,
                "note": note,
                "status": status,
                "content_type": ct,
                "size": size,
                "body_snippet": body_snippet,
                "body": body_parsed,
            }

            if status in (200, 201):
                results["200"].append(record)
            elif status in (401, 403):
                results["401_403"].append(record)
            elif status == 404:
                results["404"].append(record)
            elif status == 500:
                results["500"].append(record)
            else:
                results["other"].append(record)

            # Save full response for 200s
            if status in (200, 201):
                CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
                safe = path.replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "_")
                fname = f"{safe[:80]}.json"
                full_record = {
                    "ts": datetime.now(tz=timezone.utc).isoformat(),
                    "method": method,
                    "url": url,
                    "status": status,
                    "headers": dict(resp.headers),
                    "body": body_parsed or resp.text,
                }
                (CAPTURES_DIR / fname).write_text(json.dumps(full_record, indent=2))

            time.sleep(0.15)  # be gentle

        except requests.exceptions.ConnectionError as e:
            print(f"  [{i:3}/{total}] ❌  {method:6} {full_path}  →  CONNECTION ERROR: {e}")
            results["error"].append({"method": method, "path": full_path, "error": str(e)})
        except requests.exceptions.Timeout:
            print(f"  [{i:3}/{total}] ⏱  {method:6} {full_path}  →  TIMEOUT")
            results["error"].append({"method": method, "path": full_path, "error": "timeout"})

    return results


def print_summary(results: dict):
    print("\n" + "=" * 60)
    print("PROBE SUMMARY")
    print("=" * 60)
    print(f"  ✅  200/201 OK:      {len(results['200'])}")
    print(f"  🔐  401/403 Auth:    {len(results['401_403'])}")
    print(f"  ❌  404 Not Found:   {len(results['404'])}")
    print(f"  ⚠️   500 Error:       {len(results['500'])}")
    print(f"  ❓  Other:           {len(results['other'])}")
    print(f"  💥  Conn/Timeout:    {len(results['error'])}")

    if results["200"]:
        print("\n  NEW 200 OK ENDPOINTS:")
        for r in results["200"]:
            print(f"    {r['method']:6} {r['path']}")
            if r["body_snippet"]:
                print(f"           → {r['body_snippet'][:100]}")

    if results["401_403"]:
        print("\n  REQUIRES SPECIAL AUTH (401/403):")
        for r in results["401_403"]:
            print(f"    {r['method']:6} {r['path']}")

    if results["500"]:
        print("\n  SERVER ERRORS (500) — endpoint exists but failed:")
        for r in results["500"]:
            print(f"    {r['method']:6} {r['path']}  →  {r['body_snippet'][:100]}")


def main():
    parser = argparse.ArgumentParser(description="UniFi Talk endpoint prober")
    parser.add_argument("--host", required=True, help="UDM IP or hostname")
    parser.add_argument("--username", "-u", help="Local admin username")
    parser.add_argument("--password", "-p", help="Local admin password")
    parser.add_argument("--token", help="Existing TOKEN JWT cookie")
    parser.add_argument("--csrf", help="Existing X-CSRF-Token")
    parser.add_argument("--unknowns-only", action="store_true",
                        help="Skip endpoints already confirmed as 200")
    args = parser.parse_args()

    if args.token:
        token = args.token
        csrf = args.csrf or ""
        if not csrf:
            # Try to extract CSRF from JWT
            try:
                import base64
                payload_b64 = token.split(".")[1]
                payload_b64 += "=" * (4 - len(payload_b64) % 4)
                payload = json.loads(base64.b64decode(payload_b64))
                csrf = payload.get("csrfToken", "")
                if csrf:
                    print(f"[+] CSRF extracted from JWT: {csrf[:20]}...")
            except Exception:
                pass
    elif args.username and args.password:
        token, csrf = login(args.host, args.username, args.password)
    else:
        parser.error("Provide --token or --username/--password")
        return

    results = probe(args.host, token, csrf, unknowns_only=args.unknowns_only)
    print_summary(results)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(results, indent=2))
    print(f"\n[+] Full results written to {OUTPUT_FILE}")
    print(f"[+] 200 response bodies saved to {CAPTURES_DIR}/")


if __name__ == "__main__":
    main()
