# Devices, Users & Phone Numbers

---

## GET `/proxy/talk/api/devices`

**Status**: ✅ Confirmed — returns all UniFi Talk hardware devices (phones, ATAs) adopted by the controller.

```http
GET https://<UDM-IP>/proxy/talk/api/devices
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

### Response

Returns a JSON array of device objects.

```json
[
  {
    "mac": "aabbccddeeff",
    "ip": "192.168.1.253",
    "model": "UT-ATA",
    "sshd_port": 22,
    "mgmt_is_default": false,
    "version": "1.1.5",
    "last_seen": "2026-05-06T22:38:12.216Z",
    "con_ip": "192.168.1.253",
    "con_port": 33537,
    "uptime": 6712793,
    "con_status": null,
    "hashed_key": "a24ea7f4a26a9f3edaa04692c6c43f2a39ff4c3df2a7e611c47cd0bb3b90f8e3...",
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
    "last_inform": "2026-05-06T22:38:12.236Z",
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
```

### Device Field Reference

| Field | Type | Description |
|---|---|---|
| `mac` | string | Device MAC address (lowercase, no separators) |
| `ip` | string | Current IP address |
| `model` | string | Hardware model (e.g. `UT-ATA`, `UAP-FlexHD`, `UVP`, `UVP-X`, `UVP-Pro`) |
| `version` | string | Firmware version |
| `last_seen` | ISO 8601 string | Last time device checked in |
| `uptime` | integer | Uptime in seconds |
| `con_ip` | string | IP address of the connection |
| `con_port` | integer | TCP port of the connection to controller |
| `con_status` | string or null | Connection status |
| `sshd_port` | integer | SSH port (default 22) |
| `status` | string | Device status: `"online"`, `"offline"`, `"adopting"`, etc. |
| `sip_reg` | boolean | Whether the device has an active SIP registration |
| `adopted` | boolean | Whether the device has been adopted |
| `display_name` | string | Human-readable device name (e.g. `UT-ATA-1A27`) |
| `user_id` | string (UUID) | UUID of the user this device is assigned to |
| `user` | string | Display name of assigned user |
| `phone_number` | string | Primary E.164 DID assigned to this device |
| `ext` | string | Extension number (zero-padded, e.g. `"0002"`) |
| `update_available` | boolean | Whether a firmware update is available |
| `battery_level` | integer or null | Battery percentage for wireless phones; `null` for wired/ATA |
| `secretary_mode` | null | Secretary/shared line mode config (null if not configured) |
| `hashed_key` | string | Device SSH host key hash |
| `anonymous_device_id` | string (UUID) | Anonymous identifier for analytics |
| `additional_data.is_autolink_device` | boolean | Whether device was auto-linked via UniFi network |

### Known Device Models

| Model | Description |
|---|---|
| `UT-ATA` | Analog Telephone Adapter (connects standard phones) |
| `UVP` | UniFi VoIP Phone (touchscreen desk phone) |
| `UVP-X` | UniFi VoIP Phone Executive |
| `UVP-Pro` | UniFi VoIP Phone Pro |
| `UAP-FlexHD` | (may appear if used as intercom via UniFi Protect) |

---

## GET `/proxy/talk/api/number/list`

**Status**: ✅ Confirmed — returns all phone numbers (DIDs) configured on the system with full user, device, and extension data.

```http
GET https://<UDM-IP>/proxy/talk/api/number/list
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

### Response

Returns a JSON array. Each element is a DID assignment with full nested user and device data.

```json
[
  {
    "did": "+12125551234",
    "total_seconds": "0",
    "sip_gateway_id": 1,
    "sip_gateway_name": "Twilio My System",
    "group_data": null,
    "user_id": "a1b2c3d4-1111-2222-3333-444455556666",
    "user": "Jane Smith",
    "user_avatar": null,
    "device": "UT-ATA-1A27",
    "device_model": "UT-ATA",
    "mac": "aabbccddeeff",
    "user_data": {
      "_id": 2,
      "unique_id": "a1b2c3d4-1111-2222-3333-444455556666",
      "first_name": "Jane",
      "last_name": "Smith",
      "full_name": "Jane Smith",
      "email": "",
      "user_email": "",
      "status": null,
      "create_time": 1708380563,
      "id": 2,
      "did": "+12125551234",
      "ext": "0002",
      "updated_at": "2026-05-06T22:27:37.821Z",
      "ulp_id": "a1b2c3d4-1111-2222-3333-444455556666",
      "outbound_caller_id": null,
      "vm_data": {},
      "active_ring_flow_id": null,
      "can_start_intercom_calls": true,
      "can_start_group_intercom_calls": false,
      "assigned_phone_design": null,
      "redirect": {},
      "talk_local_user_type": null,
      "isSelf": false,
      "has_active_calls": false,
      "hide_from_user_list": false,
      "did_list": null,
      "ring_groups": [],
      "accept_queue_calls": null,
      "custom_sip_provider_id": null,
      "scopes": [
        "identity:view:app:users",
        "identity:view:controller:access"
      ],
      "resources": {
        "wifi": false,
        "vpn": false,
        "talk": false,
        "camera": 0
      },
      "groups": [
        {
          "unique_id": "1d8504c6-e5f4-43a7-80dc-b2c344421adf",
          "name": "DreamMachinePro",
          "system_name": "DreamMachinePro"
        }
      ],
      "devices": [
        {
          "mac": "aabbccddeeff",
          "model": "UT-ATA",
          "status": "online",
          "sip_reg": true,
          "display_name": "UT-ATA-1A27",
          "ext": "0002",
          "phone_number": "+12125551234",
          "version": "1.1.5",
          "uptime": 6712793
        }
      ]
    }
  }
]
```

### Top-Level Fields

| Field | Type | Description |
|---|---|---|
| `did` | string | E.164 phone number (e.g. `+12125551234`) |
| `total_seconds` | string | Total call duration (all-time) in seconds, as string |
| `sip_gateway_id` | integer | ID of the SIP gateway handling this number |
| `sip_gateway_name` | string | Name of the SIP gateway (e.g. `"Twilio My System"`) |
| `group_data` | object or null | Ring group data if DID is assigned to a group; `null` if assigned to a user |
| `user_id` | string (UUID) | UUID of the assigned user |
| `user` | string | Display name of assigned user |
| `user_avatar` | string or null | URL to user avatar; `null` if not set |
| `device` | string | Display name of primary device |
| `device_model` | string | Hardware model of primary device |
| `mac` | string | MAC address of primary device |
| `user_data` | object | Full user record (see below) |

### `user_data` Key Fields

| Field | Type | Description |
|---|---|---|
| `unique_id` / `ulp_id` | string (UUID) | User's unique ID in UniFi identity system |
| `ext` | string | Extension number |
| `did` | string | Primary phone number |
| `outbound_caller_id` | string or null | Override caller ID for outbound calls; `null` = use DID |
| `active_ring_flow_id` | string or null | ID of active ring flow/schedule; `null` = default |
| `can_start_intercom_calls` | boolean | Whether user can initiate intercom calls |
| `ring_groups` | array | Ring groups this user belongs to |
| `vm_data` | object | Voicemail configuration (empty `{}` if no custom settings) |
| `redirect` | object | Call forwarding/redirect rules |
| `assigned_phone_design` | object or null | Custom phone screen layout |
| `devices` | array | All devices assigned to this user |

---

## GET `/proxy/talk/api/number/blocked`

**Status**: ✅ Confirmed — returns the list of blocked caller IDs.

```http
GET https://<UDM-IP>/proxy/talk/api/number/blocked
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

Returns an array of blocked numbers in E.164 format.

---

## GET `/proxy/talk/api/users`

**Status**: ✅ Confirmed — returns all Talk users (subset of identity fields).

```http
GET https://<UDM-IP>/proxy/talk/api/users
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

---

## GET `/proxy/talk/api/third_party_sip/gateway_list`

**Status**: ✅ Confirmed — returns all SIP trunk/gateway configurations.

```http
GET https://<UDM-IP>/proxy/talk/api/third_party_sip/gateway_list
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

### Response

```json
[
  {
    "id": 1,
    "name": "Twilio My System",
    "enabled": true,
    "gateway_params": {
      "proxy": "unifi-twilio.pstn.twilio.com",
      "password": "<SIP password>",
      "register": true
    }
  }
]
```

> ⚠️ **Security**: This endpoint returns SIP credentials in plaintext. Treat with care; restrict API access accordingly.

### Field Reference

| Field | Type | Description |
|---|---|---|
| `id` | integer | Gateway ID (referenced in `number/list` records) |
| `name` | string | Human-readable gateway name |
| `enabled` | boolean | Whether this gateway is active |
| `gateway_params.proxy` | string | SIP proxy hostname |
| `gateway_params.password` | string | SIP account password (**sensitive**) |
| `gateway_params.register` | boolean | Whether to actively register with the SIP proxy |

---

## GET `/proxy/talk/api/contact_list`

**Status**: ✅ Confirmed — returns the shared contact directory.

```http
GET https://<UDM-IP>/proxy/talk/api/contact_list
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

---

## GET `/proxy/talk/api/ring_flow`

**Status**: ✅ Confirmed — returns ring flow/call routing schedules.

```http
GET https://<UDM-IP>/proxy/talk/api/ring_flow
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

---

## GET `/proxy/talk/api/queues`

**Status**: ✅ Confirmed — returns call queue configurations.

```http
GET https://<UDM-IP>/proxy/talk/api/queues
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

---

## GET `/proxy/talk/api/parking_lots`

**Status**: ✅ Confirmed — returns call parking lot configurations.

```http
GET https://<UDM-IP>/proxy/talk/api/parking_lots
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

---

## GET `/proxy/talk/api/switchboard`

**Status**: ✅ Confirmed — returns switchboard/receptionist console configuration.

```http
GET https://<UDM-IP>/proxy/talk/api/switchboard
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

---

## GET `/proxy/talk/api/ring_groups`

**Status**: ✅ Confirmed — returns ring group configurations.

```http
GET https://<UDM-IP>/proxy/talk/api/ring_groups
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```
