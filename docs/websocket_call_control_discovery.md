# WebSocket Call-Control Discovery

## Overview
This document summarizes real WebSocket event observations from UniFi Talk system capturing live outbound call scenarios. The data was collected via private WebSocket monitoring (`wss://192.168.1.1/proxy/talk/ws`) and analyzed to extract call-control semantics.

**Live Capture Summary**
- **Total Events Analyzed**: 141
- **Date Range**: November 2024 – May 2026 (historical + live)
- **Test Scenario**: Outbound call attempts (refused status)
- **Scenario Label**: `outbound-call-live`

---

## WebSocket Connection

### Endpoint
```
wss://<host>/proxy/talk/ws
```

### Authentication
- Token-based (same TOKEN cookie + CSRF token as REST API)
- Connection starts with device handshake and initial state sync

---

## Event Types Observed

### Top-Level Event Distribution
From 141 captured events in this session:

| Event Type | Count | Purpose |
|---|---|---|
| `DEVICES_UPDATED` | 91 | Device status, SIP registration, user assignment |
| `SYSTEM_LOG_LIST_UPDATE_TRIGGER` | 10 | System log refresh notifications |
| `BITRATE_UPDATE` | 10 | Audio quality/bitrate metrics |
| `CALL_LOG_UPDATED` | 9 | Call records with nested call lifecycle events |
| `CALL_EVENTS_UPDATED` | 6 | Real-time call event stream |
| `TRIGGER_STAT_REFRESH` | 3 | Statistics refresh signal |
| `USER_STORE_UPDATED` | 3 | User/group directory updates |
| `TALK_CONFIGURING_FSR_STARTED` / `ENDED` | 6 | Configuration state changes |
| `USERS_ON_ACTIVE_CALLS` | 2 | Active call roster |
| `ONGOING_EVENTS_UPDATE` | 1 | Ongoing event counter |

---

## Call-Control Event Analysis

### Call Lifecycle Events (Nested in CALL_LOG_UPDATED)

From captured call records, the following nested `call_events[]` are relevant for call control:

#### Call Start (Outbound)
```json
{
  "event": "call_started",
  "event_data": {
    "to": "+1-555-0100",
    "from": "EXT-001",
    "from_mac": "aabbccddee01",
    "from_user_uuid": "00000000-0000-0000-0000-000000000001"
  },
  "time": "2025-02-20T01:04:18.710Z",
  "event_uuid": "00000000-0000-0000-0000-000000000101"
}
```

#### Call Start (Inbound)
Note: inbound calls use `to_user_uuid` instead of `from_user_uuid`:
```json
{
  "event": "call_started",
  "event_data": {
    "to": "+1-555-0200",
    "from": "+1-555-0300",
    "to_user_uuid": "00000000-0000-0000-0000-000000000001"
  },
  "time": "2026-05-08T03:07:47.604Z",
  "event_uuid": "00000000-0000-0000-0000-000000000101"
}
```

#### Endpoint Sequencing (Outbound)
```json
{
  "event": "seq_call_trying_endpoints",
  "event_data": {
    "external_dids": ["+1-555-0100"]
  },
  "time": "2025-02-20T01:04:18.782Z",
  "event_uuid": "00000000-0000-0000-0000-000000000102"
}
```

#### Endpoint Sequencing (Inbound)
Inbound routing includes target user UUIDs and device MACs:
```json
{
  "event": "seq_call_trying_endpoints",
  "event_data": {
    "user_uuids": ["00000000-0000-0000-0000-000000000001"],
    "device_macs": ["aabbccddee01"]
  },
  "time": "2026-05-08T03:07:47.706Z",
  "event_uuid": "00000000-0000-0000-0000-000000000102"
}
```

#### Call Accepted
Emitted when the call is answered. Includes who answered and on which device:
```json
{
  "event": "call_accepted",
  "event_data": {
    "accepted_by": "EXT-001",
    "accepted_by_user_uuid": "00000000-0000-0000-0000-000000000001",
    "accepted_by_device_mac": "aabbccddee01"
  },
  "time": "2026-05-08T03:07:51.114Z",
  "event_uuid": "00000000-0000-0000-0000-000000000103"
}
```

#### Call Hangup (with Cause)
```json
{
  "event": "call_hangup",
  "event_data": {
    "hangup_cause": "normal_end"
  },
  "time": "2026-05-08T03:08:06.623Z",
  "event_uuid": "00000000-0000-0000-0000-000000000104"
}
```

### Call Status Lifecycle (Top-Level)
From historical call log records observed:

| Status | Count | Meaning |
|---|---|---|
| `voicemail` | 405 | Call went to voicemail |
| `refused` | 24 | Call was refused (test scenario) |
| `accepted` | 18 | Call was answered |
| `ringing` | 3 | Call in ringing state |

### Call Direction Distribution
| Direction | Count |
|---|---|
| `in` (inbound) | 423 |
| `out` (outbound) | 27 |

---

## Inbound Answered Call Example (Live Capture)

**Full lifecycle** for an inbound call that was answered then hung up from the UniFi phone side:

```
03:07:47.568Z  CALL_LOG_UPDATED  status=ringing
03:07:47.604Z    → call_started        from=+1-555-0300 to=+1-555-0200
03:07:47.706Z    → seq_call_trying_endpoints  user_uuids=[...] device_macs=[...]
03:07:51.114Z  CALL_EVENTS_UPDATED
03:07:51.114Z    → call_accepted       accepted_by=EXT-001 (device MAC + user UUID)
03:07:51.209Z  CALL_LOG_UPDATED  status=accepted, answered_by=EXT-001
                                   recording_filename set
03:08:06.623Z  CALL_EVENTS_UPDATED
03:08:06.623Z    → call_hangup         hangup_cause=normal_end
03:08:06.777Z  CALL_LOG_UPDATED  status=accepted, duration=19, recording=true, quality_score=100
```

