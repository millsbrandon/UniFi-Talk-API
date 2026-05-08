# UniFi Talk Unofficial API Reference

**Reverse-engineered against UniFi Talk v5.1.2 on UDM-Pro**  
**Last updated**: 2026-05-08  
**Status legend**: ✅ Confirmed live | ⏳ Candidate (not yet live-tested) | ❌ Does not exist

---

## Base URLs

| Component | URL |
|---|---|
| UniFi OS Auth | `https://<UDM-IP>/api/auth` |
| Talk API | `https://<UDM-IP>/proxy/talk/api` |
| WebSocket | `wss://<UDM-IP>/proxy/talk/ws` |

The UDM-Pro uses a self-signed TLS certificate on LAN. Set `verify=False` in Python requests or pass `-k` to curl.

---

## Authentication Summary

All Talk API requests require two headers:

```http
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf-uuid>
```

Obtain them via `POST /api/auth/login`. The CSRF token is in the `x-updated-csrf-token` **response header** (not the body). See [auth.md](endpoints/auth.md) for full details.

---

## Complete Endpoint Index

### Full-Capture Addendum

The full browser capture review (2026-05-08) identified additional endpoints that were previously undocumented in this reference. For endpoint-by-endpoint usage details (method, required parameters, auth, and example requests/responses), see:

- [Capture Gap-Fill Endpoint Guide](endpoints/capture_gap_fill.md)

### Authentication & Identity

| Method | Path | Status | Description |
|---|---|---|---|
| `POST` | `/api/auth/login` | ✅ | Login; returns TOKEN cookie + CSRF token in header |
| `POST` | `/api/auth/logout` | ✅ | Logout; invalidates session |
| `GET` | `/proxy/talk/api/user/info` | ✅ | Current user's Talk role and permissions |

### System Information

| Method | Path | Status | Description |
|---|---|---|---|
| `GET` | `/proxy/talk/api/info` | ✅ | Talk version, region, feature flags, system identity |
| `GET` | `/proxy/talk/api/install` | ✅ | Talk installation/onboarding status |
| `GET` | `/proxy/talk/api/ucore/system_info` | ✅ | UniFi OS core system information |
| `GET` | `/proxy/talk/api/dashboard/consolidated_info` | ✅ | Dashboard summary (console name, gateway IP, startup time) |
| `GET` | `/proxy/talk/api/dashboard/service_health` | ✅ | Time-series Talk service health data and monitoring events |
| `GET` | `/proxy/talk/api/peer_consoles` | ✅ | Peer UniFi consoles on the network |
| `GET` | `/proxy/talk/api/applications` | ✅ | Installed application configurations |

### Call Logs

| Method | Path | Status | Description |
|---|---|---|---|
| `GET` | `/proxy/talk/api/call_log?page=1` | ✅ | Paginated call history with full caller ID, direction, status, voicemail data |
| `GET` | `/proxy/talk/api/call_log/countries` | ✅ | Countries represented in call log |
| `GET` | `/proxy/talk/api/call_recording_rule` | ✅ | Call recording rule configurations |
| `PUT` | `/proxy/talk/api/call_recording_rule/{id}` | ✅ | Update a call recording rule |
| `GET` | `/proxy/talk/api/call_recording_rule/audio/{id}` | ✅ | Download the recording announcement audio for a rule |
| `GET` | `/proxy/talk/api/call_center/queue` | ✅ | Active call center queue |
| `GET` | `/proxy/talk/api/stats/calls/series` | ✅ | Time-series inbound/outbound call counts and answered aggregates |
| `GET` | `/proxy/talk/api/call_log/csv?page=1&items_per_page=50` | ✅ | Call log as CSV export |
| `GET` | `/proxy/talk/api/call_log/flow/<uuid>` | ✅ | Full event timeline for a specific call |
| `GET` | `/proxy/talk/api/call_log/transcription/<uuid>` | ✅ | AI transcription for a call (null if not enabled) |
| `DELETE` | `/proxy/talk/api/call_log/<uuid>` | ⏳ | Delete a single call log record |
| `POST` | `/proxy/talk/api/delete_call_logs` | ⏳ | Bulk delete call log records `{uuids:[...]}` |

### Call Recordings

