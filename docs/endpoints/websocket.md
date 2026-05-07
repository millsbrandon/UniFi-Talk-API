# WebSocket API

---

## Overview

UniFi Talk uses a WebSocket connection for real-time push events including:
- Incoming call notifications and call lifecycle updates
- Device presence/registration heartbeats
- Voicemail arrival notifications
- Active call tracking

The WebSocket connection is established by the Talk web UI immediately after login and remains open for the session.

---

## Connection — CONFIRMED ✅

**Confirmed path** (live-captured 2026-05-07):

```
wss://<UDM-IP>/proxy/talk/ws
```

The backend Talk process listens on `wss://localhost:3419` (internal only). The UDM nginx proxy maps `/proxy/talk/ws` → `localhost:3419`. The direct port is **firewalled** from LAN clients — you must use the nginx proxy path.

### Connection headers

```
GET /proxy/talk/ws HTTP/1.1
Host: 192.168.1.1
Upgrade: websocket
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf_from_jwt_payload>
```

> Do **not** add `Upgrade: websocket` manually when using `websocket-client` — the library adds it automatically. Adding it twice causes nginx to return `400 Invalid Upgrade header`.

---

## Authentication

- The `TOKEN` JWT cookie must be present and valid (2-hour TTL).
- The `X-CSRF-Token` header should also be sent. The CSRF token is extracted from the JWT payload field `.csrfToken` (the `csrf_token` field in the login response body is always an empty string).
- No separate WebSocket handshake or token exchange occurs — cookie auth is sufficient.

---

## Message Format — CONFIRMED ✅

All server-to-client messages use this flat envelope:

```json
{
  "event": "EVENT_TYPE",
  "data": { ... }
}
```

There is **no** `meta`/`rc`/`message` wrapper (unlike UniFi Network WS). The `event` field is a `SCREAMING_SNAKE_CASE` string.

---

## Event Types — Live Captured

### Summary

| Event | Frequency | Description |
|---|---|---|
| `DEVICES_UPDATED` | Every ~10s | Device heartbeat — full device state array |
| `CALL_LOG_UPDATED` | Per call event | Call record update with full call log entry |
| `CALL_EVENTS_UPDATED` | Per call sub-event | Lightweight pointer — call UUID + timestamp |
| `ONGOING_EVENTS_UPDATE` | On call start/end | Count of active ongoing calls |
| `USERS_ON_ACTIVE_CALLS` | On call start/end | Array of user UUIDs currently on a call |
| `TRIGGER_STAT_REFRESH` | Periodic | Signal to UI to refresh stats (no data payload) |

---

### `DEVICES_UPDATED`

Fires every ~10 seconds as a heartbeat. Contains the full device state for all registered Talk devices.

```json
{
  "event": "DEVICES_UPDATED",
  "data": [
    {
      "mac": "aabbccddeeff",
      "ip": "192.168.1.253",
      "model": "UT-ATA",
      "sshd_port": 22,
      "mgmt_is_default": false,
      "version": "1.1.5",
      "last_seen": "2026-05-07T03:46:08.074Z",
      "con_ip": "192.168.1.253",
      "con_port": 45623,
      "uptime": 18256,
      "con_status": null,
      "hashed_key": "a24ea7f4...",
      "anonymous_device_id": "f75892c9-249b-aeff-b9e3-267ee7525388",
      "additional_data": {
        "autolink_ap_mac": "78:45:58:cc:c5:04",
        "is_autolink_device": false,
        "autolink_device_mac": "aabbccddeeff",
        "backup_restore_adoption": true
      },
      "ucp4": null,
      "cfp": null,
      "wsdc_change_ready": null,
      "is_locked_device": false,
      "adopted": true,
      "last_inform": "2026-05-07T03:46:08.074Z",
      "pending_delete": null,
      "user_id": "a1b2c3d4-1111-2222-3333-444455556666",
      "display_name": "UT-ATA-1A27",
      "secretary_mode": null,
      "last_updated": null,
      "user_id_line2": null,
      "additional_config": {},
      "battery_level": null,
      "status": "online",
      "last_synced_contact_ids": [],
      "serial_number": null,
      "contact_list": [],
      "sip_reg": true,
      "user": "Jane Smith",
      "phone_number": "+12125551234",
      "phone_numbers": null,
      "user_line2": " ",
      "ext": "0002",
      "update_available": false,
      "is_assigned": "a1b2c3d4-1111-2222-3333-444455556666",
      "device_update_data": null,
      "is_assigned_to_instant_adopt_user": false
    }
  ]
}
```