**Top-level record fields populated after answer:**
- `answered_by`: extension that answered (e.g., `"0008"`)
- `answered_by_user_uuid` / `answered_by_device_mac` / `answered_by_mac`: set on final record
- `recording_filename`: set at answer time, format: `YYYYMMDD_HHMMSS_{from}_{to}_{uuid_prefix}.mp3`
- `recording: true` and `quality_score` (0-100) set after hangup

---

## Outbound Call Example (Live Capture)

**Raw Call Log Record** (captured during test):

```json
{
  "time": "2025-02-20T01:04:18.973Z",
  "from": "EXT-001",
  "to": "+1-555-0100",
  "status": "refused",
  "duration": 0,
  "direction": "out",
  "uuid": "00000000-0000-0000-0000-000000000201",
  "from_mac": "aabbccddee01",
  "from_id": "00000000-0000-0000-0000-000000000001",
  "from_caller_name": "Test User",
  "call_events": [
    {
      "time": "2025-02-20T01:04:18.710Z",
      "event": "call_started",
      "event_data": {
        "to": "+1-555-0100",
        "from": "EXT-001",
        "from_mac": "aabbccddee01",
        "from_user_uuid": "00000000-0000-0000-0000-000000000001"
      }
    },
    {
      "time": "2025-02-20T01:04:18.782Z",
      "event": "seq_call_trying_endpoints",
      "event_data": {
        "external_dids": ["+1-555-0100"]
      }
    },
    {
      "time": "2025-02-20T01:04:19.222Z",
      "event": "call_hangup",
      "event_data": {
        "hangup_cause": "refused"
      }
    }
  ]
}
```

**Timeline**:
- **02:04:18.710**: Call initiated (to +1-555-0100 from ext EXT-001)
- **02:04:18.782**: System attempts to route to external number (+1-555-0100)
- **02:04:19.222**: Call terminated with "refused" cause (rejected by remote)

---

## System Configuration Events

### Device Update Flow
`DEVICES_UPDATED` events contain full device state including:
- **SIP Registration Status** (`sip_reg`: true/null)
- **User Assignment** (`user_id`: UUID of assigned user)
- **Device Info** (MAC, IP, model, version)
- **Connection Status** (online/offline, con_ip, con_port)
- **Sync State** (`last_synced_contact_ids`, `last_informed`)

### Configuration Triggers
- **`TALK_CONFIGURING_FSR_STARTED`**: System begins configuration (e.g., after call, policy change)
- **`TALK_CONFIGURING_FSR_ENDED`**: Configuration complete; device may restart SIP registration
- **`SYSTEM_LOG_LIST_UPDATE_TRIGGER`**: Signals new system logs available

---

## Nested Call Event Types (Full Distribution)

Extracted from CALL_LOG_UPDATED records:

| Event | Count | Meaning |
|---|---|---|
| `call_hangup` | 843 | Call ended (various causes) |
| `call_started` | 450 | Call initiated |
| `call_sent_to_voicemail` | 423 | Routed to voicemail |
| `vm_msg_recorded` | 405 | Voicemail recorded |
| `skipped_endpoints` | 396 | No endpoints tried (likely internal logic) |
| `seq_call_trying_endpoints` | 36 | Endpoint sequence attempted |
| `vm_recording_canceled` | 9 | Voicemail recording cancelled |

---

## Implementation Notes

### For Call Initiation Detection
Monitor `CALL_LOG_UPDATED` events for records with:
- `direction: "out"`
- `call_events[]` containing `call_started` with `from_mac` (originating device)

### For Hangup Cause Classification
Extract `hangup_cause` from terminal `call_hangup` event within `call_events[]`:
- `"refused"` — Remote party rejected (outbound, receiver rejected)
- `"cancelled"` — Caller hung up before answer
- `"normal_end"` — Normal call termination after answer (confirmed: when UniFi side hangs up)

### For Real-Time Monitoring
Subscribe to both:
1. **`CALL_LOG_UPDATED`** — Historical call records (can batch multiple calls)
2. **`CALL_EVENTS_UPDATED`** — Real-time event stream (lower latency for in-progress calls)

### Device State Synchronization
Track `DEVICES_UPDATED` to maintain:
- Device → User UUID mapping
- SIP registration status (important for call origination availability)
- Device IP/port for any device-specific operations

---

## Open Questions for Further Discovery

1. **Client→Server Frames**: How to initiate calls via WebSocket (one-way stream observed)
2. ~~**Answered Call Lifecycle**~~ ✅ Resolved: `call_started` → `seq_call_trying_endpoints` → `call_accepted` → `call_hangup(normal_end)`
3. **Hold/Transfer Events**: Specific event types for hold and transfer states
4. **Recording Control**: Is `recording_filename` pre-assigned at answer time? Can recording be toggled mid-call?
5. **Call Transfer Frame Format**: WebSocket command structure to transfer call
6. **Inbound Hangup Causes**: What `hangup_cause` values appear when remote party hangs up first (vs. `normal_end` from UniFi side)?
7. **`quality_score` Timing**: Populated at hangup or async? Observed as 100 for a 19s call.

---

## Artifacts

- **Raw Capture**: `private_captures/ws_events.jsonl` (141 events, outbound-call-live scenario)
- **Summary**: `private_captures/ws_call_control_summary.json` (metrics and event distribution)
- **Sanitized Version**: `analysis/sanitized/ws_call_control_summary_outbound_live.sanitized.json` (public-safe)
