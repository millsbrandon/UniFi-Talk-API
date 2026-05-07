# Call Log & Call Recording Rules

---

## GET `/proxy/talk/api/call_log`

**Status**: ✅ Confirmed — returns real call records with caller ID, direction, status, duration, voicemail data, and full call event timeline.

### Request

```http
GET https://<UDM-IP>/proxy/talk/api/call_log?page=1&per_page=50
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

### Query Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `page` | integer | **Yes** | — | 1-based page number. Omitting or using `offset`/`limit` instead returns `400 invalid page`. |
| `per_page` | integer | No | 50 | Records per page. |
| `direction` | string | No | all | Filter by direction: `in` or `out`. |
| `status` | string | No | all | Filter by call status (see status values below). |
| `did` | string | No | — | Filter by DID (E.164 format, e.g. `+12125551234`). |

> Note: The `direction`, `status`, and `did` filters are accepted (200 OK) but observed behavior suggests they may be applied server-side as soft filters — the `per_page` count can still return the full page regardless. Always paginate to get all records.

> Note: `offset`/`limit` style pagination returns `400 invalid page`. Only `page`-based pagination works.

### Response

```json
{
  "records": [
    {
      "time": "2024-11-14T02:13:08.197Z",
      "from": "+19175550001",
      "to": "+12125551234",
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
      "quality_score": 0,
      "vm_data": {
        "uuid": "de8df029-f93e-48b3-a3f5-529c1fff996c",
        "read_at": "0",
        "duration": "8",
        "file_path": "/srv/unifi-talk/voicemail/talk.com/0002/msg_2b681a8c-3726-4c37-9e16-86b714c7eddc.mp3",
        "received_at": "1731550402",
        "vm_left_for_ext": "0002",
        "vm_receiver_uuid": "a1b2c3d4-1111-2222-3333-444455556666",
        "recipient_user_uuids": [
          "a1b2c3d4-1111-2222-3333-444455556666"
        ],
        "fs_db_vm_uuids_ext_mapping": [
          {
            "ext": "0002",
            "uuid": "de8df029-f93e-48b3-a3f5-529c1fff996c"
          }
        ]
      },
      "call_events": [
        {
          "time": "2024-11-14T02:13:08.227Z",
          "event": "call_started",
          "event_data": {
            "to": "+12125551234",
            "from": "+19175550001",
            "to_user_uuid": "a1b2c3d4-1111-2222-3333-444455556666"
          },
          "event_uuid": "5c7d16fa-5093-4a6e-a95f-bd845e103869"
        },
        {
          "time": "2024-11-14T02:13:08.330Z",
          "event": "skipped_endpoints",
          "event_data": {
            "user_uuids": ["a1b2c3d4-1111-2222-3333-444455556666"],
            "device_macs": [],
            "contact_uuids": [],
            "external_dids": []
          },
          "event_uuid": "914f5b41-22b0-4cd6-9ecd-a4448c3cfc74"
        },
        {
          "time": "2024-11-14T02:13:08.339Z",
          "event": "call_sent_to_voicemail",
          "event_data": {},
          "event_uuid": "..."
        }
      ]
    }
  ]
}
```

### Field Reference

| Field | Type | Description |
|---|---|---|
| `time` | ISO 8601 string | Call start timestamp (UTC) |
| `from` | string | Caller number in E.164 format (e.g. `+19175550001`) or extension (e.g. `0002`) |
| `to` | string | Callee number in E.164 format or extension |
| `answered_by` | string or null | User UUID of the person who answered; `null` if missed/voicemail |
| `status` | string | Call outcome (see status values below) |
| `duration` | integer | Call duration in seconds |
| `recording_filename` | string or null | Filename of call recording if recorded; `null` if not recorded |
| `is_video_call` | boolean | Whether this was a video call |
| `is_intercom_call` | boolean | Whether this was an internal intercom call |
| `is_group_intercom_call` | boolean | Whether this was a group intercom call |
| `direction` | string | `"in"` (inbound) or `"out"` (outbound) |
| `uuid` | string (UUID) | Unique identifier for this call record |
| `country` | string | 2-letter country code of the caller |
| `recording` | boolean | Whether a recording exists for this call |
| `quality_score` | integer | MOS-like quality score (0 = no data) |
| `vm_data` | object or null | Voicemail metadata if the call went to voicemail (see below) |
| `call_events` | array | Ordered timeline of call events (see below) |

### `vm_data` Fields

Present only when `status == "voicemail"`.

| Field | Type | Description |
|---|---|---|
| `uuid` | string | Matches the call's `uuid` |
| `read_at` | string | Unix timestamp string when voicemail was listened to; `"0"` = unread |
| `duration` | string | Duration of the voicemail message in seconds (as string) |
| `file_path` | string | Absolute server-side path to the MP3 file |
| `received_at` | string | Unix timestamp string when voicemail was received |
| `vm_left_for_ext` | string | Extension that received the voicemail |
| `vm_receiver_uuid` | string | User UUID of the voicemail recipient |
| `recipient_user_uuids` | array | All user UUIDs who should receive this voicemail |
| `fs_db_vm_uuids_ext_mapping` | array | Maps each extension to its voicemail UUID |

### `call_events` Event Types

| `event` value | Description |
|---|---|
| `call_started` | Call arrived/initiated |
| `skipped_endpoints` | Endpoints (users/devices) that were bypassed during routing |
| `call_sent_to_voicemail` | Call was routed to voicemail |
| `call_answered` | Call was answered |
| `call_ended` | Call terminated |
| `call_missed` | Call rang but was not answered and did not go to voicemail |
| `call_refused` | Call was declined |
| `call_forwarded` | Call was forwarded to another destination |

### Call Status Values

| `status` | Description |
|---|---|
| `voicemail` | Caller left a voicemail |
| `refused` | Call was declined (busy/rejected) |
| `answered` | Call was answered |
| `missed` | Call rang but was not picked up or left voicemail |
| `forwarded` | Call was forwarded |

### Pagination Example

```python
import requests