---

### `CALL_LOG_UPDATED`

Fires multiple times per call as the call progresses. The `data.records` array contains the most recently updated call records (typically the active/just-completed calls, not the full history). Each record carries the full call log entry including `call_events` sub-events and `vm_data`.

**Initial arrival — call just started (before routing):**

```json
{
  "event": "CALL_LOG_UPDATED",
  "data": {
    "records": [
      {
        "time": "2026-05-07T03:47:19.179Z",
        "from": "+19175550001",
        "to": "+12125551234",
        "answered_by": null,
        "status": "accepted",
        "duration": null,
        "recording_filename": null,
        "is_video_call": false,
        "is_intercom_call": false,
        "is_group_intercom_call": false,
        "direction": "in",
        "uuid": "574a047a-7033-4deb-aa49-2f090b225396",
        "country": "US",
        "recording": null,
        "quality_score": null,
        "vm_data": {},
        "call_events": [],
        "from_mac": null,
        "from_id": null,
        "from_contact_id": null,
        "from_did": null,
        "from_caller_name": null,
        "to_id": null,
        "to_group_id": null,
        "to_contact_id": null,
        "to_smart_attendant_id": 1,
        "to_smart_attendant_title": "Main Inbound Menu",
        "to_queue_id": null,
        "answered_by_mac": null,
        "answered_by_user_uuid": null,
        "answered_by_contact_id": null,
        "answered_by_group_id": null
      }
    ]
  }
}
```

**After call ends — voicemail received (final state):**

```json
{
  "event": "CALL_LOG_UPDATED",
  "data": {
    "records": [
      {
        "time": "2026-05-07T03:47:19.179Z",
        "from": "+19175550001",
        "to": "+12125551234",
        "answered_by": null,
        "status": "accepted",
        "duration": 22,
        "recording_filename": null,
        "is_video_call": false,
        "is_intercom_call": false,
        "is_group_intercom_call": false,
        "direction": "in",
        "uuid": "574a047a-7033-4deb-aa49-2f090b225396",
        "country": "US",
        "recording": false,
        "quality_score": 100,
        "vm_data": {
          "uuid": "574a047a-7033-4deb-aa49-2f090b225396",
          "read_at": "0",
          "duration": "5",
          "file_path": "/srv/unifi-talk/voicemail/talk.com/0008/20260506_214741_19175550001_12125551234_574a04.mp3",
          "received_at": "1778125660",
          "vm_left_for_ext": "0008",
          "vm_receiver_uuid": "b2c3d4e5-2222-3333-4444-555566667777",
          "recipient_user_uuids": ["b2c3d4e5-2222-3333-4444-555566667777"],
          "fs_db_vm_uuids_ext_mapping": [
            { "ext": "0008", "uuid": "574a047a-7033-4deb-aa49-2f090b225396" }
          ]
        },
        "call_events": [
          {
            "time": "2026-05-07T03:47:19.221Z",
            "event": "call_started",
            "event_data": {
              "to": "+12125551234",
              "from": "+19175550001",
              "to_smart_attendant_id": 1
            },
            "event_uuid": "d3dab88e-b302-4ad4-9a15-2231bb32c18b"
          },
          {
            "time": "2026-05-07T03:47:25.511Z",
            "event": "call_sent_to_voicemail",
            "event_data": {
              "recipient_user_uuids": ["b2c3d4e5-2222-3333-4444-555566667777"]
            },
            "event_uuid": "c7ad381a-4771-4642-99e6-59f55fcef0ec"
          },
          {
            "time": "2026-05-07T03:47:41.047Z",
            "event": "call_hangup",
            "event_data": { "hangup_cause": "normal_end" },
            "event_uuid": "..."
          }
        ],
        "from_caller_name": "DOE,JOHN",
        "to_smart_attendant_id": 1,
        "to_smart_attendant_title": "Main Inbound Menu"
      }
    ]
  }
}
```

