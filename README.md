# UniFi Talk — Reverse Engineering Project

Target: UniFi Talk on UDM/UDM-Pro (local controller, browser web UI)
Goal: Discover undocumented REST/WebSocket API for caller ID, recordings, call logs, etc.

---

## Architecture Overview

UniFi OS routes all application traffic through a reverse proxy on the console itself.
UniFi Talk lives at:

```
https://<UDM-IP>/proxy/talk/
```

Authentication is shared with UniFi OS — a session cookie (`TOKEN`) and CSRF token
(`X-CSRF-Token` header) are required for most requests.

### Known UniFi OS Auth Flow

```
POST https://<UDM-IP>/api/auth/login
  Body: { "username": "...", "password": "..." }
  Response: sets TOKEN cookie, returns csrf_token in body
```

All subsequent requests need:
- `Cookie: TOKEN=<value>`
- `X-CSRF-Token: <csrf_token>`

---

## Methodology

### Phase 1 — Traffic Interception (mitmproxy)

1. Install mitmproxy: `brew install mitmproxy`
2. Run the addon: `mitmproxy -s scripts/mitm_addon.py --listen-port 8080`
3. Configure your browser to use `127.0.0.1:8080` as an HTTP/HTTPS proxy
4. Install the mitmproxy CA cert in your browser (visit http://mitm.it)
5. Navigate to UniFi Talk in the browser — all requests are logged to `captures/`

The addon (`scripts/mitm_addon.py`) will:
- Filter only requests to your UDM IP
- Log request/response pairs as JSON to `captures/requests.jsonl`
- Print a live summary of new endpoint patterns

### Phase 2 — JS Bundle Analysis

The web UI is a Single Page Application (React/Vue). All API calls are compiled into
JS bundles served from the device. Extracting endpoints from the bundle is fast:

```bash
python3 scripts/extract_endpoints.py --host <UDM-IP>
```

This script:
1. Fetches the Talk SPA HTML page
2. Finds all `<script src="...">` bundle URLs
3. Downloads each bundle and regex-searches for API path strings
4. Writes discovered paths to `analysis/endpoints_from_js.txt`

### Phase 3 — WebSocket Analysis

UniFi Talk uses WebSockets for real-time events (incoming calls, status updates).
The mitmproxy addon captures WS frames too. Separately, you can use:

```bash
python3 scripts/ws_monitor.py --host <UDM-IP> --token <TOKEN>
```

Known WS endpoint (confirmed):
```
wss://<UDM-IP>/proxy/talk/ws
```

### Phase 4 — Document & Test

- Document discovered endpoints in `docs/endpoints/`
- Use `scripts/api_client.py` to test them interactively

---

## Directory Layout

```
unifi-talk-re/
├── README.md               — this file
├── scripts/
│   ├── mitm_addon.py       — mitmproxy addon for traffic capture
│   ├── extract_endpoints.py— JS bundle scraper
│   ├── ws_monitor.py       — WebSocket monitor
│   └── api_client.py       — interactive API client
├── captures/
│   └── requests.jsonl      — captured HTTP traffic (git-ignored)
├── analysis/
│   └── endpoints_from_js.txt
└── docs/
    └── endpoints/
        ├── auth.md
        ├── calls.md
        ├── recordings.md
        └── devices.md
```

---

## Confirmed Endpoints

See `docs/endpoints/` for detailed notes, or `docs/UNIFI_TALK_UNOFFICIAL_API.md` for the full reference. Quick reference:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | UniFi OS login |
| POST | `/api/auth/logout` | Invalidate session |
| GET | `/proxy/talk/api/info` | Talk version, features |
| GET | `/proxy/talk/api/call_log` | Paginated call history |
| GET | `/proxy/talk/api/call_log/csv` | Export call log as CSV |
| GET | `/proxy/talk/api/call_log/recording/<uuid>` | Download call recording (MP3) |
| GET | `/proxy/talk/api/call_log/audio_data/<uuid>` | Waveform peaks data |
| GET | `/proxy/talk/api/call_log/flow/<uuid>` | Full call routing timeline |
| GET | `/proxy/talk/api/devices` | All adopted Talk devices |
| GET | `/proxy/talk/api/users` | All Talk users |
| GET | `/proxy/talk/api/number/list` | All configured DIDs |
| GET | `/proxy/talk/api/sms/conversations` | SMS threads |
| GET | `/proxy/talk/api/setting/config` | System configuration |
| GET | `/proxy/talk/api/third_party_sip/gateway_list` | SIP trunk/gateway list |
| GET | `/proxy/talk/api/debug/pcap/status` | Packet capture status |
| WS | `wss://<UDM-IP>/proxy/talk/ws` | Real-time events (calls, devices) |

All 56 confirmed endpoints are listed in the [full API reference](docs/UNIFI_TALK_UNOFFICIAL_API.md).

---

## Tips & Gotchas

- **Self-signed cert**: UDM uses a self-signed cert by default. mitmproxy handles this
  automatically. If you've installed a real cert on the UDM, mitmproxy still works fine.
- **Token expiry**: The `TOKEN` cookie expires after ~1 hour of inactivity. The api_client
  script handles re-authentication automatically.
- **UniFi OS proxy prefix**: Unlike older UCK setups, all Talk traffic goes through
  `/proxy/talk/` — bare paths like `/api/...` will 404 from within Talk context.
- **CSRF**: Every mutating request (POST/PUT/DELETE) needs `X-CSRF-Token`. GET requests
  to the API may work with just the cookie.
- **Rate limiting**: UniFi OS has rate limiting on `/api/auth/login`. Don't hammer it.
