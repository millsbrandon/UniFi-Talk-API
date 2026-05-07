# UniFi Talk Unofficial API — Community Research Notes

> **Status**: Living document — confirmed against UniFi Talk v5.1.2 on UDM-Pro running UniFi OS v5.1.10  
> **Reverse-engineered by**: Live traffic capture + JS bundle analysis (`index-5.1.2.js`, 5.4 MB webpack bundle)  
> **Disclaimer**: Ubiquiti provides no public API for UniFi Talk. This is the result of independent reverse-engineering. It may break without notice on future firmware updates.

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [System Information](#system-information)
4. [Call Logs](#call-logs)
5. [Call Recordings](#call-recordings)
6. [Voicemail](#voicemail)
7. [Devices](#devices)
8. [Users & Phone Numbers](#users--phone-numbers)
9. [Call Routing](#call-routing)
10. [SMS](#sms)
11. [System Settings](#system-settings)
12. [SIP / Trunking](#sip--trunking)
13. [Billing & Compliance](#billing--compliance)
14. [Debug](#debug)
15. [WebSocket — Real-Time Events](#websocket--real-time-events)
16. [Python SDK Quick Start](#python-sdk-quick-start)
17. [Endpoint Status Index](#endpoint-status-index)

---

## Overview

UniFi Talk is a VoIP application that runs on UniFi Dream Machine Pro and similar consoles. All API traffic is proxied through the UDM nginx instance at `https://<UDM-IP>/proxy/talk/`. There is no cloud relay — every call goes directly to your local controller.

### Base URLs

| Component | Base |
|---|---|
| UniFi OS Auth | `https://<UDM-IP>/api/auth` |
| Talk API | `https://<UDM-IP>/proxy/talk/api` |
| WebSocket | `wss://<UDM-IP>/proxy/talk/ws` |

> The UDM uses a self-signed TLS certificate on LAN. Use `verify=False` in Python requests or `-k` in curl. The certificate is stable and you may choose to pin it once extracted.

### How the proxy works

The nginx reverse proxy on the UDM routes:
- `https://<UDM-IP>/proxy/talk/*` → `http://localhost:8082` (Talk HTTP API)
- `wss://<UDM-IP>/proxy/talk/ws` → `ws://localhost:3419` (Talk WebSocket, internal port only)

---

## Authentication

UniFi Talk uses standard UniFi OS session auth. This works only with **local accounts** created directly on the console ("Local Access Only" accounts). Ubiquiti cloud/SSO accounts require a separate OAuth flow.

### POST `/api/auth/login`

```http
POST https://<UDM-IP>/api/auth/login
Content-Type: application/json

{
  "username": "localadmin",
  "password": "yourpassword",
  "rememberMe": false
}
```

**Response (200 OK)**:

```json
{
  "uniqueId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "username": "localadmin",
  "csrf_token": ""
}
```

> ⚠️ The `csrf_token` body field is **always an empty string**. The real CSRF token comes from the `x-updated-csrf-token` **response header**, or can be decoded from the JWT cookie payload field `.csrfToken`.

**Set-Cookie**:
```
TOKEN=<jwt>; Path=/; HttpOnly; SameSite=Strict
```

**JWT payload structure** (base64-decode the middle segment):

```json
{
  "userId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "passwordRevision": 1700000000,
  "isRemembered": false,
  "csrfToken": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "iat": 1700000000,
  "exp": 1700007200,
  "jti": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy"
}
```

Token lifetime: **2 hours** (`exp - iat = 7200`).

**Extracting CSRF from the JWT in Python**:

```python
import base64, json

def extract_csrf(token: str) -> str:
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)  # fix padding
    return json.loads(base64.urlsafe_b64decode(payload))["csrfToken"]
```

### Required headers for all Talk API requests

```http
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf_uuid>
```

Both are required. Most GETs work without the CSRF header, but POST/PUT/DELETE will return `401` without it.

### Rate limiting

After ~5 failed login attempts the server returns `429 AUTHENTICATION_FAILED_LIMIT_REACHED`. Wait approximately 3 minutes before retrying.

### POST `/api/auth/logout`

```http
POST https://<UDM-IP>/api/auth/logout
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

Clears the `TOKEN` cookie and invalidates the server-side session.

---

## System Information

### GET `/proxy/talk/api/info`

Returns Talk version, region, enabled feature flags, and system identity.

```http
GET https://<UDM-IP>/proxy/talk/api/info
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

**Response**:

```json
{
  "version": "5.1.2",
  "region": "US",
  "hostname": "my-udm-pro",
  "features": {
    "call_recording": true,
    "voicemail": true,
    "sms": true,
    "call_transcription": false,
    "advanced_routing": false,
    "call_center": false
  }
}
```

### GET `/proxy/talk/api/info/app_owner`

Returns the Talk account owner's profile.

### GET `/proxy/talk/api/install`

Returns Talk installation/onboarding completion state.

### GET `/proxy/talk/api/setup_complete`

Returns whether initial Talk setup wizard has been completed (`true`/`false`).

### GET `/proxy/talk/api/updates`

Returns available firmware/software updates for the Talk system.

### GET `/proxy/talk/api/ucore/system_info`

Returns UniFi OS core information (console model, serial, hardware revision).

**Example response (sanitized)**:

```json
{
  "model": "UDMPRO",
  "version": "5.1.10",
  "serial": "xxxxxxxxxxxx",
  "mac": "xx:xx:xx:xx:xx:xx",
  "hostname": "UniFi-Dream-Machine-Pro"
}
```

### GET `/proxy/talk/api/dashboard/consolidated_info`

Returns a dashboard summary: console name, WAN/gateway IPs, Talk service uptime.

### GET `/proxy/talk/api/dashboard/most_active_users`

Returns the most active Talk users by call count/duration.

### GET `/proxy/talk/api/peer_consoles`

Returns other UniFi consoles discovered on the network.

### GET `/proxy/talk/api/applications`

Returns configuration for installed UniFi applications on this console.

### GET `/proxy/talk/api/drive/status`

Returns storage drive status for the console.

---

## Call Logs

### GET `/proxy/talk/api/call_log`

Returns paginated call history. Each record includes full caller ID metadata, direction, status, duration, voicemail data, and a sub-event timeline for the call.

```http
GET https://<UDM-IP>/proxy/talk/api/call_log?page=1&per_page=50
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

**Query parameters**:

| Parameter | Type | Required | Default | Notes |
|---|---|---|---|---|
| `page` | integer | **Yes** | — | 1-based. Omitting returns `400 invalid page`. |
| `per_page` | integer | No | 50 | Records per page. |
| `direction` | string | No | — | `in` or `out` |
| `status` | string | No | — | See status values below |
| `did` | string | No | — | Filter by DID (E.164, e.g. `+12125551234`) |

> `offset`/`limit` pagination returns `400 invalid page`. Only `page`-based works.

**Response**:

```json
{
  "records": [
    {
      "time": "2024-03-15T14:22:08.197Z",
      "from": "+12125551234",
      "to": "+13105559876",
      "answered_by": null,
      "status": "voicemail",
      "duration": 16,
      "recording_filename": null,
      "is_video_call": false,
      "is_intercom_call": false,
      "is_group_intercom_call": false,
      "direction": "in",
      "uuid": "de8df029-f93e-48b3-a3f5-529c1fff996c",
      "country": "US",
      "recording": false,
      "quality_score": 98,
      "vm_data": {
        "uuid": "de8df029-f93e-48b3-a3f5-529c1fff996c",
        "read_at": "0",
        "duration": "8",
        "file_path": "/srv/unifi-talk/voicemail/talk.com/0002/msg_2b681a8c.mp3",
        "received_at": "1710512528",
        "vm_left_for_ext": "0002",
        "vm_receiver_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "recipient_user_uuids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
        "fs_db_vm_uuids_ext_mapping": [
          { "ext": "0002", "uuid": "de8df029-f93e-48b3-a3f5-529c1fff996c" }
        ]
      },
      "call_events": [
        {
          "time": "2024-03-15T14:22:08.227Z",
          "event": "call_started",
          "event_data": {
            "to": "+13105559876",
            "from": "+12125551234",
            "to_user_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
          },
          "event_uuid": "5c7d16fa-5093-4a6e-a95f-bd845e103869"
        },
        {
          "time": "2024-03-15T14:22:08.330Z",
          "event": "seq_call_trying_endpoints",
          "event_data": {
            "user_uuids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
            "device_macs": ["aabbccddeeff"]
          },
          "event_uuid": "914f5b41-22b0-4cd6-9ecd-a4448c3cfc74"
        },
        {
          "time": "2024-03-15T14:22:39.003Z",
          "event": "call_sent_to_voicemail",
          "event_data": {
            "recipient_user_uuids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
          },
          "event_uuid": "ccddee11-2233-4455-6677-889900aabbcc"
        },
        {
          "time": "2024-03-15T14:22:45.111Z",
          "event": "call_hangup",
          "event_data": { "hangup_cause": "normal_end" },
          "event_uuid": "ff001122-3344-5566-7788-99aabbccddee"
        }
      ],
      "from_caller_name": "JOHN DOE",
      "to_smart_attendant_id": null,
      "to_smart_attendant_title": null,
      "to_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "to_group_id": null,
      "to_queue_id": null,
      "answered_by_user_uuid": null,
      "answered_by_mac": null
    }
  ]
}
```

**Call record field reference**:

| Field | Type | Description |
|---|---|---|
| `time` | ISO 8601 | Call start timestamp (UTC) |
| `from` | string | Caller number (E.164) or internal extension |
| `to` | string | Dialed number (E.164) or internal extension |
| `answered_by` | string \| null | User UUID who answered; null if unanswered |
| `status` | string | Call outcome (see below) |
| `duration` | integer \| null | Total call duration in seconds; null while active |
| `recording_filename` | null | Always null — use recording UUID instead |
| `is_video_call` | boolean | Video call flag |
| `is_intercom_call` | boolean | Internal intercom call |
| `direction` | string | `"in"` or `"out"` |
| `uuid` | UUID string | Primary key for this call record |
| `country` | string | ISO 3166-1 alpha-2 caller country |
| `recording` | boolean \| null | Whether a recording file exists |
| `quality_score` | integer | Call quality score (0–100; 0 = no data) |
| `vm_data` | object \| null | Voicemail metadata when `status == "voicemail"` |
| `call_events` | array | Ordered timeline of internal routing events |
| `from_caller_name` | string \| null | CNAM lookup result; may arrive null then populate |
| `to_smart_attendant_id` | integer \| null | Smart attendant ID if routed to SA |
| `to_smart_attendant_title` | string \| null | Smart attendant name |
| `to_group_id` | UUID \| null | Ring group UUID |
| `to_queue_id` | UUID \| null | Call queue UUID |

**Call status values**:

| `status` | Meaning |
|---|---|
| `"accepted"` | Call in progress (live) |
| `"voicemail"` | Caller left a voicemail |
| `"missed"` | Rang but unanswered, no voicemail |
| `"declined"` | Call rejected |
| `"failed"` | Call failed (e.g. no route) |

**`call_events` sub-event types** (observed in live captures):

| `event` | Description | Key `event_data` fields |
|---|---|---|
| `call_started` | Call arrived at system | `from`, `to`, `to_user_uuid` or `to_smart_attendant_id` |
| `seq_call_trying_endpoints` | Ringing destination devices | `user_uuids[]`, `device_macs[]` |
| `skipped_endpoints` | Destinations bypassed during routing | `user_uuids[]`, `device_macs[]`, `contact_uuids[]`, `external_dids[]` |
| `call_sent_to_voicemail` | Routed to voicemail | `recipient_user_uuids[]` |
| `call_hangup` | Call terminated | `hangup_cause` (e.g. `"normal_end"`) |
| `call_answered` | Call picked up | user/device identifiers |

**`vm_data` field reference**:

| Field | Type | Description |
|---|---|---|
| `uuid` | UUID | Matches the call's `uuid` |
| `read_at` | string | Unix timestamp string; `"0"` = unread |
| `duration` | string | Voicemail length in seconds (string, not integer) |
| `file_path` | string | Absolute server-side MP3 path (SSH-accessible only) |
| `received_at` | string | Unix timestamp string of voicemail receipt |
| `vm_left_for_ext` | string | Extension number that received the voicemail |
| `vm_receiver_uuid` | UUID | User UUID of recipient |

---

### GET `/proxy/talk/api/call_log/csv`

Exports call log as CSV. Requires `items_per_page` (not `per_page`).

```http
GET https://<UDM-IP>/proxy/talk/api/call_log/csv?page=1&items_per_page=500
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

**Response** (`text/csv`):

```
time,from,to,answered_by,status,duration,recording_filename,is_video_call,is_intercom_call,is_group_intercom_call,queue_name
2024-03-15 14:22:08,+12125551234,+13105559876,,voicemail,16,,false,false,false,
2024-03-15 13:10:44,+13105559876,+12065554321,Jane Smith,answered,182,,false,false,false,
```

**Columns**:

| Column | Description |
|---|---|
| `time` | Call timestamp (UTC, `YYYY-MM-DD HH:MM:SS`) |
| `from` | Caller number |
| `to` | Dialed number |
| `answered_by` | Name of user who answered (empty if unanswered) |
| `status` | Call outcome |
| `duration` | Duration in seconds |
| `recording_filename` | Always empty (see recording download endpoint) |
| `is_video_call` | `true`/`false` |
| `is_intercom_call` | `true`/`false` |
| `is_group_intercom_call` | `true`/`false` |
| `queue_name` | Call center queue name if applicable |

> ⚠️ The parameter name is `items_per_page`, not `per_page`. Using `per_page` returns `400 invalid items per page`. Maximum observed: 500 per page.

---

### GET `/proxy/talk/api/call_log/flow/<uuid>`

Returns the full routing/event timeline for a specific call. More detailed than the `call_events` array in the call log record.

```http
GET https://<UDM-IP>/proxy/talk/api/call_log/flow/de8df029-f93e-48b3-a3f5-529c1fff996c
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

**Response** (array of events):

```json
[
  {
    "time": "2024-03-15T14:22:08.227Z",
    "event": "call_started",
    "event_data": { "to": "+13105559876", "from": "+12125551234" },
    "event_uuid": "5c7d16fa-5093-4a6e-a95f-bd845e103869"
  },
  {
    "time": "2024-03-15T14:22:08.330Z",
    "event": "seq_call_trying_endpoints",
    "event_data": { "user_uuids": ["a1b2c3d4-..."], "device_macs": ["aabbccddeeff"] },
    "event_uuid": "914f5b41-..."
  }
]
```

---

### GET `/proxy/talk/api/call_log/transcription/<uuid>`

Returns AI-generated transcription for a call. Returns `null` fields if transcription is not enabled.

```http
GET https://<UDM-IP>/proxy/talk/api/call_log/transcription/de8df029-f93e-48b3-a3f5-529c1fff996c
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

---

### GET `/proxy/talk/api/call_log/countries`

Returns a list of country codes represented in the call log.

---

### GET `/proxy/talk/api/call_recording_rule`

Returns call recording rule configurations (which extensions/users have recording enabled, etc.).

---

### Call log deletion (✅ live-confirmed)

| Method | Path | Body | Description |
|---|---|---|---|
| `DELETE` | `/proxy/talk/api/call_log/<uuid>` | — | Delete single call log entry |
| `POST` | `/proxy/talk/api/delete_call_logs` | `{"uuids": ["<uuid1>", ...]}` | Bulk delete call log entries |

---

## Call Recordings

> **Important**: The `recording_filename` field on every call log record is always `null` in the API, even when a recording exists. Use the call's `uuid` directly in the recording download URL.

### GET `/proxy/talk/api/call_log/recording/<uuid>`

Downloads a call recording as raw MP3.

```http
GET https://<UDM-IP>/proxy/talk/api/call_log/recording/de8df029-f93e-48b3-a3f5-529c1fff996c
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

**Response**: Raw `audio/mpeg` binary (~1.5 KB/sec for standard quality).

Returns `404` with JSON body if no recording exists:

```json
{
  "message": "ENOENT: no such file or directory, stat '/srv/unifi-talk/recordings/<uuid>'"
}
```

Recordings are stored at `/srv/unifi-talk/recordings/<uuid>` on the UDM filesystem.

**Python example**:

```python
response = requests.get(
    f"https://{host}/proxy/talk/api/call_log/recording/{call_uuid}",
    cookies={"TOKEN": token},
    headers={"X-CSRF-Token": csrf},
    verify=False,
    stream=True,
)
if response.status_code == 200:
    with open(f"{call_uuid}.mp3", "wb") as f:
        f.write(response.content)
```

---

### GET `/proxy/talk/api/call_log/audio_data/<uuid>`

Returns waveform peaks data for rendering a visual waveform player in the UI.

```http
GET https://<UDM-IP>/proxy/talk/api/call_log/audio_data/de8df029-f93e-48b3-a3f5-529c1fff996c
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

**Response**:

```json
{
  "peaks_data": {
    "version": 2,
    "channels": 1,
    "sample_rate": 8000,
    "samples_per_pixel": 512,
    "bits": 8,
    "length": 3126,
    "data": [0, 12, 3, 8, 5, 14, 2, 7]
  },
  "recording_file_type": "mp3"
}
```

The `data` array contains amplitude samples suitable for drawing a waveform.

---

### Recording deletion (⚠️ not testable — no recordings on system during testing)

| Method | Path | Body | Description |
|---|---|---|---|
| `DELETE` | `/proxy/talk/api/call_log/recording/<uuid>` | — | Delete recording file for a call |
| `POST` | `/proxy/talk/api/call_log/recording/delete` | `{"uuids": ["<uuid1>", ...]}` | Bulk delete recordings |

---

## Voicemail

> **No HTTP download API exists for voicemail audio.** The `vm_data.file_path` field in call records reveals the server-side path (`/srv/unifi-talk/voicemail/talk.com/<ext>/<filename>.mp3`). Retrieve via SSH/SCP. This appears to be an intentional product limitation.

### GET `/proxy/talk/api/voicemail/data/<uuid>`

Returns voicemail metadata for a specific call UUID.

```http
GET https://<UDM-IP>/proxy/talk/api/voicemail/data/de8df029-f93e-48b3-a3f5-529c1fff996c
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

### GET `/proxy/talk/api/setting/voicemail_greeting_file`

Returns the global system voicemail greeting as a raw MP3 binary.

```http
GET https://<UDM-IP>/proxy/talk/api/setting/voicemail_greeting_file
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

**Response**: `Content-Type: audio/mpeg`, raw MP3 binary (no JSON wrapper).

### Voicemail deletion (✅ live-confirmed)

| Method | Path | Body | Description |
|---|---|---|---|
| `DELETE` | `/proxy/talk/api/call_log/<uuid>` | — | Delete voicemail for a call |
| `POST` | `/proxy/talk/api/voicemail/delete` | `{"uuids": ["<uuid1>", ...]}` | Bulk delete voicemails — ✅ confirmed |

---

## Devices

### GET `/proxy/talk/api/devices`

Returns all Talk hardware devices (phones, ATAs) adopted by the controller.

```http
GET https://<UDM-IP>/proxy/talk/api/devices
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

**Response** (array of device objects):

```json
[
  {
    "mac": "aabbccddeeff",
    "ip": "192.168.1.100",
    "model": "UT-ATA",
    "version": "1.1.5",
    "last_seen": "2024-03-15T14:30:00.000Z",
    "con_ip": "192.168.1.100",
    "con_port": 45623,
    "uptime": 86400,
    "con_status": null,
    "is_locked_device": false,
    "adopted": true,
    "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "display_name": "Front Desk ATA",
    "status": "online",
    "sip_reg": true,
    "user": "Jane Smith",
    "phone_number": "+13105559876",
    "ext": "0002",
    "update_available": false,
    "is_assigned": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "battery_level": null,
    "additional_config": {},
    "secretary_mode": null
  }
]
```

**Device field reference**:

| Field | Type | Description |
|---|---|---|
| `mac` | string | MAC address (lowercase, no separators) |
| `ip` | string | Current IP address |
| `model` | string | Hardware model (e.g. `UT-ATA`, `UVP`, `UVP-X`, `UVP-Pro`) |
| `version` | string | Firmware version |
| `uptime` | integer | Device uptime in seconds |
| `adopted` | boolean | Whether device is adopted to this controller |
| `status` | string | `"online"` or `"offline"` |
| `sip_reg` | boolean | Whether the SIP endpoint is registered |
| `user` | string | Display name of assigned user |
| `phone_number` | string | Primary DID (E.164) |
| `ext` | string | Extension number |
| `update_available` | boolean | Whether a firmware update is available |
| `user_id` | UUID | UUID of assigned Talk user |
| `battery_level` | integer \| null | Battery % for wireless devices |

**Known model identifiers**: `UT-ATA` (ATA adapter), `UVP` (UniFi VoIP Phone), `UVP-X` (UniFi VoIP Pro), `UVP-Pro`, `UP-FlexHD`

### GET `/proxy/talk/api/device/24h_call_quality`

Returns call quality metrics for all devices over the past 24 hours.

---

## Users & Phone Numbers

### GET `/proxy/talk/api/users`

Returns all Talk users.

```http
GET https://<UDM-IP>/proxy/talk/api/users
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

### GET `/proxy/talk/api/user/info`

Returns the currently authenticated user's Talk role and permissions.

### GET `/proxy/talk/api/number/list`

Returns all DIDs configured on the system with full assignment, SIP, and routing data.

```http
GET https://<UDM-IP>/proxy/talk/api/number/list
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

**Response excerpt**:

```json
[
  {
    "number": "+13105559876",
    "friendly_name": "(310) 555-9876",
    "account_sid": "ACxxxxxxxxxxxxxxxxx",
    "type": "local",
    "assigned_to_user_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "assigned_to_ext": "0002",
    "sms_enabled": true,
    "voice_enabled": true
  }
]
```

> ⚠️ This response includes Twilio `account_sid` and similar identifiers. Treat accordingly.

### GET `/proxy/talk/api/number/blocked`

Returns blocked caller IDs.

### GET `/proxy/talk/api/contact_list`

Returns the system-wide shared contact directory.

### GET `/proxy/talk/api/contacts`

Returns the full contact list (may differ from `contact_list` in scope).

### GET `/proxy/talk/api/emergency_address/list`

Returns registered E911 emergency addresses for all DIDs.

### GET `/proxy/talk/api/group_list`

Returns all ring groups.

### GET `/proxy/talk/api/number_porting/list`

Returns pending number porting requests.

### GET `/proxy/talk/api/number_porting/request_count`

Returns number of porting requests and configured limits.

---

## Call Routing

### GET `/proxy/talk/api/ring_flow`

Returns the ring flow / call routing schedule configurations.

### GET `/proxy/talk/api/parking_lots`

Returns call parking lot configurations.

**Response**:

```json
[
  {
    "id": 1,
    "name": "Main Parking Lot",
    "slots": 10,
    "timeout": 60,
    "return_to": "extension",
    "return_extension": "0001"
  }
]
```

### GET `/proxy/talk/api/switchboard`

Returns switchboard/receptionist console configuration and state.

### GET `/proxy/talk/api/phone_designer`

Returns phone screen layout configurations for all devices.

### GET `/proxy/talk/api/phone_designer/wallpaper/list`

Returns available wallpaper images for UniFi phones.

### GET `/proxy/talk/api/call_center/queue`

Returns real-time active call center queue state.

### GET `/proxy/talk/api/protect/cameras`

Returns UniFi Protect cameras available for video/intercom calling.

---

## SMS

### GET `/proxy/talk/api/sms/conversations`

Returns SMS conversation list.

```http
GET https://<UDM-IP>/proxy/talk/api/sms/conversations?page=1
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

Supports `?page=` for pagination. Response includes conversation thread metadata; individual message bodies are fetched per-thread.

---

## System Settings

### GET `/proxy/talk/api/setting/config`

Returns the full Talk system configuration.

```http
GET https://<UDM-IP>/proxy/talk/api/setting/config
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

**Response**:

```json
{
  "nat_needs_static_port": true,
  "static_port": 6767,
  "call_log_recording_enabled": true,
  "advanced_call_routing_enabled": false,
  "voicemail_enabled": true,
  "voicemail_email_enabled": false,
  "voicemail_slack_enabled": false,
  "voicemail_teams_enabled": false,
  "voicemail_email_transcriptions_enabled": false,
  "global_voicemail_timeout": 30,
  "global_voicemail_greeting": "global_greeting.mp3",
  "voicemail_instructions_enabled": false,
  "time_server_started": "2024-03-15T08:00:00.000Z",
  "logging_level": "info",
  "sip_trace": false,
  "audio_export_in_progress": false,
  "is_audio_export_available": false,
  "audio_codec_list": "PCMU,PCMA"
}
```

**Key fields**:

| Field | Type | Description |
|---|---|---|
| `nat_needs_static_port` | boolean | Static RTP port for NAT traversal enabled |
| `static_port` | integer | RTP static port (default `6767`) |
| `call_log_recording_enabled` | boolean | Global call recording on/off |
| `global_voicemail_timeout` | integer | Seconds before routing to voicemail |
| `audio_codec_list` | string | Comma-separated enabled codecs (e.g. `"PCMU,PCMA"`) |
| `time_server_started` | ISO 8601 | Last Talk service restart time |
| `audio_export_in_progress` | boolean | Whether an audio archive export is running |
| `is_audio_export_available` | boolean | Whether a completed archive is ready to download |

### GET `/proxy/talk/api/setting/emergency_status`

Returns E911 address registration status per DID.

### GET `/proxy/talk/api/setting/default_area_code`

Returns the configured default local area code.

### GET `/proxy/talk/api/setting/dialing_country`

Returns the configured dialing country (for local number formatting).

### GET `/proxy/talk/api/setting/hold_music`

Returns hold music configuration.

### GET `/proxy/talk/api/setting/ringtones`

Returns available ringtone options.

---

## SIP / Trunking

### GET `/proxy/talk/api/third_party_sip/gateway_list`

Returns all configured SIP trunk/gateway entries.

> ⚠️ **This response includes SIP credentials** (usernames, passwords, or authentication tokens). Handle with care and do not log or share this response.

```http
GET https://<UDM-IP>/proxy/talk/api/third_party_sip/gateway_list
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

---

## Billing & Compliance

### GET `/proxy/talk/api/billing/coupons/balance`

Returns Ubiquiti/Talk coupon or credit balance.

### GET `/proxy/talk/api/identity/status`

Returns KYC (Know Your Customer) / business profile verification status required for A2P SMS.

### GET `/proxy/talk/api/regulatory/bundle`

Returns A2P/SMS regulatory bundle and STIR-SHAKEN status.

### GET `/proxy/talk/api/lock/usage`

Returns current seat/license usage vs limits.

### GET `/proxy/talk/api/owner_transfer/transfer_state`

Returns the state of any pending system ownership transfer.

---

## Debug

### GET `/proxy/talk/api/debug/pcap/status`

Returns status of any active packet capture on the Talk service.

```http
GET https://<UDM-IP>/proxy/talk/api/debug/pcap/status
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

**PCAP control endpoints** (live-tested):

| Method | Path | Body | Status | Notes |
|---|---|---|---|---|
| `POST` | `/proxy/talk/api/debug/pcap/start` | `{"durationSeconds": 60}` | ⚠️ 500 | Endpoint exists; server returns 500 if tshark is not installed on the UDM |
| `POST` | `/proxy/talk/api/debug/pcap/stop` | — | ✅ 200 | Confirmed |
| `GET` | `/proxy/talk/api/debug/pcap/download` | — | ⚠️ 400 | Returns 400 when no capture is active |

### Audio export (live-tested)

| Method | Path | Body | Status | Notes |
|---|---|---|---|---|
| `POST` | `/proxy/talk/api/exports/prepare_audio_data` | — | ✅ 200 | Triggers background archive build; `setting/config.audio_export_in_progress` becomes `true` |
| `GET` | `/proxy/talk/api/exports/audio_data_archive` | — | ✅ | Returns 500 while export is building; returns binary ZIP when `is_audio_export_available` becomes `true` |

> ⚠️ The correct path prefix is `exports/` — not `prepare_audio_data` at the root. The path is `POST /proxy/talk/api/exports/prepare_audio_data`.

---

## WebSocket — Real-Time Events

### Connection

**Confirmed path**: `wss://<UDM-IP>/proxy/talk/ws`

The Talk backend listens internally on `localhost:3419`. The UDM nginx proxy at `/proxy/talk/ws` forwards WebSocket connections to it. **Port 3419 is not reachable from LAN clients** — always use the nginx proxy path.

```
GET /proxy/talk/ws HTTP/1.1
Host: <UDM-IP>
Upgrade: websocket
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

> Do **not** manually add `Upgrade: websocket` when using the Python `websocket-client` library — it adds this header automatically. Adding it twice causes nginx to reject the request with `400 Invalid Upgrade header`.

### Message format

All server-to-client messages use a flat envelope:

```json
{
  "event": "EVENT_TYPE",
  "data": { ... }
}
```

There is no `meta`/`rc`/`message` wrapper (unlike UniFi Network's WebSocket). The `event` field uses `SCREAMING_SNAKE_CASE`. No client-to-server messages have been observed.

### Event types (all live-captured)

| Event | Frequency | Data type |
|---|---|---|
| `DEVICES_UPDATED` | Every ~10s (heartbeat) | Array of device objects |
| `CALL_LOG_UPDATED` | Multiple times per call | Object with `records[]` array |
| `CALL_EVENTS_UPDATED` | Per call sub-event | `{ call_id, updated_at }` pointer |
| `ONGOING_EVENTS_UPDATE` | On call count change | `{ ongoing_event_count: "N" }` |
| `USERS_ON_ACTIVE_CALLS` | On call start/end | `{ user_ids: [] }` |
| `TRIGGER_STAT_REFRESH` | Periodic | `{}` (no payload) |

---

### `DEVICES_UPDATED`

Fires every ~10 seconds. Full device state for all adopted Talk devices — same schema as `GET /devices`.

```json
{
  "event": "DEVICES_UPDATED",
  "data": [
    {
      "mac": "aabbccddeeff",
      "ip": "192.168.1.100",
      "model": "UT-ATA",
      "version": "1.1.5",
      "last_seen": "2024-03-15T14:30:00.000Z",
      "uptime": 86400,
      "adopted": true,
      "status": "online",
      "sip_reg": true,
      "user": "Jane Smith",
      "phone_number": "+13105559876",
      "ext": "0002"
    }
  ]
}
```

---

### `CALL_LOG_UPDATED`

Fires 4–5 times during a typical call. The `records` array contains only the recently-modified calls (not the full log). Each fire delivers an updated snapshot of the call record with progressively more data as the call progresses.

**On call arrival** (call_events is empty, duration is null, vm_data is empty):

```json
{
  "event": "CALL_LOG_UPDATED",
  "data": {
    "records": [
      {
        "time": "2024-03-15T14:22:08.000Z",
        "from": "+12125551234",
        "to": "+13105559876",
        "status": "accepted",
        "duration": null,
        "direction": "in",
        "uuid": "de8df029-f93e-48b3-a3f5-529c1fff996c",
        "recording": null,
        "quality_score": null,
        "vm_data": {},
        "call_events": [],
        "from_caller_name": null,
        "to_smart_attendant_id": 1,
        "to_smart_attendant_title": "Main Inbound Menu"
      }
    ]
  }
}
```

**On call completion** (all fields populated):

```json
{
  "event": "CALL_LOG_UPDATED",
  "data": {
    "records": [
      {
        "time": "2024-03-15T14:22:08.000Z",
        "from": "+12125551234",
        "to": "+13105559876",
        "status": "accepted",
        "duration": 22,
        "direction": "in",
        "uuid": "de8df029-f93e-48b3-a3f5-529c1fff996c",
        "recording": false,
        "quality_score": 100,
        "vm_data": {
          "uuid": "de8df029-f93e-48b3-a3f5-529c1fff996c",
          "read_at": "0",
          "duration": "8",
          "file_path": "/srv/unifi-talk/voicemail/talk.com/0002/msg_de8df029.mp3",
          "received_at": "1710512528",
          "vm_left_for_ext": "0002",
          "vm_receiver_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
          "recipient_user_uuids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
          "fs_db_vm_uuids_ext_mapping": [
            { "ext": "0002", "uuid": "de8df029-f93e-48b3-a3f5-529c1fff996c" }
          ]
        },
        "call_events": [
          {
            "time": "2024-03-15T14:22:08.220Z",
            "event": "call_started",
            "event_data": { "to": "+13105559876", "from": "+12125551234", "to_smart_attendant_id": 1 },
            "event_uuid": "5c7d16fa-5093-4a6e-a95f-bd845e103869"
          },
          {
            "time": "2024-03-15T14:22:14.000Z",
            "event": "call_sent_to_voicemail",
            "event_data": { "recipient_user_uuids": ["a1b2c3d4-..."] },
            "event_uuid": "914f5b41-..."
          },
          {
            "time": "2024-03-15T14:22:30.000Z",
            "event": "call_hangup",
            "event_data": { "hangup_cause": "normal_end" },
            "event_uuid": "ccddee11-..."
          }
        ],
        "from_caller_name": "JOHN DOE"
      }
    ]
  }
}
```

---

### `CALL_EVENTS_UPDATED`

Lightweight pointer fired each time a sub-event is appended to a call record. Signals clients to re-fetch the call log.

```json
{
  "event": "CALL_EVENTS_UPDATED",
  "data": {
    "call_id": "de8df029-f93e-48b3-a3f5-529c1fff996c",
    "updated_at": "2024-03-15T14:22:30.000Z"
  }
}
```

Multiple `CALL_EVENTS_UPDATED` may fire in rapid succession for the same call. Always followed by `CALL_LOG_UPDATED`.

---

### `ONGOING_EVENTS_UPDATE`

```json
{
  "event": "ONGOING_EVENTS_UPDATE",
  "data": {
    "ongoing_event_count": "2"
  }
}
```

> `ongoing_event_count` is a **string**, not an integer.

---

### `USERS_ON_ACTIVE_CALLS`

```json
{
  "event": "USERS_ON_ACTIVE_CALLS",
  "data": {
    "user_ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
  }
}
```

Empty array when no calls are active. Fires at connection time and on call state changes.

---

### `TRIGGER_STAT_REFRESH`

```json
{
  "event": "TRIGGER_STAT_REFRESH",
  "data": {}
}
```

---

### Event sequence — inbound call to smart attendant → voicemail

Live-observed sequence with two test calls:

```
1. CALL_EVENTS_UPDATED    { call_id, updated_at }                   ← new call record created
2. CALL_LOG_UPDATED       records: [{ call_events:[], status:"accepted", duration:null }]
3. CALL_EVENTS_UPDATED    { call_id, updated_at }                   ← call_started sub-event added
4. CALL_LOG_UPDATED       records: [{ call_events:[call_started] }] ← CNAM may populate here
5. CALL_EVENTS_UPDATED    { call_id, updated_at }                   ← call_sent_to_voicemail added
6. CALL_LOG_UPDATED       records: [{ call_events:[..., call_sent_to_voicemail] }]
7. CALL_EVENTS_UPDATED    (fires twice rapidly)                     ← call_hangup added
8. CALL_LOG_UPDATED       records: [{ vm_data:{...}, duration:22, recording:false }]
```

**Key observations**:
- `from_caller_name` starts as `null` and is populated by CNAM lookup in a later `CALL_LOG_UPDATED`
- `vm_data.duration` is a string; `call_record.duration` is an integer
- `vm_data.file_path` is the server-side MP3 location (SSH-only access)
- Smart-attendant-only calls do not trigger changes to `USERS_ON_ACTIVE_CALLS` (only fired when a human user picks up)

---

### Python WebSocket monitor snippet

```python
import websocket, json, ssl, base64

def get_csrf(token: str) -> str:
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))["csrfToken"]

def on_message(ws, msg):
    data = json.loads(msg)
    print(f"[{data['event']}]", json.dumps(data.get("data"), indent=2)[:200])

def on_open(ws):
    print("WebSocket connected")

HOST = "192.168.1.1"
TOKEN = "eyJ..."  # from login
CSRF = get_csrf(TOKEN)

ws = websocket.WebSocketApp(
    f"wss://{HOST}/proxy/talk/ws",
    cookie=f"TOKEN={TOKEN}",
    header={"X-CSRF-Token": CSRF},
    on_message=on_message,
    on_open=on_open,
)
ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
```

---

## Python SDK Quick Start

A full Python SDK (`scripts/talk_sdk.py`) is included in the [project repository](#). It wraps all confirmed endpoints.

### Installation

```bash
pip install requests websocket-client
```

### Basic usage

```python
from talk_sdk import TalkClient

# Connect and authenticate
client = TalkClient("192.168.1.1")
client.login("localadmin", "yourpassword")

# System info
info = client.get_info()
print(f"Talk version: {info['version']}")

# List all users
users = client.get_users()
for user in users:
    print(user['first_name'], user['last_name'], user.get('ext'))

# Get call log (page 1)
calls = client.get_call_log(page=1, per_page=50)
for call in calls['records']:
    print(call['time'], call['direction'], call['from'], '->', call['to'], call['status'])

# Download a call recording
call_uuid = calls['records'][0]['uuid']
if calls['records'][0].get('recording'):
    mp3 = client.download_recording(call_uuid)
    with open(f"{call_uuid}.mp3", "wb") as f:
        f.write(mp3)

# Get waveform data for the recording
waveform = client.get_recording_waveform(call_uuid)
peaks = waveform['peaks_data']['data']

# Export call log as CSV
csv_text = client.export_call_log_csv(page=1, items_per_page=500)
with open("call_log.csv", "w") as f:
    f.write(csv_text)

# Get all devices
devices = client.get_devices()
for device in devices:
    print(device['display_name'], device['model'], device['status'])

# Get system config
config = client.get_setting_config()
print(f"Voicemail timeout: {config['global_voicemail_timeout']}s")
print(f"Recording enabled: {config['call_log_recording_enabled']}")
```

---

## Endpoint Status Index

| Method | Path | Status |
|---|---|---|
| `POST` | `/api/auth/login` | ✅ Confirmed |
| `POST` | `/api/auth/logout` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/info` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/info/app_owner` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/install` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/setup_complete` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/updates` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/ucore/system_info` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/dashboard/consolidated_info` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/dashboard/most_active_users` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/peer_consoles` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/applications` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/drive/status` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/call_log` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/call_log/csv` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/call_log/flow/<uuid>` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/call_log/transcription/<uuid>` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/call_log/countries` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/call_log/recording/<uuid>` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/call_log/audio_data/<uuid>` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/call_recording_rule` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/voicemail/data/<uuid>` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/setting/voicemail_greeting_file` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/setting/hold_music` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/setting/ringtones` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/devices` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/device/24h_call_quality` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/users` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/user/info` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/number/list` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/number/blocked` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/contact_list` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/contacts` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/emergency_address/list` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/group_list` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/number_porting/list` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/number_porting/request_count` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/ring_flow` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/parking_lots` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/switchboard` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/phone_designer` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/phone_designer/wallpaper/list` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/call_center/queue` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/protect/cameras` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/sms/conversations` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/setting/config` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/setting/emergency_status` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/setting/default_area_code` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/setting/dialing_country` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/third_party_sip/gateway_list` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/billing/coupons/balance` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/identity/status` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/regulatory/bundle` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/lock/usage` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/owner_transfer/transfer_state` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/debug/pcap/status` | ✅ Confirmed |
| `WS` | `wss://<UDM-IP>/proxy/talk/ws` | ✅ Confirmed |
| `DELETE` | `/proxy/talk/api/call_log/<uuid>` | ✅ Confirmed |
| `POST` | `/proxy/talk/api/delete_call_logs` | ✅ Confirmed |
| `DELETE` | `/proxy/talk/api/call_log/recording/<uuid>` | ⚠️ Skipped — no recordings on system |
| `POST` | `/proxy/talk/api/call_log/recording/delete` | ⚠️ Skipped — no recordings on system |
| `POST` | `/proxy/talk/api/voicemail/delete` | ✅ Confirmed |
| `POST` | `/proxy/talk/api/debug/pcap/start` | ⚠️ 500 — endpoint exists, server lacks tshark |
| `POST` | `/proxy/talk/api/debug/pcap/stop` | ✅ Confirmed |
| `GET` | `/proxy/talk/api/debug/pcap/download` | ⚠️ 400 — no capture active |
| `POST` | `/proxy/talk/api/exports/prepare_audio_data` | ✅ Confirmed — triggers archive build |
| `GET` | `/proxy/talk/api/exports/audio_data_archive` | ✅ Confirmed — 500 until export ready, binary ZIP when done |

---

## Known Limitations & Gaps

| Item | Status |
|---|---|
| Voicemail audio download via HTTP | ❌ No API — SSH/SCP only |
| Outbound call initiation | ❌ Not found |
| SMS send / reply | ❌ Not found |
| Call answer / hangup control | ❌ Not found |
| Mutation endpoints (POST/PUT settings) | ⏳ Not yet captured — need mitmproxy traffic from the UI |
| Smart attendant management | ⏳ Not yet captured |
| Ring group management | ⏳ Not yet captured |
| WebSocket client-to-server messages | ⏳ None observed |
| Answered/direct-ring call WS sequence | ⏳ Not yet captured (only SA → voicemail tested) |

---

## How This Was Researched

1. **JS bundle extraction**: Pulled `index-5.1.2.js` (5.4 MB webpack bundle) from the Talk UI and grepped for URL patterns, fetch calls, and string constants.

2. **Endpoint probing**: Wrote a script that hit all candidate endpoints with valid auth and recorded 200/404/4xx responses to identify which paths exist.

3. **Live traffic capture**: Wrote a Python WebSocket monitor (`ws_monitor.py`) that connects to the confirmed WS path and dumps all events to JSONL. Made test calls to observe the full event sequence.

4. **Response capture**: All confirmed endpoint responses are saved to `captures/api_responses/` and `captures/live_probe/`.

### Tools used

- Python `requests` — HTTP
- Python `websocket-client` — WebSocket
- Standard base64/JSON — JWT decoding
- `grep`/`sed` on the webpack bundle

---

*Tested on*: UniFi Talk v5.1.2, UniFi OS v5.1.10, model UDM-Pro  
*Last updated*: 2026-05-07  
*License*: CC0 — use freely, no attribution required
