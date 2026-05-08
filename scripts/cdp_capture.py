#!/usr/bin/env python3
"""
cdp_capture.py — Capture UniFi Talk traffic from a Chrome tab via the
Chrome DevTools Protocol (CDP), without using a proxy.

This is intended for manual UI exploration on macOS when mitmproxy is flaky.
You control the Chrome window yourself; this script attaches to the tab and logs:
  - HTTP requests/responses for Talk API and auth endpoints
  - WebSocket frames for UniFi Talk real-time events

Usage:
    python3 scripts/cdp_capture.py --host 192.168.1.1
    python3 scripts/cdp_capture.py --host 192.168.1.1 --port 9222 --verbose

Expected browser launch:
    /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
      --user-data-dir=/tmp/unifi-talk-manual-capture \
      --remote-debugging-port=9222 \
      --ignore-certificate-errors \
      https://192.168.1.1/talk
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlparse

import requests
import websocket
from websocket import WebSocketConnectionClosedException, WebSocketTimeoutException


ROOT_DIR = Path(__file__).parent.parent
CAPTURES_DIR = Path(os.environ.get("UNIFI_CAPTURE_DIR", str(ROOT_DIR / "private_captures")))
DEFAULT_HTTP_LOG = CAPTURES_DIR / "cdp_requests.jsonl"
DEFAULT_WS_LOG = CAPTURES_DIR / "cdp_websocket.jsonl"


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=True)


class CDPCapture:
    def __init__(self, ws_url: str, host: str, debug_port: int, http_log: Path, ws_log: Path, verbose: bool = False):
        self.ws_url = ws_url
        self.host = host
        self.debug_port = debug_port
        self.http_log = http_log
        self.ws_log = ws_log
        self.verbose = verbose
        self.ws: websocket.WebSocket | None = None
        self.next_id = 1
        self.running = True
        self.requests: dict[str, dict[str, Any]] = {}
        self.seen_patterns: set[str] = set()

    def log(self, msg: str) -> None:
        print(msg, flush=True)

    def connect(self) -> None:
        self.ws = websocket.create_connection(self.ws_url, timeout=5, suppress_origin=True)
        self.send_cmd("Network.enable")
        self.send_cmd("Page.enable")

    def reconnect(self) -> bool:
        try:
            new_ws_url = find_tab(self.debug_port, self.host)
            if self.ws:
                try:
                    self.ws.close()
                except Exception:
                    pass
            self.ws_url = new_ws_url
            self.connect()
            self.log(f"CDP reattached: {self.ws_url}")
            return True
        except Exception as exc:
            self.log(f"CDP reconnect failed: {exc}")
            return False

    def send_cmd(self, method: str, params: dict[str, Any] | None = None, timeout: float = 5.0) -> dict[str, Any] | None:
        if not self.ws:
            raise RuntimeError("CDP socket not connected")
        msg_id = self.next_id
        self.next_id += 1
        self.ws.send(_json_dumps({"id": msg_id, "method": method, "params": params or {}}))

        deadline = time.time() + timeout
        while time.time() < deadline and self.running:
            try:
                raw = self.ws.recv()
            except WebSocketTimeoutException:
                continue
            payload = json.loads(raw)
            if "id" in payload and payload["id"] == msg_id:
                return payload
            if "method" in payload:
                self.handle_event(payload)
        return None

    def write_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        with open(path, "a") as handle:
            handle.write(_json_dumps(record) + "\n")

    def interesting_url(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.hostname != self.host:
            return False
        path = parsed.path
        return (
            path.startswith("/proxy/talk/api")
            or path.startswith("/api/auth")
            or path.startswith("/proxy/talk/ws")
        )

    def request_pattern(self, request: dict[str, Any]) -> str:
        path = request.get("path", "")
        return f"{request.get('method', '?')} {path}"

    def maybe_print_summary(self, request: dict[str, Any]) -> None:
        pattern = self.request_pattern(request)
        is_new = pattern not in self.seen_patterns
        self.seen_patterns.add(pattern)
        if is_new:
            self.log(f"[NEW] {request.get('method')} {request.get('path')} -> {request.get('status')}")
        elif self.verbose and request.get("status") not in (200, 204):
            self.log(f"[HTTP] {request.get('method')} {request.get('path')} -> {request.get('status')}")

    def handle_request_will_be_sent(self, params: dict[str, Any]) -> None:
        request = params.get("request", {})
        url = request.get("url", "")
        if not self.interesting_url(url):
            return
        parsed = urlparse(url)
        self.requests[params["requestId"]] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "method": request.get("method"),
            "url": url,
            "path": parsed.path,
            "query": dict(parse_qsl(parsed.query, keep_blank_values=True)),
            "req_headers": request.get("headers", {}),
            "req_body": request.get("postData"),
            "status": None,
            "resp_content_type": None,
            "resp_headers": {},
            "resp_body": None,
            "resource_type": params.get("type"),
        }

    def handle_response_received(self, params: dict[str, Any]) -> None:
        req = self.requests.get(params.get("requestId"))
        if not req:
            return
        response = params.get("response", {})
        req["status"] = response.get("status")
        req["resp_content_type"] = response.get("mimeType")
        req["resp_headers"] = response.get("headers", {})

    def handle_loading_finished(self, params: dict[str, Any]) -> None:
        req_id = params.get("requestId")
        req = self.requests.get(req_id)
        if not req:
            return

        body_text = None
        try:
            body_resp = self.send_cmd("Network.getResponseBody", {"requestId": req_id}, timeout=1.5)
        except WebSocketConnectionClosedException:
            body_resp = None
        if body_resp and "result" in body_resp:
            body_text = body_resp["result"].get("body")
            if body_resp["result"].get("base64Encoded") and body_text is not None:
                try:
                    body_text = base64.b64decode(body_text).decode("utf-8", errors="replace")
                except Exception:
                    pass

        if body_text:
            content_type = (req.get("resp_content_type") or "").lower()
            if "json" in content_type:
                try:
                    req["resp_body"] = json.loads(body_text)
                except Exception:
                    req["resp_body"] = body_text[:5000]
            elif "text" in content_type or "javascript" in content_type or "html" in content_type:
                req["resp_body"] = body_text[:5000]

        self.write_jsonl(self.http_log, req)
        self.maybe_print_summary(req)
        self.requests.pop(req_id, None)

    def handle_ws_frame(self, direction: str, params: dict[str, Any]) -> None:
        response = params.get("response", {})
        payload = response.get("payloadData", "")
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "type": "websocket",
            "url": params.get("requestId", ""),
            "direction": direction,
            "content": payload,
        }
        self.write_jsonl(self.ws_log, record)
        if self.verbose:
            self.log(f"[WS {direction}] {payload[:160]}")

    def handle_event(self, payload: dict[str, Any]) -> None:
        method = payload.get("method")
        params = payload.get("params", {})
        if method == "Network.requestWillBeSent":
            self.handle_request_will_be_sent(params)
        elif method == "Network.responseReceived":
            self.handle_response_received(params)
        elif method == "Network.loadingFinished":
            self.handle_loading_finished(params)
        elif method == "Network.webSocketFrameReceived":
            self.handle_ws_frame("server->client", params)
        elif method == "Network.webSocketFrameSent":
            self.handle_ws_frame("client->server", params)

    def run(self) -> int:
        CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
        self.connect()

        self.log(f"CDP attached: {self.ws_url}")
        self.log(f"HTTP log: {self.http_log}")
        self.log(f"WS log:   {self.ws_log}")
        self.log("Drive the Chrome window manually. Press Ctrl-C here when finished.")

        try:
            while self.running:
                try:
                    raw = self.ws.recv()
                except WebSocketTimeoutException:
                    continue
                except WebSocketConnectionClosedException:
                    if not self.running:
                        break
                    if not self.reconnect():
                        time.sleep(1)
                    continue
                payload = json.loads(raw)
                if "method" in payload:
                    self.handle_event(payload)
        except KeyboardInterrupt:
            self.running = False
            self.log("Stopping capture...")
        finally:
            try:
                self.ws.close()
            except Exception:
                pass
        return 0


def find_tab(debug_port: int, host: str) -> str:
    base = f"http://127.0.0.1:{debug_port}"
    pages = requests.get(f"{base}/json", timeout=3).json()
    for page in pages:
        if page.get("type") != "page":
            continue
        url = page.get("url", "")
        if host in url:
            return page["webSocketDebuggerUrl"]
    for page in pages:
        if page.get("type") == "page" and page.get("webSocketDebuggerUrl"):
            return page["webSocketDebuggerUrl"]
    raise RuntimeError(f"No debuggable Chrome page found on port {debug_port}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture UniFi Talk browser traffic via Chrome DevTools Protocol")
    parser.add_argument("--host", default="192.168.1.1", help="UDM host/IP to match")
    parser.add_argument("--port", type=int, default=9222, help="Chrome remote debugging port")
    parser.add_argument("--http-log", default=str(DEFAULT_HTTP_LOG), help="Output JSONL for HTTP traffic")
    parser.add_argument("--ws-log", default=str(DEFAULT_WS_LOG), help="Output JSONL for WebSocket traffic")
    parser.add_argument("--verbose", action="store_true", help="Print more HTTP/WS events while capturing")
    args = parser.parse_args()

    try:
        ws_url = find_tab(args.port, args.host)
    except Exception as exc:
        print(f"Failed to find Chrome debugging target: {exc}", file=sys.stderr)
        print(
            "Launch Chrome with: --remote-debugging-port=9222 --ignore-certificate-errors https://<UDM-IP>/talk",
            file=sys.stderr,
        )
        return 1

    capture = CDPCapture(
        ws_url=ws_url,
        host=args.host,
        debug_port=args.port,
        http_log=Path(args.http_log),
        ws_log=Path(args.ws_log),
        verbose=args.verbose,
    )
    return capture.run()


if __name__ == "__main__":
    sys.exit(main())