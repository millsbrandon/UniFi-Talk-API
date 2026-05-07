#!/usr/bin/env python3
"""
extract_endpoints.py — Scrape API endpoint strings from the UniFi Talk JS bundles.

Usage:
    python3 scripts/extract_endpoints.py --host 192.168.1.1

The Talk SPA is served from https://<host>/proxy/talk/
This script:
  1. Fetches the Talk index HTML
  2. Finds all <script src="..."> bundle URLs
  3. Downloads each bundle
  4. Regex-searches for API path strings
  5. Writes results to analysis/endpoints_from_js.txt

Pass --no-verify to skip TLS certificate verification (needed for self-signed UDM certs).
"""

import argparse
import re
import sys
import urllib.parse
from pathlib import Path

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    print("Install requests: pip3 install requests")
    sys.exit(1)

ANALYSIS_DIR = Path(__file__).parent.parent / "analysis"

# Regex patterns that look like API paths inside JS bundles
# Matches strings like "/api/v1/calls", "/proxy/talk/api/...", etc.
PATH_PATTERNS = [
    re.compile(r'["\`](/(?:proxy/talk|api)[/\w\-{}:]+)["\`]'),
    re.compile(r'["\`](/v\d+/[\w\-/{}.]+)["\`]'),
    re.compile(r'baseURL\s*[:=]\s*["\`]([^"` ]+)["\`]'),
    re.compile(r'endpoint\s*[:=]\s*["\`]([^"` ]+)["\`]'),
    re.compile(r'url\s*[:=]\s*["\`](/[^"` ]{3,})["\`]'),
]

# Filter out obviously non-API paths
IGNORE_PATTERNS = [
    re.compile(r'\.(css|js|png|jpg|svg|woff|ttf|map)$'),
    re.compile(r'^/static/'),
    re.compile(r'^/assets/'),
    re.compile(r'\$\{'),   # template literals already partially resolved — keep for review but mark
]


def fetch(session: requests.Session, url: str):  # -> str | None
    try:
        r = session.get(url, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  [WARN] Could not fetch {url}: {e}")
        return None


def find_script_urls(html: str, base_url: str) -> list[str]:
    srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
    urls = []
    for src in srcs:
        if src.startswith("http"):
            urls.append(src)
        else:
            urls.append(urllib.parse.urljoin(base_url, src))
    return urls


def extract_paths_from_js(js_text: str) -> list[str]:
    found = set()
    for pattern in PATH_PATTERNS:
        for match in pattern.finditer(js_text):
            path = match.group(1)
            # Skip if it matches ignore patterns
            if any(ig.search(path) for ig in IGNORE_PATTERNS):
                continue
            found.add(path)
    return sorted(found)


def main():
    parser = argparse.ArgumentParser(description="Extract UniFi Talk API endpoints from JS bundles")
    parser.add_argument("--host", required=True, help="UDM IP or hostname, e.g. 192.168.1.1")
    parser.add_argument("--username", "-u", help="UniFi OS username")
    parser.add_argument("--password", "-p", help="UniFi OS password")
    parser.add_argument("--no-verify", action="store_true", default=True,
                        help="Skip TLS verification (default: True for self-signed certs)")
    parser.add_argument("--talk-path", default="/proxy/talk/",
                        help="Path to the Talk web UI (default: /proxy/talk/)")
    args = parser.parse_args()

    base_url = f"https://{args.host}"
    talk_url = f"{base_url}{args.talk_path}"
    verify = not args.no_verify

    session = requests.Session()
    session.verify = verify

    # Authenticate if credentials provided
    if args.username and args.password:
        print(f"[*] Logging in as {args.username}...")
        r = session.post(
            f"{base_url}/api/auth/login",
            json={"username": args.username, "password": args.password, "rememberMe": False},
            timeout=10,
        )
        if r.status_code not in (200, 201):
            print(f"[-] Login failed: HTTP {r.status_code}")
            sys.exit(1)
        csrf = r.json().get("csrf_token") or r.headers.get("X-CSRF-Token", "")
        session.headers.update({"X-CSRF-Token": csrf})
        print(f"[+] Authenticated.")

    print(f"[*] Fetching Talk index: {talk_url}")
    html = fetch(session, talk_url)
    if not html:
        print("[-] Could not fetch Talk index page. Check --host and that Talk is installed.")
        sys.exit(1)

    script_urls = find_script_urls(html, talk_url)
    print(f"[*] Found {len(script_urls)} script tags")

    # Also try /proxy/talk/index.html explicitly
    if not script_urls:
        alt = fetch(session, f"{talk_url}index.html")
        if alt:
            script_urls = find_script_urls(alt, talk_url)

    all_paths: dict[str, list[str]] = {}  # path -> [source bundle(s)]

    for url in script_urls:
        print(f"  [*] Downloading {url}")
        js = fetch(session, url)
        if not js:
            continue

        # Cache bundle locally for manual inspection
        bundle_name = url.split("/")[-1].split("?")[0] or "bundle.js"
        cache_path = ANALYSIS_DIR / "bundles" / bundle_name
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(js, encoding="utf-8", errors="replace")

        paths = extract_paths_from_js(js)
        print(f"      → {len(paths)} potential paths")
        for p in paths:
            all_paths.setdefault(p, []).append(bundle_name)

    if not all_paths:
        print("[-] No paths found. The app may use runtime-constructed URLs — use mitmproxy capture instead.")
        sys.exit(0)

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    out = ANALYSIS_DIR / "endpoints_from_js.txt"

    with open(out, "w") as f:
        f.write(f"# Extracted from UniFi Talk JS bundles on {args.host}\n")
        f.write(f"# Total unique paths: {len(all_paths)}\n\n")
        for path in sorted(all_paths.keys()):
            sources = ", ".join(all_paths[path])
            f.write(f"{path}  # [{sources}]\n")

    print(f"\n[+] Wrote {len(all_paths)} paths to {out}")
    print(f"[+] Bundles cached in {ANALYSIS_DIR / 'bundles'}/")
    print("\nTop paths (Talk-specific):")
    for p in sorted(all_paths):
        if "talk" in p.lower() or "call" in p.lower() or "record" in p.lower():
            print(f"  {p}")


if __name__ == "__main__":
    main()
