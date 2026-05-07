# System Settings & Configuration

---

## GET `/proxy/talk/api/setting/config`

**Status**: ✅ Confirmed — returns the full Talk system configuration.

```http
GET https://<UDM-IP>/proxy/talk/api/setting/config
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

### Response

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
  "emergency_status": {
    "address": {
      "sid": "AD32ecadebdd3c1fda805fe6becf79a5f7",
      "customer_name": "System Owner",
      "street": "123 EXAMPLE ST",
      "street_secondary": null,
      "city": "ANYTOWN",
      "region": "CO",
      "postal_code": "10001",
      "iso_country": "US",
      "state": "valid",
      "address_type": null
    },
    "pending_changes": false,
    "all_active": true,
    "all_inactive": true
  },
  "time_server_started": "2026-05-06T22:27:36.438Z",
  "owner_full_name": "System Owner",
  "owner_email": "admin@example.com",
  "logging_level": "info",
  "sip_trace": false,
  "audio_export_in_progress": false,
  "is_audio_export_available": false,
  "audio_codec_list": "PCMU,PCMA"
}
```

### Field Reference

| Field | Type | Description |
|---|---|---|
| `nat_needs_static_port` | boolean | Whether a static RTP port is configured for NAT traversal |
| `static_port` | integer | Static RTP port for NAT (default `6767`) |
| `call_log_recording_enabled` | boolean | Whether call recording is globally enabled |
| `advanced_call_routing_enabled` | boolean | Whether advanced ring flow routing is enabled |
| `voicemail_enabled` | boolean | Whether voicemail is enabled system-wide |
| `voicemail_email_enabled` | boolean | Whether voicemail-to-email is enabled |
| `voicemail_slack_enabled` | boolean | Whether voicemail Slack notifications are enabled |
| `voicemail_teams_enabled` | boolean | Whether voicemail Microsoft Teams notifications are enabled |
| `voicemail_email_transcriptions_enabled` | boolean | Whether voicemail transcription in email is enabled |
| `global_voicemail_timeout` | integer | Seconds before calls are routed to voicemail (default `30`) |
| `global_voicemail_greeting` | string | Filename of the global voicemail greeting MP3 |
| `voicemail_instructions_enabled` | boolean | Whether recorded instructions are played before voicemail beep |
| `emergency_status` | object | 911/E911 address registration status (see below) |
| `time_server_started` | ISO 8601 string | When the Talk service last started |
| `owner_full_name` | string | Full name of the system owner |
| `owner_email` | string | Email of the system owner |
| `logging_level` | string | Server log level: `"info"`, `"debug"`, `"warn"`, `"error"` |
| `sip_trace` | boolean | Whether SIP protocol tracing is enabled (debug use) |
| `audio_export_in_progress` | boolean | Whether an audio archive export is currently being generated |
| `is_audio_export_available` | boolean | Whether an audio archive is ready for download |
| `audio_codec_list` | string | Comma-separated list of enabled audio codecs |

### `emergency_status.address` Fields

| Field | Type | Description |
|---|---|---|
| `sid` | string | Twilio address SID for E911 registration |
| `customer_name` | string | Name on the E911 registration |
| `street` | string | Street address |
| `city` | string | City |
| `region` | string | State/region code |
| `postal_code` | string | ZIP/postal code |
| `iso_country` | string | ISO 3166-1 alpha-2 country code |
| `state` | string | Validation state: `"valid"`, `"pending"`, `"error"` |

---

## GET `/proxy/talk/api/setting/emergency_status`

**Status**: ✅ Confirmed — returns the E911 emergency address registration status for all DIDs.

```http
GET https://<UDM-IP>/proxy/talk/api/setting/emergency_status
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

---

## GET `/proxy/talk/api/setting/voicemail_greeting_file`

**Status**: ✅ Confirmed — returns raw MP3 binary of the global voicemail greeting.

```http
GET https://<UDM-IP>/proxy/talk/api/setting/voicemail_greeting_file
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

**Response**: Raw `audio/mpeg` binary (no JSON wrapper).

---

## GET `/proxy/talk/api/setting/hold_music`

**Status**: ✅ Confirmed (200 OK).

```http
GET https://<UDM-IP>/proxy/talk/api/setting/hold_music
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

---

## GET `/proxy/talk/api/setting/ringtones`

**Status**: ✅ Confirmed (200 OK) — returns available ringtone options for devices.

```http
GET https://<UDM-IP>/proxy/talk/api/setting/ringtones
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

---

## GET `/proxy/talk/api/ucore/system_info`

**Status**: ✅ Confirmed — returns UniFi OS core system information.

```http
GET https://<UDM-IP>/proxy/talk/api/ucore/system_info
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

---

## GET `/proxy/talk/api/install`

**Status**: ✅ Confirmed — returns Talk installation/onboarding status.

```http
GET https://<UDM-IP>/proxy/talk/api/install
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

---

## GET `/proxy/talk/api/applications`

**Status**: ✅ Confirmed — returns installed application configurations.

```http
GET https://<UDM-IP>/proxy/talk/api/applications
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

---

## GET `/proxy/talk/api/peer_consoles`

**Status**: ✅ Confirmed — returns information about peer UniFi consoles on the network.

```http
GET https://<UDM-IP>/proxy/talk/api/peer_consoles
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

---

## GET `/proxy/talk/api/protect/cameras`

**Status**: ✅ Confirmed — returns UniFi Protect camera list (used for video calling / door intercom integration).

```http
GET https://<UDM-IP>/proxy/talk/api/protect/cameras
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

---

## GET `/proxy/talk/api/sms/conversations`

**Status**: ✅ Confirmed — returns SMS conversation list (requires SMS capability on gateway).

```http
GET https://<UDM-IP>/proxy/talk/api/sms/conversations
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

---

## GET `/proxy/talk/api/phone_designer`

**Status**: ✅ Confirmed — returns phone screen layout/designer configurations.

```http
GET https://<UDM-IP>/proxy/talk/api/phone_designer
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```