def get_all_call_logs(session, host):
    """Fetch every page of call log records."""
    B = f"https://{host}/proxy/talk/api"
    all_records = []
    page = 1
    while True:
        r = session.get(f"{B}/call_log", params={"page": page, "per_page": 50})
        r.raise_for_status()
        records = r.json().get("records", [])
        if not records:
            break
        all_records.extend(records)
        if len(records) < 50:
            break
        page += 1
    return all_records
```

---

## GET `/proxy/talk/api/call_log/countries`

**Status**: ✅ Confirmed — returns the set of countries represented in the call log (useful for building filter UIs).

```http
GET https://<UDM-IP>/proxy/talk/api/call_log/countries
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

### Response

```json
["US", "CA", "GB"]
```

Array of ISO 3166-1 alpha-2 country codes.

---

## GET `/proxy/talk/api/call_recording_rule`

**Status**: ✅ Confirmed — returns call recording rules configured in Talk settings.

```http
GET https://<UDM-IP>/proxy/talk/api/call_recording_rule
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

### Response

```json
[
  {
    "id": 1,
    "dids": [],
    "direction": "in+out",
    "record_announcement_text": "",
    "record_announcement_file_path": null,
    "should_record_internal_calls": true,
    "play_record_announcement_for_internal_calls": false
  }
]
```

### Field Reference

| Field | Type | Description |
|---|---|---|
| `id` | integer | Rule ID |
| `dids` | array | List of DIDs this rule applies to; empty = applies to all |
| `direction` | string | Which call directions to record: `"in"`, `"out"`, or `"in+out"` |
| `record_announcement_text` | string | Text for TTS announcement played before recording starts |
| `record_announcement_file_path` | string or null | Path to custom audio file played as recording announcement |
| `should_record_internal_calls` | boolean | Whether to record extension-to-extension calls |
| `play_record_announcement_for_internal_calls` | boolean | Whether to play recording announcement for internal calls |

---

## GET `/proxy/talk/api/dashboard/consolidated_info`

**Status**: ✅ Confirmed — high-level system summary used by the Talk dashboard.

```http
GET https://<UDM-IP>/proxy/talk/api/dashboard/consolidated_info
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