| Method | Path | Status | Description |
|---|---|---|---|
| `GET` | `/proxy/talk/api/call_log/recording/<uuid>` | ✅ | Download call recording as `audio/mpeg` |
| `GET` | `/proxy/talk/api/call_log/audio_data/<uuid>` | ✅ | Waveform peaks data (for UI waveform player) |
| `DELETE` | `/proxy/talk/api/call_log/recording/<uuid>` | ⏳ | Delete recording file for a call |
| `POST` | `/proxy/talk/api/call_log/recording/delete` | ⏳ | Bulk delete recordings `{uuids:[...]}` |

### Voicemail & Recordings

| Method | Path | Status | Description |
|---|---|---|---|
| `GET` | `/proxy/talk/api/voicemail/data/<uuid>` | ✅ | Voicemail metadata by UUID |
| `GET` | `/proxy/talk/api/setting/voicemail_greeting_file` | ✅ | Global voicemail greeting (raw MP3 binary) |
| `GET` | `/proxy/talk/api/setting/hold_music` | ✅ | Hold music track list |
| `GET` | `/proxy/talk/api/setting/ringtones` | ✅ | Available ringtone options |
| `POST` | `/proxy/talk/api/call_log/<uuid>/delete` | ⏳ | Delete voicemail for an extension `{ext:"0002"}` |
| `POST` | `/proxy/talk/api/voicemail/delete` | ⏳ | Bulk delete voicemails `{uuids:[...]}` |
| `GET` | `/proxy/talk/api/exports/audio_data_archive` | ⏳ | Bulk audio export download (500 when no export queued) |

> **Voicemail audio download**: No HTTP API exists. The `voicemail/data/<uuid>` endpoint returns `file_path` pointing to the MP3 on the UDM filesystem (`/srv/unifi-talk/voicemail/talk.com/<ext>/<filename>.mp3`). Retrieve via SSH/SCP.

### Devices

| Method | Path | Status | Description |
|---|---|---|---|
| `GET` | `/proxy/talk/api/devices` | ✅ | All adopted Talk hardware devices (phones, ATAs) |
| `GET` | `/proxy/talk/api/uids/softphone` | ✅ | Softphone UID availability, assigned UIDs, and region support |
| `PUT` | `/proxy/talk/api/device/third_party` | ✅ | Create a new third-party SIP device and assign it to a user |
| `PUT` | `/proxy/talk/api/device/third_party/{uuid}` | ✅ | Update an existing third-party SIP device |

### Users & Phone Numbers

| Method | Path | Status | Description |
|---|---|---|---|
| `GET` | `/proxy/talk/api/users` | ✅ | All Talk users |
| `PUT` | `/proxy/talk/api/user/{user_uuid}` | ✅ | Full-object user update used by the UI for device and DID reassignment |
| `GET` | `/proxy/talk/api/number/list` | ✅ | All DIDs with full user, device, extension, and SIP data |
| `GET` | `/proxy/talk/api/number/blocked` | ✅ | Blocked caller ID rules |
| `PUT` | `/proxy/talk/api/number/blocked` | ✅ | Add a blocked number rule (full-number, prefix, or area-code; per-user/group or global) |
| `POST` | `/proxy/talk/api/number/delete_blocked` | ✅ | Delete blocked number rules by ID array `{"ids":[...]}` |
| `GET` | `/proxy/talk/api/contacts` | ✅ | Per-tenant contact objects used by the Talk UI |
| `POST` | `/proxy/talk/api/contacts` | ✅ | Create or upsert contacts (array payload; returns `inserted_uuids`) |
| `GET` | `/proxy/talk/api/contact_list` | ✅ | Shared contact directory (lists of contacts) |
| `POST` | `/proxy/talk/api/contact_list` | ✅ | Create a named contact list `{"name":"...","contacts":[...]}` |

### Call Routing

