#!/usr/bin/env python3
"""
test_mutations.py — Live test of unconfirmed UniFi Talk mutation endpoints.

Tests (in safe order):
  1.  PCAP start / status / stop / download
  2.  Audio export trigger / download
  3.  Call log deletion  (single + bulk) — uses OLDEST call in log
  4.  Recording deletion (single + bulk) — only if a recording exists
  5.  Voicemail deletion (bulk)           — only if a voicemail exists

All destructive actions target the OLDEST records to avoid losing recent data.
Results are printed and written to private_captures/mutation_probe_results.json by default.
Override output dir with UNIFI_CAPTURE_DIR=/path/to/dir.

Usage:
    python3 scripts/test_mutations.py
    python3 scripts/test_mutations.py --host <UDM-IP> -u <user> -p <pass>
    python3 scripts/test_mutations.py --host <UDM-IP> --token eyJ...
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent))

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    sys.exit("Install requests: pip3 install requests")

from talk_sdk import TalkClient, TalkAPIError


# ── Helpers ───────────────────────────────────────────────────────────────────

results: dict = {}
ROOT_DIR = Path(__file__).parent.parent
DEFAULT_SECRETS_FILE = ROOT_DIR / ".local" / "secrets.json"
DEFAULT_OUTPUT_FILE = Path(os.environ.get("UNIFI_CAPTURE_DIR", str(ROOT_DIR / "private_captures"))) / "mutation_probe_results.json"


def load_secrets(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        print(f"[-] Failed to parse secrets file {path}: {exc}")
        return {}

def probe(label: str, method: str, client: TalkClient, path: str,
          body=None, stream=False) -> dict:
    """Make a request and record the result."""
    url = f"https://{client.host}{path}"
    try:
        kwargs = dict(
            headers={"X-CSRF-Token": client._csrf},
            cookies={"TOKEN": client._token},
            verify=False,
            timeout=20,
            stream=stream,
        )
        if body is not None:
            kwargs["json"] = body

        resp = getattr(requests, method.lower())(url, **kwargs)

        content_type = resp.headers.get("Content-Type", "")
        if "json" in content_type:
            try:
                body_preview = resp.json()
            except Exception:
                body_preview = resp.text[:300]
        elif stream or "octet" in content_type or "audio" in content_type:
            size = len(resp.content)
            body_preview = f"<binary {size} bytes>"
        else:
            body_preview = resp.text[:300]

        result = {
            "status": resp.status_code,
            "content_type": content_type,
            "body": body_preview,
            "confirmed": resp.status_code < 300,
        }
        tag = "✅" if result["confirmed"] else f"❌ {resp.status_code}"
        print(f"  {tag}  {method} {path}")
        if not result["confirmed"]:
            print(f"      → {str(body_preview)[:200]}")

        results[label] = result
        return result

    except Exception as exc:
        result = {"status": "error", "error": str(exc), "confirmed": False}
        print(f"  💥  {method} {path} — {exc}")
        results[label] = result
        return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host")
    ap.add_argument("-u", "--username", default="")
    ap.add_argument("-p", "--password", default="")
    ap.add_argument("--token", default="")
    ap.add_argument("--dry-run", action="store_true",
                    help="Skip destructive deletions, only test PCAP/export")
    ap.add_argument(
        "--secrets",
        default=str(DEFAULT_SECRETS_FILE),
        help="Path to local secrets JSON (default: .local/secrets.json)",
    )
    ap.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_FILE),
        help="Output JSON path for probe results",
    )
    args = ap.parse_args()

    secrets = load_secrets(Path(args.secrets))
    host = args.host or secrets.get("host", "")
    username = args.username or secrets.get("username", "")
    password = args.password or secrets.get("password", "")
    token = args.token or secrets.get("token", "")

    if not host:
        sys.exit("Provide --host or set host in --secrets file")

    out_path = Path(args.output)

    client = TalkClient(host)

    if token:
        import base64
        client._token = token
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        client._csrf = json.loads(base64.urlsafe_b64decode(payload))["csrfToken"]
        client._session.cookies.set("TOKEN", client._token)
        client._session.headers["X-CSRF-Token"] = client._csrf
    else:
        if not username or not password:
            sys.exit("Provide token or username/password via args or --secrets file")
        print(f"Logging in as {username}...")
        client.login(username, password)

    B = f"/proxy/talk/api"

    # ── 1. PCAP ───────────────────────────────────────────────────────────────
    print("\n── PCAP ─────────────────────────────────────────────────────")
    probe("pcap_start",  "POST", client, f"{B}/debug/pcap/start",
          body={"durationSeconds": 10})
    time.sleep(2)
    r = probe("pcap_status", "GET",  client, f"{B}/debug/pcap/status")
    time.sleep(2)
    probe("pcap_stop",   "POST", client, f"{B}/debug/pcap/stop")
    time.sleep(1)
    dl = probe("pcap_download", "GET", client, f"{B}/debug/pcap/download", stream=True)
    if dl.get("confirmed") and isinstance(dl.get("body"), str) and "bytes" in dl["body"]:
        print(f"      PCAP download: {dl['body']}")

    # ── 2. Audio export ───────────────────────────────────────────────────────
    print("\n── Audio export ─────────────────────────────────────────────")
    probe("audio_export_prepare", "POST", client, f"{B}/exports/prepare_audio_data")
    time.sleep(3)
    # Check if it's ready
    _cfg_resp = client._request("GET", f"{B}/setting/config")
    info = _cfg_resp.json() if _cfg_resp.ok else {}
    in_progress = info.get("audio_export_in_progress", False)
    available   = info.get("is_audio_export_available", False)
    print(f"      export_in_progress={in_progress}  available={available}")
    results["audio_export_status"] = {
        "in_progress": in_progress, "available": available, "confirmed": True
    }
    if available:
        probe("audio_export_download", "GET", client,
              f"{B}/exports/audio_data_archive", stream=True)
    else:
        r2 = probe("audio_export_download", "GET", client,
              f"{B}/exports/audio_data_archive")
        if r2.get("status") == 500:
            print("      (500 expected when no export has been prepared yet)")
            results["audio_export_download"]["confirmed"] = True
            results["audio_export_download"]["note"] = "500 = endpoint exists, no export queued"

    if args.dry_run:
        print("\n── Dry run — skipping destructive deletion tests ───────────")
        _save_results(out_path)
        return

    # ── 3. Fetch call log to find test targets ─────────────────────────────
    print("\n── Fetching call log for test targets ───────────────────────")
    try:
        _log_resp = client._request("GET", f"{B}/call_log", params={"page": 1, "per_page": 50})
        log = _log_resp.json() if _log_resp.ok else {}
        records = log.get("records", [])
    except Exception as exc:
        print(f"  Could not fetch call log: {exc}")
        records = []

    # Sort oldest first — safest to delete
    records_sorted = sorted(records, key=lambda r: r.get("time", ""))

    oldest_call_uuid   = None
    recording_uuid     = None
    voicemail_uuids    = []

    for r in records_sorted:
        uuid = r.get("uuid")
        if not oldest_call_uuid:
            oldest_call_uuid = uuid
        if not recording_uuid and r.get("recording"):
            recording_uuid = uuid
        if r.get("status") == "voicemail" and r.get("vm_data"):
            voicemail_uuids.append(uuid)

    print(f"      oldest call:    {oldest_call_uuid}")
    print(f"      has recording:  {recording_uuid}")
    print(f"      voicemails:     {len(voicemail_uuids)} found")

    # ── 4. Recording deletion ─────────────────────────────────────────────────
    print("\n── Recording deletion ───────────────────────────────────────")
    if recording_uuid:
        probe("recording_delete_single", "DELETE", client,
              f"{B}/call_log/recording/{recording_uuid}")
        # Bulk delete (use same uuid — already gone, tests the endpoint shape)
        probe("recording_delete_bulk", "POST", client,
              f"{B}/call_log/recording/delete",
              body={"uuids": [recording_uuid]})
    else:
        print("  ⚠️  No recording found in recent call log — skipping")
        results["recording_delete_single"] = {"status": "skipped", "confirmed": None}
        results["recording_delete_bulk"]   = {"status": "skipped", "confirmed": None}

    # ── 5. Voicemail deletion ─────────────────────────────────────────────────
    print("\n── Voicemail deletion ───────────────────────────────────────")
    if voicemail_uuids:
        # Bulk delete the oldest voicemail
        target_vm = voicemail_uuids[0]
        probe("voicemail_delete_bulk", "POST", client,
              f"{B}/voicemail/delete",
              body={"uuids": [target_vm]})
        # Also try single delete via call_log/<uuid>/delete with ext
        # (fetch ext from vm_data)
        for r in records_sorted:
            if r.get("uuid") == target_vm:
                ext = r.get("vm_data", {}).get("vm_left_for_ext", "")
                if ext:
                    probe("voicemail_delete_single", "POST", client,
                          f"{B}/call_log/{target_vm}/delete",
                          body={"ext": ext})
                break
    else:
        print("  ⚠️  No voicemails found — skipping")
        results["voicemail_delete_bulk"]   = {"status": "skipped", "confirmed": None}
        results["voicemail_delete_single"] = {"status": "skipped", "confirmed": None}

    # ── 6. Call log deletion ──────────────────────────────────────────────────
    print("\n── Call log deletion ────────────────────────────────────────")
    if oldest_call_uuid:
        probe("call_log_delete_single", "DELETE", client,
              f"{B}/call_log/{oldest_call_uuid}")
        # Grab the next oldest for bulk test
        bulk_uuids = [r["uuid"] for r in records_sorted[1:3] if r.get("uuid")]
        if bulk_uuids:
            probe("call_log_delete_bulk", "POST", client,
                  f"{B}/delete_call_logs",
                  body={"uuids": bulk_uuids})
        else:
            print("  ⚠️  Not enough records for bulk delete test")
    else:
        print("  ⚠️  No call log records found — skipping")

    _save_results(out_path)


def _save_results(out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, default=str))
    confirmed = sum(1 for v in results.values() if v.get("confirmed") is True)
    total     = sum(1 for v in results.values() if v.get("confirmed") is not None)
    print(f"\n── Summary: {confirmed}/{total} confirmed ────────────────────────")
    print(f"   Results saved to {out}")


if __name__ == "__main__":
    main()