### Response (abbreviated)

```json
{
  "consoleShortname": "UDMPRO",
  "consoleName": "My UDM Pro",
  "talkServiceEnabled": true,
  "gatewayIp": "<gateway-ip>",
  "systemStartupUnix": 1746573232
}
```

---

## GET `/proxy/talk/api/info`

**Status**: ✅ Confirmed — system-level Talk info including version, region, and feature flags.

```http
GET https://<UDM-IP>/proxy/talk/api/info
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

### Response

```json
{
  "version": "5.1.2",
  "setup_complete": true,
  "default_country_code": "+1",
  "default_country": "US",
  "default_area_code": "212",
  "controller_region": "New York",
  "controller_region_code": "NY",
  "controller_latitude": 40.7128,
  "controller_longitude": -74.0060,
  "ivr_custom_recording_max_mb": 5,
  "vm_custom_greeting_max_mb": 5,
  "has_custom_gateways": true,
  "is_hdd_available": true,
  "is_ssd_available": false,
  "call_recordings_available": true,
  "has_switchboard": false,
  "has_enabled_gateways": true,
  "host_device_name": "My UDM Pro",
  "host_device_model": "UDMPRO",
  "host_device_serial": "aabbccddeeff",
  "anonymous_controller_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "update_channel": "beta",
  "identity_service_status": {
    "uid": { "enabled": false, "running": false },
    "talk": {
      "is_installed": true,
      "is_configured": true,
      "running": true,
      "assigned": false,
      "updating": false,
      "enabled": false
    }
  },
  "region_has_talk_service_support": true
}
```

---

## GET `/proxy/talk/api/call_log/flow/<uuid>`

**Status**: ✅ Confirmed — returns the full event timeline for a specific call.

```http
GET https://<UDM-IP>/proxy/talk/api/call_log/flow/<call_uuid>
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

Similar to `call_events` embedded in call_log records, but includes additional internal routing events not always surfaced in the main call_log response.

**Response** (array of event objects):
```json
[
  {
    "time": "2024-09-09T22:34:55.592Z",
    "event": "call_started",
    "event_data": {
      "to": "+12125551234",
      "from": "+19175550001",
      "to_user_uuid": "a1b2c3d4-1111-2222-3333-444455556666"
    },
    "event_uuid": "a2142a65-4d1c-4106-bbaa-3dc57f32179a"
  },
  {
    "time": "2024-09-09T22:34:55.642Z",
    "event": "seq_call_trying_endpoints",
    "event_data": {
      "user_uuids": ["a1b2c3d4-1111-2222-3333-444455556666"],
      "device_macs": ["70:a7:41:xx:xx:xx"]
    },
    "event_uuid": "..."
  }
]
```

---

## GET `/proxy/talk/api/call_log/transcription/<uuid>`

**Status**: ✅ Confirmed — returns AI transcription data for a call.

```http
GET https://<UDM-IP>/proxy/talk/api/call_log/transcription/<call_uuid>
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

**Response**:
```json
{
  "status": null,
  "transcript": null,
  "version": 1,
  "call_uuid": "48ad2b5c-12e3-4d82-8b3a-c9a90987f4e4"
}
```

> **Note**: Returns `{status: null, transcript: null}` if AI transcription is not enabled in Talk settings or the transcription hasn't been generated yet. Enable the feature in Talk → Settings → AI & Transcription first.

---

## GET `/proxy/talk/api/call_log/csv`

**Status**: ✅ Confirmed — exports call log as CSV.

```http
GET https://<UDM-IP>/proxy/talk/api/call_log/csv?page=1&items_per_page=50
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