| Method | Path | Status | Description |
|---|---|---|---|
| `GET` | `/proxy/talk/api/ring_flow` | ✅ | Ring flow / call routing schedules |
| `GET` | `/proxy/talk/api/ring_groups` | ✅ | Ring group configurations |
| `GET` | `/proxy/talk/api/group_list` | ✅ | Ring group / group definitions used by routing UI |
| `PUT` | `/proxy/talk/api/group` | ✅ | Create a new ring group (returns integer group ID) |
| `PUT` | `/proxy/talk/api/group/{id}` | ✅ | Update an existing ring group |
| `POST` | `/proxy/talk/api/group/{id}/vm_greeting` | ✅ | Upload/confirm a voicemail greeting audio file for a ring group |
| `GET` | `/proxy/talk/api/queues` | ✅ | Call queue configurations |
| `GET` | `/proxy/talk/api/parking_lots` | ✅ | Call parking lot configurations (list) |
| `PUT` | `/proxy/talk/api/parking_lot` | ✅ | Create or update a single parking lot |
| `POST` | `/proxy/talk/api/parking_lots/delete` | ✅ | Delete parking lots by UUID array `{"uuids":[...]}` |
| `GET` | `/proxy/talk/api/switchboard` | ✅ | Switchboard/receptionist console configuration |
| `POST` | `/proxy/talk/api/switchboard/setup` | ✅ | Initialize a new switchboard (returns `{"swb_id": N}`) |
| `PUT` | `/proxy/talk/api/switchboard/item` | ✅ | Create or update a switchboard node (IVR menu item) |
| `PUT` | `/proxy/talk/api/switchboard/item/{id}/users` | ✅ | Assign/replace users for a switchboard item |
| `DELETE` | `/proxy/talk/api/switchboard/item/{id}` | ✅ | Delete a switchboard item |
| `DELETE` | `/proxy/talk/api/switchboard/item/{id}/user/{uuid}` | ✅ | Remove a specific user from a switchboard item |
| `PUT` | `/proxy/talk/api/switchboard/time_column` | ✅ | Add time-based routing columns (business hours / holidays) to a switchboard |
| `GET` | `/proxy/talk/api/phone_designer` | ✅ | Phone screen layout configurations |

### SIP / Trunking

| Method | Path | Status | Description |
|---|---|---|---|
| `GET` | `/proxy/talk/api/third_party_sip/gateway_list` | ✅ | SIP trunk/gateway configurations (**includes credentials — rotate after exposure**) |
| `PUT` | `/proxy/talk/api/third_party_sip/gateway` | ✅ | Create or update a SIP trunk (include `id` in body to update; omit to create) |

### SIP Protocol (Programmatic Call Control)

UniFi Talk exposes a native **FreeSWITCH 1.10.12** SIP server. Any SIP UA can register using credentials obtained from the REST API and place or end calls programmatically.

| Parameter | Value |
|---|---|
| SIP host | `<UDM-IP>:5060` (UDP) / `<UDM-IP>:5061` (TLS) |
| Auth scheme | RFC 3261 Digest MD5 (`qop="auth"`) |
| REGISTER challenge | `401 Unauthorized` + `WWW-Authenticate` |
| INVITE challenge | `407 Proxy Auth Required` + `Proxy-Authenticate` |
| Credentials source | `GET /proxy/talk/api/users` → `sip_password` + `ext` fields |
| Header style | Compact (RFC 3261 short forms: `v:`, `f:`, `t:`, `i:`, `l:`, `k:`) |

See [SIP Protocol & Call Control](endpoints/sip.md) for full flow diagrams, Digest auth examples, NOTIFY handling, and a complete Python implementation.

### System Settings

| Method | Path | Status | Description |
|---|---|---|---|
| `GET` | `/proxy/talk/api/setting/config` | ✅ | Full system config (recording, voicemail, NAT, codecs, E911, owner info) |
| `GET` | `/proxy/talk/api/setting/emergency_status` | ✅ | E911 address registration status per DID |
| `PUT` | `/proxy/talk/api/setting/voicemail_greeting` | ✅ | Upload or confirm the global voicemail greeting audio |
| `PUT` | `/proxy/talk/api/setting/default_area_code` | ✅ | Set the default area code for 7-digit dialing `{"area_code":"415"}` |

### SMS

| Method | Path | Status | Description |
|---|---|---|---|
| `GET` | `/proxy/talk/api/sms/conversations` | ✅ | SMS conversation list (supports `?page=`) |
| `GET` | `/proxy/talk/api/sms/trigger_sms_fetch` | ✅ | Forces an SMS sync/poll from the upstream provider |

### Integrations

| Method | Path | Status | Description |
|---|---|---|---|
| `GET` | `/proxy/talk/api/protect/cameras` | ✅ | UniFi Protect cameras (for video/intercom calling) |

### Audio

