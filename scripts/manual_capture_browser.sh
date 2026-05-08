#!/usr/bin/env bash
# =============================================================================
# manual_capture_browser.sh — Launch Chrome for manual UI driving and capture
# UniFi Talk API traffic via Chrome DevTools Protocol (no proxy / no mitm).
#
# Usage:
#   ./scripts/manual_capture_browser.sh [--host 192.168.1.1] [--port 9222]
#
# What it does:
#   1. Launches an isolated Chrome profile with remote debugging enabled
#   2. Opens the Talk UI with TLS errors ignored for the self-signed UDM cert
#   3. Runs scripts/cdp_capture.py in the foreground to log HTTP + WS traffic
#
# Output:
#   private_captures/cdp_requests.jsonl
#   private_captures/cdp_websocket.jsonl
# =============================================================================
set -euo pipefail

UDM_HOST="192.168.1.1"
DEBUG_PORT=9222
CHROME_PROFILE="/tmp/unifi-talk-manual-capture"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) UDM_HOST="$2"; shift 2 ;;
    --port) DEBUG_PORT="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [[ ! -x "$CHROME_BIN" ]]; then
  echo "ERROR: Google Chrome not found at $CHROME_BIN"
  exit 1
fi

mkdir -p "$PROJECT_DIR/private_captures"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  UniFi Talk Manual Capture (No Proxy)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  UDM host    : $UDM_HOST"
echo "  Debug port  : $DEBUG_PORT"
echo "  Chrome prof : $CHROME_PROFILE"
echo "  HTTP log    : $PROJECT_DIR/private_captures/cdp_requests.jsonl"
echo "  WS log      : $PROJECT_DIR/private_captures/cdp_websocket.jsonl"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Drive the Chrome window yourself once it opens."
echo "Suggested targets: IVR, user creation, SIP trunk setup, ring groups, parking lots."
echo

"$CHROME_BIN" \
  --user-data-dir="$CHROME_PROFILE" \
  --remote-debugging-port="$DEBUG_PORT" \
  --remote-allow-origins="http://127.0.0.1:$DEBUG_PORT" \
  --ignore-certificate-errors \
  --no-first-run \
  --no-default-browser-check \
  "https://$UDM_HOST/talk" \
  &>/dev/null &

CHROME_PID=$!

cleanup() {
  echo
  echo "Capture stopped. Chrome is still running in its isolated profile."
  echo "Analyze with: python3 scripts/analyze_captures.py --input private_captures/cdp_requests.jsonl"
}
trap cleanup EXIT

sleep 2
python3 "$SCRIPT_DIR/cdp_capture.py" --host "$UDM_HOST" --port "$DEBUG_PORT"