### ⚠️ Parameter Name Difference

The CSV endpoint uses `items_per_page` (NOT `per_page`). Using `per_page` returns `400 invalid items per page`.

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `page` | integer | **Yes** | 1-based page number |
| `items_per_page` | integer | **Yes** | Records per page (e.g. 50, 100, 500) |
| `direction` | string | No | Filter: `in` or `out` |
| `status` | string | No | Filter by call status |
| `did` | string | No | Filter by DID |

**Response** (`text/csv`):
```
time,from,to,answered_by,status,duration,recording_filename,is_video_call,is_intercom_call,is_group_intercom_call,queue_name
2024-12-03T21:28:08.172Z,+19175550001,+12125551234,,voicemail,11,,false,false,false,
2024-09-09T22:34:55.592Z,+19175550002,+12125551234,a1b2c3d4...,answered,95,,false,false,false,
```

### CSV Columns

| Column | Description |
|---|---|
| `time` | Call start time (ISO 8601 UTC) |
| `from` | Caller number (E.164) |
| `to` | Called number (E.164) |
| `answered_by` | User UUID who answered (empty if missed/voicemail) |
| `status` | Call outcome |
| `duration` | Duration in seconds |
| `recording_filename` | Recording filename (empty if not recorded) |
| `is_video_call` | `true`/`false` |
| `is_intercom_call` | `true`/`false` |
| `is_group_intercom_call` | `true`/`false` |
| `queue_name` | Call center queue name (empty if not from a queue) |

---

## GET `/proxy/talk/api/voicemail/data/<uuid>`

**Status**: ✅ Confirmed — returns voicemail metadata by UUID.

```http
GET https://<UDM-IP>/proxy/talk/api/voicemail/data/<vm_uuid>
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

**Response**:
```json
{
  "uuid": "de8df029-f93e-48b3-a3f5-529c1fff996c",
  "read_at": "0",
  "duration": "8",
  "file_path": "/srv/unifi-talk/voicemail/talk.com/0002/msg_2b681a8c-3726-4c37-9e16-86b714c7eddc.mp3",
  "received_at": "1731550402",
  "vm_left_for_ext": "0002",
  "vm_receiver_uuid": "a1b2c3d4-1111-2222-3333-444455556666",
  "recipient_user_uuids": ["a1b2c3d4-1111-2222-3333-444455556666"],
  "fs_db_vm_uuids_ext_mapping": [
    {"ext": "0002", "uuid": "de8df029-f93e-48b3-a3f5-529c1fff996c"}
  ]
}
```

> **Note**: Voicemail audio is **not downloadable via HTTP**. The `file_path` is server-side only. Retrieve via SSH/SCP:  
> `scp root@<UDM-IP>:/srv/unifi-talk/voicemail/talk.com/0002/msg_<uuid>.mp3 .`

---

## DELETE / POST — Call Log & Recording Deletion

These paths are confirmed from JS bundle analysis. Not yet live-tested.

| Method | Path | Body | Description |
|---|---|---|---|
| `DELETE` | `/proxy/talk/api/call_log/<uuid>` | — | Delete single call log record |
| `POST` | `/proxy/talk/api/delete_call_logs` | `{"uuids":[...]}` | Bulk delete call log records |
| `DELETE` | `/proxy/talk/api/call_log/recording/<uuid>` | — | Delete recording for a call |
| `POST` | `/proxy/talk/api/call_log/recording/delete` | `{"uuids":[...]}` | Bulk delete recordings |
| `POST` | `/proxy/talk/api/call_log/<uuid>/delete` | `{"ext":"0002"}` | Delete voicemail for an extension |
| `POST` | `/proxy/talk/api/voicemail/delete` | `{"uuids":[...]}` | Bulk delete voicemails |