| Method | Path | Status | Description |
|---|---|---|---|
| `GET` | `/proxy/talk/api/setting/voicemail_greeting_file` | ✅ | Global voicemail greeting (raw MP3 binary) |
| `GET` | `/proxy/talk/api/setting/hold_music` | ✅ | Hold music track list |
| `GET` | `/proxy/talk/api/setting/hold_music/standard/{filename}` | ✅ | Download a standard hold music track (e.g. `Piano.wav`) |
| `PUT` | `/proxy/talk/api/setting/hold_music` | ✅ | Set the active hold music track `{"title":"Piano.wav","type":"standard"}` |
| `PUT` | `/proxy/talk/api/setting/ringback` | ✅ | Set the ringback tone `{"title":"Serene.wav","type":"standard"}` |
| `POST` | `/proxy/talk/api/setting/hold_music/upload` | ✅ | Upload a custom hold music file (multipart) |
| `GET` | `/proxy/talk/api/setting/ringtones` | ✅ | Ringtone list |
| `GET` | `/proxy/talk/api/voicemail/greeting/{filename}` | ✅ | Download a user or group voicemail greeting MP3 by filename |
| `GET` | `/proxy/talk/api/exports/audio_data_archive` | ⏳ | Bulk audio export download (500 when no export queued) |
| `POST` | `/proxy/talk/api/prepare_audio_data` | ⏳ | Trigger bulk audio export |

### Billing & Compliance

| Method | Path | Status | Description |
|---|---|---|---|
| `GET` | `/proxy/talk/api/acceptance/payments` | ✅ | Payment terms acceptance state and hosted terms URL |
| `GET` | `/proxy/talk/api/billing/coupons/balance` | ✅ | Coupon balance |
| `GET` | `/proxy/talk/api/billing/usage` | ✅ | Current usage counters for minutes, SMS, CNAM, transcription, and softphone |
| `GET` | `/proxy/talk/api/identity/status` | ✅ | KYC / business profile status |
| `GET` | `/proxy/talk/api/regulatory_bundle` | ✅ | A2P / STIR-SHAKEN bundle status |
| `GET` | `/proxy/talk/api/lock/usage` | ✅ | Seat/license usage |
| `GET` | `/proxy/talk/api/owner_transfer/transfer_state` | ✅ | Owner transfer state |
| `GET` | `/proxy/talk/api/number/porting/list` | ✅ | Number porting requests |
| `GET` | `/proxy/talk/api/number/porting/request_count` | ✅ | Porting request counts and limits |

### Debug

| Method | Path | Status | Description |
|---|---|---|---|
| `GET` | `/proxy/talk/api/debug/pcap/status` | ✅ | Packet capture status |
| `POST` | `/proxy/talk/api/debug/pcap/start` | ⏳ | Start packet capture |
| `POST` | `/proxy/talk/api/debug/pcap/stop` | ⏳ | Stop packet capture |
| `GET` | `/proxy/talk/api/debug/pcap/download` | ⏳ | Download PCAP file |

### AI / Transcription (Candidates — from JS bundle)

| Method | Path | Status | Description |
|---|---|---|---|
| `GET` | `/proxy/talk/api/ai_call_transcriptions` | ⏳ | AI call transcription settings |
| `GET` | `/proxy/talk/api/ai_vm_transcriptions` | ⏳ | AI voicemail transcription settings |

### WebSocket (Real-time Events)

| Path | Status | Description |
|---|---|---|
| `wss://<UDM-IP>/proxy/talk/ws` | ✅ | Confirmed — nginx proxies to localhost:3419 |
| `wss://<UDM-IP>/proxy/talk/wss/s/default/events` | ⏳ | Candidate — JS bundle + UniFi proxy convention |
| `wss://<UDM-IP>/proxy/talk/api/ws` | ⏳ | Tertiary candidate |

---

## Quick Reference: Common Tasks

### Using the SDK (recommended)

```python
from scripts.talk_sdk import TalkClient

c = TalkClient("192.168.1.1")
c.login("localadmin", "yourpassword")

info    = c.get_info()          # system version/flags
users   = c.get_users()         # all users
numbers = c.get_numbers()       # all DIDs with assignment data
calls   = c.get_all_call_logs() # all call history (auto-paginated)
vms     = c.get_voicemails()    # calls where status=="voicemail"
config  = c.get_config()        # system settings
```

### Get all inbound call history with caller ID (raw)

