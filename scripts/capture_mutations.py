#!/usr/bin/env python3
"""
capture_mutations.py — Targeted mitmproxy addon for capturing Talk UI mutation
traffic: smart attendant, ring groups, settings, SMS, and outbound calls.

Usage:
    mitmdump -s scripts/capture_mutations.py --listen-port 8080 \
             --set udm_host=192.168.1.1

Then set your browser proxy to 127.0.0.1:8080 and perform UI actions in Talk.

Captured endpoints are printed live and saved to:
    private_captures/ui_mutations.jsonl   — full request/response records
    private_captures/ui_mutations_summary.txt — one-line summary per new endpoint
Override output dir with UNIFI_CAPTURE_DIR=/path/to/dir.
"""

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from mitmproxy import ctx, http

ROOT_DIR = Path(__file__).parent.parent
CAPTURES_DIR = Path(os.environ.get("UNIFI_CAPTURE_DIR", str(ROOT_DIR / "private_captures")))
DEFAULT_UDM_HOST = "192.168.1.1"

# Only log Talk API paths (skip static assets, network app, etc.)
TALK_API_PREFIX = "/proxy/talk/api"

# Paths we already know — only alert if new
KNOWN_GET_ENDPOINTS = {
    "/proxy/talk/api/info",
    "/proxy/talk/api/call_log",
    "/proxy/talk/api/call_log/countries",
    "/proxy/talk/api/call_recording_rule",
    "/proxy/talk/api/dashboard/consolidated_info",
    "/proxy/talk/api/dashboard/most_active_users",
    "/proxy/talk/api/devices",
    "/proxy/talk/api/device/24h_call_quality",
    "/proxy/talk/api/users",
    "/proxy/talk/api/user/info",
    "/proxy/talk/api/number/list",
    "/proxy/talk/api/number/blocked",
    "/proxy/talk/api/contact_list",
    "/proxy/talk/api/contacts",
    "/proxy/talk/api/emergency_address/list",
    "/proxy/talk/api/group_list",
    "/proxy/talk/api/ring_flow",
    "/proxy/talk/api/parking_lots",
    "/proxy/talk/api/switchboard",
    "/proxy/talk/api/phone_designer",
    "/proxy/talk/api/sms/conversations",
    "/proxy/talk/api/setting/config",
    "/proxy/talk/api/setting/emergency_status",
    "/proxy/talk/api/setting/default_area_code",
    "/proxy/talk/api/setting/dialing_country",
    "/proxy/talk/api/setting/hold_music",
    "/proxy/talk/api/setting/ringtones",
    "/proxy/talk/api/third_party_sip/gateway_list",
    "/proxy/talk/api/billing/coupons/balance",
    "/proxy/talk/api/identity/status",
    "/proxy/talk/api/regulatory/bundle",
    "/proxy/talk/api/lock/usage",
    "/proxy/talk/api/debug/pcap/status",
    "/proxy/talk/api/peer_consoles",
    "/proxy/talk/api/applications",
    "/proxy/talk/api/install",
    "/proxy/talk/api/setup_complete",
    "/proxy/talk/api/updates",
    "/proxy/talk/api/ucore/system_info",
    "/proxy/talk/api/protect/cameras",
    "/proxy/talk/api/call_center/queue",
    "/proxy/talk/api/number_porting/list",
    "/proxy/talk/api/number_porting/request_count",
    "/proxy/talk/api/owner_transfer/transfer_state",
    "/proxy/talk/api/drive/status",
    "/proxy/talk/api/info/app_owner",
    "/proxy/talk/api/phone_designer/wallpaper/list",
}

# Target mutations we're hunting — highlight these
TARGETS = [
    # Smart attendant
    "smart_attendant",
    "ivr",
    # Ring groups
    "ring_group",
    "group",
    # Settings mutations
    "setting",
    # SMS
    "sms",
    "message",
    # Calls
    "call/initiate",
    "call/start",
    "dial",
    "outbound",
    # Number / user management
    "number",
    "user",
]

_seen: set[str] = set()


def _normalize_path(path: str) -> str:
    """Replace UUIDs and numeric IDs with placeholders for dedup."""
    path = re.sub(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "/<uuid>", path)
    path = re.sub(r"/\d{4,}", "/<id>", path)
    return path


def _is_target(method: str, path: str) -> bool:
    if method == "GET" and _normalize_path(path) in KNOWN_GET_ENDPOINTS:
        return False  # already documented
    if not path.startswith(TALK_API_PREFIX):
        return False
    return True


