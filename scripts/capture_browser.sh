#!/usr/bin/env bash
# =============================================================================
# capture_browser.sh — Start mitmweb + launch a dedicated Chrome proxy session
#
# Usage:
#   ./scripts/capture_browser.sh [--host 192.168.1.1] [--port 8080]
#
# What it does:
#   1. Starts mitmweb (mitmproxy with a web UI) on --port (default 8080)
#   2. Opens mitmweb's dashboard at http://127.0.0.1:<port+1>
#   3. Launches an isolated Chrome profile that proxies ALL traffic through
#      mitmweb — including the UniFi OS self-signed TLS cert, which is
#      silently accepted via --ignore-certificate-errors in the capture profile.
#
# The Chrome window that opens is a SEPARATE profile (/tmp/unifi-capture-chrome)
# and does NOT affect your normal Chrome profile.
#
# After capturing:
#   - View live traffic at http://127.0.0.1:8081  (mitmweb dashboard)
#   - Saved JSONL log: private_captures/requests.jsonl
#   - Stop everything: Ctrl-C in this terminal (mitmweb) then close Chrome
# =============================================================================
set -euo pipefail

UDM_HOST="192.168.1.1"
MITM_PORT=8080
MITM_WEB_PORT=8081
CHROME_PROFILE="/tmp/unifi-capture-chrome"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ── Parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) UDM_HOST="$2"; shift 2 ;;
    --port) MITM_PORT="$2"; MITM_WEB_PORT=$(( MITM_PORT + 1 )); shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# ── Check deps ────────────────────────────────────────────────────────────────
if ! command -v mitmweb &>/dev/null; then
  echo "ERROR: mitmweb not found. Install with: pip3 install mitmproxy"
  exit 1
fi
CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if [[ ! -x "$CHROME_BIN" ]]; then
  echo "ERROR: Google Chrome not found at $CHROME_BIN"
  exit 1
fi

# ── Ensure output dir ─────────────────────────────────────────────────────────
mkdir -p "$PROJECT_DIR/private_captures"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  UniFi Talk API Capture Session"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Proxy   : http://127.0.0.1:$MITM_PORT"
echo "  Dashboard: http://127.0.0.1:$MITM_WEB_PORT"
echo "  UDM host : $UDM_HOST"
echo "  Log file : $PROJECT_DIR/private_captures/requests.jsonl"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  ACTION PLAN for capturing mutating endpoints:"
echo "  • IVR / Ring Flows  : Settings → Ring Flows → create / edit a flow"
echo "  • Auto-Attendant     : Settings → Auto-Attendant"
echo "  • User creation      : Users → Invite / Add User"
echo "  • SIP provider setup : Settings → SIP Trunks → Add/Edit trunk"
echo "  • Ring Groups        : Settings → Ring Groups → create"
echo "  • Parking Lots       : Settings → Call Parking → create"
echo "  • Number assignment  : Users → assign DID"
echo "  • Call routing rules : Settings → Call Routing"
echo ""
echo "  Launching Chrome capture profile in 3 seconds..."
sleep 3

# ── Launch Chrome with proxy ──────────────────────────────────────────────────
# --user-data-dir         : isolated profile, no interaction with real Chrome
# --proxy-server          : route all traffic through mitmweb
# --ignore-certificate-errors : accept both UDM self-signed cert AND mitmproxy injected cert
# --disable-features=IsolateOrigins,site-per-process : avoids some proxy-break issues
# --no-first-run / --no-default-browser-check : skip Chrome setup dialogs
"$CHROME_BIN" \
  --user-data-dir="$CHROME_PROFILE" \
  --proxy-server="http://127.0.0.1:$MITM_PORT" \
  --ignore-certificate-errors \
  --no-first-run \
  --no-default-browser-check \
  --disable-features=IsolateOrigins \
  "https://$UDM_HOST/talk" \
  "http://127.0.0.1:$MITM_WEB_PORT" \
  &>/dev/null &
CHROME_PID=$!

echo "  Chrome PID: $CHROME_PID  (isolated profile: $CHROME_PROFILE)"
echo ""
echo "  Starting mitmweb... (Ctrl-C to stop)"
echo ""

# ── Start mitmweb (foreground — Ctrl-C to stop) ───────────────────────────────
# --set udm_host filters the addon's log to only UniFi traffic (everything
# still flows through the proxy; this just controls what gets written to JSONL)
mitmweb \
  --listen-port "$MITM_PORT" \
  --web-port "$MITM_WEB_PORT" \
  --web-open-browser \
  --scripts "$SCRIPT_DIR/mitm_addon.py" \
  --set "udm_host=$UDM_HOST" \
  --ssl-insecure \
  2>&1

# ── Cleanup on exit ───────────────────────────────────────────────────────────
echo ""
echo "  mitmweb stopped. Killing Chrome capture profile..."
kill "$CHROME_PID" 2>/dev/null || true
echo "  Done. Captured traffic in: $PROJECT_DIR/private_captures/requests.jsonl"