```python
import requests, warnings
warnings.filterwarnings("ignore")

HOST = "192.168.1.1"
s = requests.Session()
s.verify = False

# Login
r = s.post(f"https://{HOST}/api/auth/login",
           json={"username": "localadmin", "password": "yourpassword", "rememberMe": False})
s.headers["X-CSRF-Token"] = r.headers["x-updated-csrf-token"]

# Fetch all call log pages
all_calls = []
page = 1
while True:
    r = s.get(f"https://{HOST}/proxy/talk/api/call_log",
              params={"page": page, "per_page": 50})
    records = r.json().get("records", [])
    if not records:
        break
    all_calls.extend(records)
    if len(records) < 50:
        break
    page += 1

# Print inbound calls with caller ID
for call in all_calls:
    if call["direction"] == "in":
        print(f"{call['time']}  FROM: {call['from']}  STATUS: {call['status']}  DURATION: {call['duration']}s")
```

### Get all voicemails

```python
voicemails = [c for c in all_calls if c["status"] == "voicemail" and c.get("vm_data")]
for vm in voicemails:
    data = vm["vm_data"]
    read = "READ" if data["read_at"] != "0" else "UNREAD"
    print(f"{vm['time']}  FROM: {vm['from']}  [{read}]  {data['duration']}s  {data['file_path']}")
```

### Probe all candidate endpoints

```bash
# Probe everything (slow — tests ~80 paths):
python3 scripts/probe_endpoints.py --host 192.168.1.1 -u admin -p yourpass

# Only test endpoints not yet confirmed as 200:
python3 scripts/probe_endpoints.py --host 192.168.1.1 -u admin -p yourpass --unknowns-only
```

### Monitor WebSocket events in real time

```bash
python3 scripts/ws_monitor.py --host 192.168.1.1 -u admin -p yourpass
```

### Place a call programmatically (SIP)

Register as a UniFi Talk extension and originate a call using `scripts/sip_test.py`. Credentials come from `GET /proxy/talk/api/users` — no separate provisioning needed.

```bash
# First: get your SIP credentials
python3 scripts/api_client.py --host 192.168.1.1 -u admin -p yourpass \
  --endpoint users | python3 -c "import json,sys; [print(u['ext'], u['sip_password']) for u in json.load(sys.stdin)]"

# Save to .local/sip_credentials.json:
# {"host": "192.168.1.1", "ext": "0001", "password": "<sip_password>"}

# Test registration
python3 scripts/sip_test.py

# Call an internal extension (hangs up after 5 seconds)
python3 scripts/sip_test.py --call 0002 --hangup-after 5

# Call a PSTN number
python3 scripts/sip_test.py --call +17195551234 --hangup-after 10
```

See [SIP Protocol & Call Control](endpoints/sip.md) for the complete reference including digest auth flow, compact header handling, and a minimal Python implementation.

---

## Known Gaps (Still Investigating)

| Topic | Gap | Next Step |
|---|---|---|
| WebSocket | ✅ Confirmed — `wss://<UDM-IP>/proxy/talk/ws`; schema still being documented | See [websocket.md](endpoints/websocket.md) |
| Voicemail audio download | No HTTP API exists — only filesystem access | SSH to `/srv/unifi-talk/voicemail/talk.com/<ext>/` |
| Per-user voicemail greeting | No confirmed HTTP download API | SSH to `/srv/unifi-talk/voicemail/talk.com/<ext>/greeting.mp3` |
| Mutating endpoints | POST/PUT/DELETE for settings/routing not yet confirmed | Use mitmproxy to capture Talk UI save actions |
| SMS sending | Conversations confirmed; send/reply API unknown | Capture from UI via mitmproxy |
| Call initiation | ✅ Resolved — use SIP INVITE via internal FreeSWITCH | See [sip.md](endpoints/sip.md) and `scripts/sip_test.py` |
| Audio export trigger | `POST /prepare_audio_data` returns 404 | Check correct path in bundle; may be `POST /exports/audio_data_archive` |
| Call transcription content | `call_log/transcription/<uuid>` confirmed — returns null | Enable AI transcription in Talk settings first |

---

## Detailed Documentation

- [Authentication](endpoints/auth.md)
- [Call Logs & Recording Rules](endpoints/calls.md)
- [Recordings & Voicemail](endpoints/recordings.md)
- [Devices, Users & Phone Numbers](endpoints/devices.md)
- [SIP Protocol & Programmatic Call Control](endpoints/sip.md)
- [Capture Gap-Fill Endpoint Guide (2026-05-08)](endpoints/capture_gap_fill.md)
- [WebSocket Real-time Events](endpoints/websocket.md)
- [System Settings & Configuration](endpoints/settings.md)
