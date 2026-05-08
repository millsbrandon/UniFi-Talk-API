#!/usr/bin/env python3
"""
api_client.py — Interactive UniFi Talk API client.

Handles authentication (with automatic re-auth on 401), and provides
convenience methods to call discovered endpoints.

Usage (interactive REPL):
    python3 scripts/api_client.py --host 192.168.1.1 --username admin --password pass

Usage (one-shot):
    python3 scripts/api_client.py --host 192.168.1.1 -u admin -p pass \
        --get /proxy/talk/api/v1/calls

The client will pretty-print JSON responses and save them to private_captures/api_responses/
Override output dir with UNIFI_CAPTURE_DIR=/path/to/dir.
"""

import argparse
import code
import json
import os
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

ROOT_DIR = Path(__file__).parent.parent
DEFAULT_SECRETS_FILE = ROOT_DIR / ".local" / "secrets.json"
CAPTURES_DIR = Path(os.environ.get("UNIFI_CAPTURE_DIR", str(ROOT_DIR / "private_captures"))) / "api_responses"


def load_secrets(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        print(f"[-] Failed to parse secrets file {path}: {exc}")
        return {}


class UniFiTalkClient:
    """
    Authenticated HTTP client for UniFi OS / Talk API.

    Example usage:
        c = UniFiTalkClient("192.168.1.1")
        c.login("admin", "password")

        # Explore:
        c.get("/proxy/talk/api/v1/calls")
        c.get("/proxy/talk/api/v1/devices")
        c.get("/proxy/talk/api/v1/recordings")
        c.get("/proxy/talk/api/v1/clients")

        # Raw request with custom headers:
        c.request("GET", "/proxy/talk/api/v1/calls", params={"limit": 50})
    """

    def __init__(self, host: str, verify_ssl: bool = False):
        self.base = f"https://{host}"
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.token: str = ""
        self.csrf: str = ""
        self._username: str = ""
        self._password: str = ""

    # ── Auth ──────────────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> bool:
        """Authenticate with UniFi OS."""
        self._username = username
        self._password = password
        url = f"{self.base}/api/auth/login"
        resp = self.session.post(
            url,
            json={"username": username, "password": password, "rememberMe": False},
            timeout=10,
        )
        if resp.status_code not in (200, 201):
            print(f"[-] Login failed: {resp.status_code} — {resp.text[:200]}")
            return False

        self.token = resp.cookies.get("TOKEN", "")
        body = resp.json()
        self.csrf = body.get("csrf_token") or resp.headers.get("X-CSRF-Token", "")
        self.session.headers.update({"X-CSRF-Token": self.csrf})
        self.session.cookies.set("TOKEN", self.token)
        print(f"[+] Logged in. CSRF: {self.csrf[:20]}...")
        return True

    def _reauth(self):
        print("[*] Re-authenticating...")
        self.login(self._username, self._password)

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base}{path}" if path.startswith("/") else path
        resp = self.session.request(method, url, timeout=15, **kwargs)
        if resp.status_code == 401 and self._username:
            self._reauth()
            resp = self.session.request(method, url, timeout=15, **kwargs)
        self._print_and_save(method, path, resp)
        return resp

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.request("DELETE", path, **kwargs)

    # ── Convenience methods for known/suspected Talk endpoints ────────────────

    def get_calls(self, limit: int = 50, offset: int = 0):
        """Attempt to retrieve call log."""
        for path in [
            f"/proxy/talk/api/v1/calls?limit={limit}&offset={offset}",
            f"/proxy/talk/api/v1/call-log?limit={limit}",
            f"/proxy/talk/api/v1/history?limit={limit}",
            f"/proxy/talk/api/v1/cdr",  # Call Detail Records
        ]:
            r = self.get(path)
            if r.status_code == 200:
                print(f"[+] Calls endpoint found: {path}")
                return r
        print("[-] No call log endpoint found yet")

    def get_recordings(self):
        """Attempt to retrieve voicemail/recordings."""
        for path in [
            "/proxy/talk/api/v1/recordings",
            "/proxy/talk/api/v1/voicemail",
            "/proxy/talk/api/v1/media",
        ]:
            r = self.get(path)
            if r.status_code == 200:
                print(f"[+] Recordings endpoint found: {path}")
                return r
        print("[-] No recordings endpoint found yet")

    def get_devices(self):
        """List Talk devices (phones)."""
        for path in [
            "/proxy/talk/api/v1/devices",
            "/proxy/talk/api/v1/phones",
            "/proxy/talk/api/v1/extensions",
        ]:
            r = self.get(path)
            if r.status_code == 200:
                print(f"[+] Devices endpoint found: {path}")
                return r

    def enumerate(self, base_path: str = "/proxy/talk/api/v1"):
        """
        Brute-force common resource names under a base path.
        Useful for discovering available endpoints.
        """
        candidates = [
            "calls", "call-log", "cdr", "history",
            "recordings", "voicemail", "media",
            "devices", "phones", "extensions", "lines",
            "contacts", "directory",
            "clients", "users",
            "settings", "config",
            "status", "info", "health",
            "events", "alerts",
            "numbers", "did",
        ]
        found = []
        print(f"[*] Enumerating {base_path}/...")
        for name in candidates:
            path = f"{base_path}/{name}"
            try:
                r = self.session.get(f"{self.base}{path}", timeout=5)
                status = r.status_code
                icon = "✅" if status == 200 else ("🔐" if status in (401, 403) else "❌")
                size = len(r.content)
                print(f"  {icon} {path}  →  {status}  ({size} bytes)")
                if status in (200, 401, 403):
                    found.append((path, status, size))
            except Exception as e:
                print(f"  ?? {path}  →  error: {e}")
        print(f"\n[+] {len(found)} interesting paths found")
        return found

    # ── Output ────────────────────────────────────────────────────────────────

    def _print_and_save(self, method: str, path: str, resp: requests.Response):
        ct = resp.headers.get("content-type", "")
        ts = datetime.now(tz=timezone.utc).isoformat()

        print(f"\n{method} {path}  →  HTTP {resp.status_code}  ({len(resp.content)} bytes)")

        body_text = None
        if "json" in ct:
            try:
                body_text = json.dumps(resp.json(), indent=2)
                preview = body_text[:3000]
                print(preview)
                if len(body_text) > 3000:
                    print(f"  ... [{len(body_text) - 3000} more chars]")
            except Exception:
                body_text = resp.text
                print(body_text[:1000])
        elif "text" in ct:
            body_text = resp.text
            print(body_text[:1000])

        # Save to captures
        CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
        safe_path = path.replace("/", "_").strip("_")
        filename = f"{ts[:19].replace(':', '-')}_{method}_{safe_path[:60]}.json"
        record = {
            "ts": ts,
            "method": method,
            "url": resp.url,
            "status": resp.status_code,
            "resp_headers": dict(resp.headers),
            "body": body_text,
        }
        (CAPTURES_DIR / filename).write_text(json.dumps(record, indent=2))


