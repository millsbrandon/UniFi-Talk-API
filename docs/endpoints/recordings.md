# Recordings & Voicemail

---

## Overview

UniFi Talk stores two types of audio on the controller:

| Type | Where | How to Access |
|---|---|---|
| **Call recordings** | `/srv/unifi-talk/recordings/<uuid>` | ✅ `GET /proxy/talk/api/call_log/recording/<uuid>` returns raw MP3 |
| **Call waveform data** | Derived from recording | ✅ `GET /proxy/talk/api/call_log/audio_data/<uuid>` returns JSON peaks |
| **Voicemail messages** | `/srv/unifi-talk/voicemail/talk.com/<ext>/msg_<uuid>.mp3` | ❌ No HTTP download API — retrieve via SSH/SCP |
| **Voicemail greeting** | Server | ✅ `GET /proxy/talk/api/setting/voicemail_greeting_file` returns raw MP3 |
| **Hold music** | Server | ✅ `GET /proxy/talk/api/setting/hold_music` returns config |
| **Ringtones** | Server | ✅ `GET /proxy/talk/api/setting/ringtones` returns list |
| **Audio export archive** | Server | ⚠️ `GET /proxy/talk/api/exports/audio_data_archive` — 500 when no export queued |

---

## GET `/proxy/talk/api/call_log/recording/<uuid>`

**Status**: ✅ Confirmed — downloads the call recording as a raw MP3.

```http
GET https://<UDM-IP>/proxy/talk/api/call_log/recording/<call_uuid>
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

**Response**: Raw `audio/mpeg` binary (MP3), ~1.5 KB/sec for standard quality calls.  
Returns `404` if the call was not recorded (or if the recording file has been deleted).

**404 Error body**:
```json
{"message": "ENOENT: no such file or directory, stat '/srv/unifi-talk/recordings/<uuid>'"}
```

**SDK**:
```python
mp3_bytes = client.download_recording(call_uuid)
with open(f"{call_uuid}.mp3", "wb") as f:
    f.write(mp3_bytes)
```

**Notes**:
- The `uuid` is the `call_uuid` from the call log record — NOT the `recording_filename` field (which is always null in the API despite recordings existing).
- Files live at `/srv/unifi-talk/recordings/<uuid>` on the UDM filesystem.

---

## GET `/proxy/talk/api/call_log/audio_data/<uuid>`

**Status**: ✅ Confirmed — returns waveform peaks data for rendering a waveform player in the UI.

```http
GET https://<UDM-IP>/proxy/talk/api/call_log/audio_data/<call_uuid>
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
    "data": [0, 12, 3, 8, ...]
  },
  "recording_file_type": "mp3"
}
```

---

## DELETE `/proxy/talk/api/call_log/recording/<uuid>`

**Status**: ⏳ From JS bundle — not yet live-tested.

Deletes the recording file for a specific call. Irreversible.

---

## POST `/proxy/talk/api/call_log/recording/delete`

**Status**: ⏳ From JS bundle — not yet live-tested.

Bulk delete recording files.

```json
{ "uuids": ["<call_uuid_1>", "<call_uuid_2>"] }
```

---

## GET `/proxy/talk/api/setting/voicemail_greeting_file`

**Status**: ✅ Confirmed — returns raw MP3 binary of the system voicemail greeting.

```http
GET https://<UDM-IP>/proxy/talk/api/setting/voicemail_greeting_file
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

**Response**: Raw `audio/mpeg` binary (MP3). No JSON wrapper.

```
Content-Type: audio/mpeg
Content-Length: <size>

<binary MP3 data>
```

**Notes**:
- This is the **global** voicemail greeting played to all callers.
- Per-user greetings are stored on the filesystem at paths like:  
  `/srv/unifi-talk/voicemail/talk.com/<ext>/greeting.mp3`  
  but there is no confirmed API to retrieve them without filesystem access.

---

## GET `/proxy/talk/api/setting/hold_music`