#### `call_events` sub-event types (confirmed)

These appear inside `CALL_LOG_UPDATED → records[n].call_events[]`:

| `event` | When it fires | Key `event_data` fields |
|---|---|---|
| `call_started` | Call arrives at the system | `from`, `to`, `to_smart_attendant_id` (if SA) or `to_user_uuid` (if direct) |
| `seq_call_trying_endpoints` | System is ringing destination device(s) | `user_uuids[]`, `device_macs[]` |
| `call_sent_to_voicemail` | Call forwarded to a voicemail box | `recipient_user_uuids[]` |
| `call_hangup` | Call ended | `hangup_cause` (e.g. `"normal_end"`) |

#### Call record status values (confirmed)

| `status` | Meaning |
|---|---|
| `"accepted"` | Call is in-progress (live) |
| `"voicemail"` | Call ended; went to voicemail |
| `"missed"` | Call rang but was not answered (no voicemail) |

#### Call record routing fields

| Field | Type | Description |
|---|---|---|
| `to_smart_attendant_id` | int \| null | Smart attendant ID if call was routed to an SA |
| `to_smart_attendant_title` | string \| null | Smart attendant name (e.g. `"Main Inbound Menu"`) |
| `to_id` | string \| null | Target user UUID for direct calls |
| `to_group_id` | string \| null | Ring group UUID |
| `to_queue_id` | string \| null | Call center queue UUID |
| `to_contact_id` | string \| null | Contact ID |
| `answered_by_user_uuid` | string \| null | UUID of user who answered |
| `answered_by_mac` | string \| null | Device MAC of answering device |
| `answered_by_group_id` | string \| null | Group UUID if answered via ring group |

---

### `CALL_EVENTS_UPDATED`

A lightweight pointer event fired whenever a `call_events` sub-event is appended to a call record. It signals clients to re-fetch the call log for the given `call_id`. Does not carry the call data itself.

```json
{
  "event": "CALL_EVENTS_UPDATED",
  "data": {
    "call_id": "574a047a-7033-4deb-aa49-2f090b225396",
    "updated_at": "2026-05-07T03:47:25.538Z"
  }
}
```

Multiple `CALL_EVENTS_UPDATED` events may fire in rapid succession for the same call (one per sub-event appended). They are always followed shortly by a `CALL_LOG_UPDATED` with the full updated record.

---

### `ONGOING_EVENTS_UPDATE`

Fires when the count of active (in-progress) calls changes.

```json
{
  "event": "ONGOING_EVENTS_UPDATE",
  "data": {
    "ongoing_event_count": "0"
  }
}
```

> Note: `ongoing_event_count` is a **string**, not an integer.

---

### `USERS_ON_ACTIVE_CALLS`

Fires when any user starts or ends a call. Contains the full list of user UUIDs who currently have an active call in progress.

```json
{
  "event": "USERS_ON_ACTIVE_CALLS",
  "data": {
    "user_ids": ["a1b2c3d4-1111-2222-3333-444455556666"]
  }
}
```

Empty list when no calls are active:

```json
{
  "event": "USERS_ON_ACTIVE_CALLS",
  "data": {
    "user_ids": []
  }
}
```

---

### `TRIGGER_STAT_REFRESH`

A server-side signal telling the Talk UI to refresh its statistics dashboard. Carries no meaningful data payload. Fires periodically (observed once per session in the initial connection burst).

```json
{
  "event": "TRIGGER_STAT_REFRESH",
  "data": {}
}
```