def main():
    parser = argparse.ArgumentParser(description="UniFi Talk API client")
    parser.add_argument("--host")
    parser.add_argument("--username", "-u")
    parser.add_argument("--password", "-p")
    parser.add_argument("--token", help="Existing TOKEN cookie")
    parser.add_argument("--get", metavar="PATH", help="One-shot GET request")
    parser.add_argument("--enumerate", action="store_true", help="Enumerate common endpoints")
    parser.add_argument("--repl", action="store_true", default=True, help="Start interactive REPL")
    parser.add_argument(
        "--secrets",
        default=str(DEFAULT_SECRETS_FILE),
        help="Path to local secrets JSON (default: .local/secrets.json)",
    )
    args = parser.parse_args()

    secrets = load_secrets(Path(args.secrets))
    host = args.host or secrets.get("host", "")
    username = args.username or secrets.get("username", "")
    password = args.password or secrets.get("password", "")
    token = args.token or secrets.get("token", "")

    if not host:
        parser.error("Provide --host or set host in --secrets file")

    client = UniFiTalkClient(host)

    if token:
        client.token = token
        client.session.cookies.set("TOKEN", token)
    elif username and password:
        if not client.login(username, password):
            sys.exit(1)
    else:
        parser.error("Provide token or username/password via args or --secrets file")

    if args.get:
        client.get(args.get)
        return

    if args.enumerate:
        client.enumerate()
        return

    # Drop into interactive REPL with `client` in scope
    print("\n[+] UniFi Talk API client ready.")
    print("    Variable 'c' is your authenticated client.")
    print("    Try: c.enumerate()  |  c.get_calls()  |  c.get('/proxy/talk/api/v1/...')\n")
    code.interact(local={"c": client, "client": client}, banner="")


if __name__ == "__main__":
    main()