**Status**: ✅ Confirmed (200 OK). Returns the hold music configuration or binary.

```http
GET https://<UDM-IP>/proxy/talk/api/setting/hold_music
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

---

## GET `/proxy/talk/api/setting/ringtones`

**Status**: ✅ Confirmed (200 OK). Returns available ringtone options.

```http
GET https://<UDM-IP>/proxy/talk/api/setting/ringtones
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

---

## Voicemail Data in Call Log

The most reliable way to access voicemail metadata is through the call log. When a call goes to voicemail, the `vm_data` object is populated in the call record:

```json
{
  "status": "voicemail",
  "vm_data": {
    "uuid": "de8df029-f93e-48b3-a3f5-529c1fff996c",
    "read_at": "0",
    "duration": "8",
    "file_path": "/srv/unifi-talk/voicemail/talk.com/0002/msg_2b681a8c-3726-4c37-9e16-86b714c7eddc.mp3",
    "received_at": "1731550402",
    "vm_left_for_ext": "0002",
    "vm_receiver_uuid": "a1b2c3d4-1111-2222-3333-444455556666",
    "recipient_user_uuids": ["a1b2c3d4-1111-2222-3333-444455556666"],
    "fs_db_vm_uuids_ext_mapping": [
      { "ext": "0002", "uuid": "de8df029-f93e-48b3-a3f5-529c1fff996c" }
    ]
  }
}
```

The `file_path` field gives the absolute path on the UDM filesystem. The files can be accessed via SSH if needed.

**To enumerate all voicemails**:
```python
import requests

def get_voicemails(session, host):
    """Pull all call log records that have voicemail."""
    B = f"https://{host}/proxy/talk/api"
    all_vms = []
    page = 1
    while True:
        r = session.get(f"{B}/call_log", params={"page": page, "per_page": 50})
        records = r.json().get("records", [])
        if not records:
            break
        for rec in records:
            if rec.get("status") == "voicemail" and rec.get("vm_data"):
                all_vms.append(rec)
        if len(records) < 50:
            break
        page += 1
    return all_vms
```

---

## Call Recording Files

When a call is recorded, the `call_log` record will have:
- `"recording": true`
- `"recording_filename": "<filename>"` (non-null string)

> ⚠️ **No confirmed download API**: All attempts to reach recording files via the API returned 404. The confirmed paths that do NOT work include:
> - `/proxy/talk/api/voicemail` → 404
> - `/proxy/talk/api/voicemail/recording` → 404
> - `/proxy/talk/api/voicemail/recordings` → 404
> - `/proxy/talk/api/voicemail/list` → 404

> The `recording_filename` field was `null` in all currently observed call records (recording feature is enabled in config but no recorded calls exist in the test dataset). When a non-null `recording_filename` is found, candidate download paths to try are:
> - `GET /proxy/talk/api/call_log/<uuid>/recording`
> - `GET /proxy/talk/api/recording/<recording_filename>`
> - `GET /proxy/talk/api/recordings/<recording_filename>`

---

## GET `/proxy/talk/api/exports/audio_data_archive`

**Status**: ⚠️ Exists but returns 500 when no export has been queued.

This endpoint appears to download a bulk audio export archive (ZIP of all recordings/voicemails). The export must first be triggered via a separate mechanism (likely a POST) before the archive is available for download.

```http
GET https://<UDM-IP>/proxy/talk/api/exports/audio_data_archive
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

**Response when no export queued**: `500 Internal Server Error`

The `setting/config` response includes:
```json
{
  "audio_export_in_progress": false,
  "is_audio_export_available": false
}
```

When `is_audio_export_available` is `true`, this endpoint should return the archive binary.

---

## Audio Codec Configuration

From `GET /proxy/talk/api/setting/config`:

```json
{
  "audio_codec_list": "PCMU,PCMA"
}
```

Supported codecs: **PCMU** (G.711 µ-law) and **PCMA** (G.711 A-law). These are standard 8kHz telephony codecs. Recordings are stored as MP3.