---

## Event Sequence — Inbound Call to Smart Attendant → Voicemail

The following sequence was observed during two live test calls (2026-05-07):

```
1. CALL_EVENTS_UPDATED        { call_id, updated_at }          ← call record created
2. CALL_LOG_UPDATED           { records: [{ call_events:[], status:"accepted", ... }] }
3. CALL_EVENTS_UPDATED        { call_id, updated_at }          ← call_started appended
4. CALL_LOG_UPDATED           { records: [{ call_events:[call_started], ... }] }
5. CALL_EVENTS_UPDATED        { call_id, updated_at }          ← call_sent_to_voicemail appended
6. CALL_LOG_UPDATED           { records: [{ call_events:[call_started, call_sent_to_voicemail], ... }] }
7. CALL_EVENTS_UPDATED (x2)   { call_id, updated_at }          ← call_hangup appended (2 rapid fires)
8. CALL_LOG_UPDATED           { records: [{ vm_data:{...}, call_events:[...call_hangup], duration:22, ... }] }
```

`ONGOING_EVENTS_UPDATE` and `USERS_ON_ACTIVE_CALLS` fire at connection time and when call state changes, but were not observed to update during smart-attendant-only calls (likely because no human user was placed on an active call — the SA handled it entirely).

**Key observations:**
- `CALL_LOG_UPDATED.records` contains only recently-modified calls (1–2 records), not the full log.
- `from_caller_name` is initially `null` and populated in a subsequent `CALL_LOG_UPDATED` once CNAM resolves.
- `vm_data.file_path` reveals the server-side MP3 path (SSH-accessible only, no HTTP download API).
- `vm_data.duration` is a **string** (seconds), not an integer.
- `duration` on the call record itself (total call duration) is an integer.

---

## Python WebSocket Monitor

The `scripts/ws_monitor.py` script connects to the confirmed path and prints events in real time:

```bash
python3 scripts/ws_monitor.py --host 192.168.1.1 -u localadmin -p 'yourpassword'
```

Events are printed to stdout and appended to `captures/ws_events.jsonl`.

### Quick Python snippet

```python
import websocket, json, ssl, base64

HOST = "192.168.1.1"
TOKEN = "eyJ..."  # JWT from login response cookie
# Extract CSRF from JWT payload
payload = TOKEN.split(".")[1]
payload += "=" * (-len(payload) % 4)
csrf = json.loads(base64.urlsafe_b64decode(payload))["csrfToken"]

def on_message(ws, msg):
    data = json.loads(msg)
    print(data["event"], json.dumps(data.get("data"), indent=2))

ws = websocket.WebSocketApp(
    f"wss://{HOST}/proxy/talk/ws",
    cookie=f"TOKEN={TOKEN}",
    header={"X-CSRF-Token": csrf},
    on_message=on_message,
)
ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
```

---

## Status

| Item | Status |
|---|---|
| WS path confirmed | ✅ `wss://<UDM-IP>/proxy/talk/ws` |
| Direct backend port | ✅ `localhost:3419` (firewalled from LAN) |
| Message schema confirmed | ✅ flat `{"event": "...", "data": {...}}` |
| `DEVICES_UPDATED` schema | ✅ live-captured |
| `CALL_LOG_UPDATED` schema | ✅ live-captured |
| `CALL_EVENTS_UPDATED` schema | ✅ live-captured |
| `ONGOING_EVENTS_UPDATE` schema | ✅ live-captured |
| `USERS_ON_ACTIVE_CALLS` schema | ✅ live-captured |
| `TRIGGER_STAT_REFRESH` schema | ✅ live-captured |
| Inbound call → SA → voicemail sequence | ✅ live-captured |
| Direct extension ring sequence | ⏳ not yet captured |
| Answered call sequence | ⏳ not yet captured |
| Outbound call sequence | ⏳ not yet captured |
| Client-to-server messages (commands) | ⏳ unknown — no client sends observed |
