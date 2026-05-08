"""
mitmproxy addon for capturing UniFi Talk API traffic.

Usage:
    mitmproxy -s scripts/mitm_addon.py --listen-port 8080 \
              --set udm_host=192.168.1.1

Then proxy your browser through 127.0.0.1:8080.
Install the mitmproxy CA cert by visiting http://mitm.it while proxied.

Output:
    private_captures/requests.jsonl  — newline-delimited JSON of every request/response
    Override output dir with UNIFI_CAPTURE_DIR=/path/to/dir.
"""

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from mitmproxy import ctx, http, websocket


# ── Config defaults (override with --set udm_host=X) ─────────────────────────
DEFAULT_UDM_HOST = ""          # e.g. "192.168.1.1" — filter to this host only
ROOT_DIR = Path(__file__).parent.parent
CAPTURES_DIR = Path(os.environ.get("UNIFI_CAPTURE_DIR", str(ROOT_DIR / "private_captures")))

# Paths that are almost never interesting — skip logging them
IGNORE_PATH_PREFIXES = [
    "/proxy/talk/static/",
    "/proxy/talk/assets/",
    "/proxy/network/static/",
    "/static/",
    "/favicon",
]

# ── Seen endpoint patterns for live dedup summary ────────────────────────────
_seen_patterns: set[str] = set()


def _pattern(flow: http.HTTPFlow) -> str:
    """Replace numeric segments so /calls/123 and /calls/456 share a pattern."""
    path = urlparse(flow.request.pretty_url).path
    path = re.sub(r"/\d{6,}", "/{id}", path)   # long numeric IDs
    path = re.sub(r"/[0-9a-f]{24,}", "/{id}", path)  # hex/mongo IDs
    return f"{flow.request.method} {path}"


def _is_interesting(flow: http.HTTPFlow) -> bool:
    url = flow.request.pretty_url
    path = urlparse(url).path
    host = urlparse(url).hostname or ""

    udm_host = ctx.options.udm_host if ctx.options.udm_host else DEFAULT_UDM_HOST
    if udm_host and host != udm_host:
        return False
    if any(path.startswith(p) for p in IGNORE_PATH_PREFIXES):
        return False
    return True


def _content_type(flow: http.HTTPFlow) -> str:
    return flow.response.headers.get("content-type", "") if flow.response else ""


class UniFiTalkAddon:
    def load(self, loader):
        loader.add_option(
            name="udm_host",
            typespec=str,
            default="",
            help="Only capture traffic to this UDM hostname/IP (leave blank for all)",
        )
        CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
        self._log_path = CAPTURES_DIR / "requests.jsonl"
        ctx.log.info(f"[UniFi-RE] Logging to {self._log_path}")

    def response(self, flow: http.HTTPFlow):
        if not _is_interesting(flow):
            return

        pattern = _pattern(flow)
        is_new = pattern not in _seen_patterns
        _seen_patterns.add(pattern)

        # Build record
        req = flow.request
        resp = flow.response

        # Safely decode bodies
        try:
            req_body = req.text if req.content else None
        except Exception:
            req_body = req.content.hex() if req.content else None

        resp_body = None
        if resp and resp.content:
            ct = _content_type(flow)
            if "json" in ct or "text" in ct:
                try:
                    resp_body = resp.text
                except Exception:
                    resp_body = resp.content.hex()

        record = {
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            "method": req.method,
            "url": req.pretty_url,
            "path": urlparse(req.pretty_url).path,
            "query": dict(req.query),
            "req_headers": dict(req.headers),
            "req_body": req_body,
            "status": resp.status_code if resp else None,
            "resp_content_type": _content_type(flow),
            "resp_body": resp_body,
            "resp_headers": dict(resp.headers) if resp else {},
        }

        with open(self._log_path, "a") as f:
            f.write(json.dumps(record) + "\n")

        if is_new:
            status = resp.status_code if resp else "?"
            ctx.log.info(f"[NEW] {pattern}  →  {status}")

    def websocket_message(self, flow: http.HTTPFlow):
        """Log WebSocket frames."""
        if not _is_interesting(flow):
            return

        msg = flow.websocket.messages[-1]  # most recent message
        record = {
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            "type": "websocket",
            "url": flow.request.pretty_url,
            "direction": "client→server" if msg.from_client else "server→client",
            "content": msg.text if isinstance(msg.content, str) else msg.content.hex(),
        }

        ws_log = CAPTURES_DIR / "websocket.jsonl"
        with open(ws_log, "a") as f:
            f.write(json.dumps(record) + "\n")

        direction = "→ server" if msg.from_client else "← server"
        preview = (msg.text if isinstance(msg.content, str) else "[binary]")[:120]
        ctx.log.info(f"[WS {direction}] {preview}")


addons = [UniFiTalkAddon()]