class MutationCapture:
    def load(self, loader):
        loader.add_option(
            name="udm_host",
            typespec=str,
            default=DEFAULT_UDM_HOST,
            help="UDM IP to filter traffic to",
        )
        loader.add_option(
            name="scenario",
            typespec=str,
            default="",
            help="Optional run label (example: outbound-call-test)",
        )
        CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
        self._jsonl = CAPTURES_DIR / "ui_mutations.jsonl"
        self._summary = CAPTURES_DIR / "ui_mutations_summary.txt"
        ctx.log.info(f"[MutationCapture] Watching for Talk API mutations on {DEFAULT_UDM_HOST}")
        ctx.log.info(f"[MutationCapture] Output: {self._jsonl}")
        ctx.log.info("[MutationCapture] Set your browser proxy to 127.0.0.1:8080")
        ctx.log.info("[MutationCapture] Then perform UI actions in UniFi Talk")

    def response(self, flow: http.HTTPFlow):
        req = flow.request
        resp = flow.response

        host = urlparse(req.pretty_url).hostname or ""
        udm_host = ctx.options.udm_host or DEFAULT_UDM_HOST
        if host != udm_host:
            return

        path = urlparse(req.pretty_url).path
        if not _is_target(req.method, path):
            return

        # Decode bodies
        try:
            req_body_raw = req.text if req.content else None
        except Exception:
            req_body_raw = None
        try:
            req_body = json.loads(req_body_raw) if req_body_raw else None
        except Exception:
            req_body = req_body_raw

        resp_body_raw = None
        if resp and resp.content:
            ct = resp.headers.get("content-type", "")
            if "json" in ct or "text" in ct:
                try:
                    resp_body_raw = resp.text
                except Exception:
                    pass
        try:
            resp_body = json.loads(resp_body_raw) if resp_body_raw else None
        except Exception:
            resp_body = resp_body_raw

        record = {
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            "scenario": ctx.options.scenario,
            "method": req.method,
            "path": path,
            "query": dict(req.query),
            "req_body": req_body,
            "status": resp.status_code if resp else None,
            "resp_body": resp_body,
        }

        # Save full record
        with open(self._jsonl, "a") as f:
            f.write(json.dumps(record) + "\n")

        # Dedup key for summary
        norm = f"{req.method} {_normalize_path(path)}"
        is_new = norm not in _seen
        _seen.add(norm)

        # Is it one of our targets?
        is_target = any(t in path.lower() for t in TARGETS) or req.method != "GET"

        status = resp.status_code if resp else "?"
        flag = "🎯 NEW" if is_new and is_target else ("NEW" if is_new else "   ")

        line = f"{flag}  {req.method:6} {path}  →  {status}"
        if req_body and req.method != "GET":
            body_preview = json.dumps(req_body)[:120] if isinstance(req_body, dict) else str(req_body)[:120]
            line += f"\n       body: {body_preview}"
        if resp_body and status not in (200, 201, 204):
            resp_preview = json.dumps(resp_body)[:120] if isinstance(resp_body, dict) else str(resp_body)[:120]
            line += f"\n       resp: {resp_preview}"

        ctx.log.info(f"[Talk] {line}")

        if is_new:
            with open(self._summary, "a") as f:
                f.write(f"{datetime.now(tz=timezone.utc).isoformat()}  {req.method:6} {path}  {status}\n")
                if req_body and req.method != "GET":
                    f.write(f"  body: {json.dumps(req_body, indent=2)}\n")
                f.write("\n")

    def websocket_message(self, flow: http.HTTPFlow):
        host = urlparse(flow.request.pretty_url).hostname or ""
        udm_host = ctx.options.udm_host or DEFAULT_UDM_HOST
        if host != udm_host:
            return
        msg = flow.websocket.messages[-1]
        if msg.from_client:
            try:
                text = msg.text if isinstance(msg.content, str) else msg.content.decode("utf-8", errors="replace")
                ctx.log.info(f"[WS CLIENT→SERVER] {text[:200]}")
                record = {
                    "ts": datetime.now(tz=timezone.utc).isoformat(),
                    "scenario": ctx.options.scenario,
                    "type": "ws_client_to_server",
                    "content": text,
                }
                with open(self._jsonl, "a") as f:
                    f.write(json.dumps(record) + "\n")
            except Exception:
                pass


addons = [MutationCapture()]
