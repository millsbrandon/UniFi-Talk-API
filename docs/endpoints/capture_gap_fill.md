# Capture Gap-Fill Endpoint Guide (2026-05-08)

This document captures endpoints observed in full browser/API capture that were not previously documented in the endpoint guides.

All requests below use the same authentication unless noted otherwise.


## Authentication

- Cookie: TOKEN=<jwt>
- Header: X-CSRF-Token: <csrf>
- Base URL: https://<UDM-IP>/proxy/talk/api


## Call Routing & Switchboard


### POST /proxy/talk/api/switchboard/setup

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- none


Example request:

```bash
curl -k -X POST 'https://<UDM-IP>/proxy/talk/api/switchboard/setup' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
{"swb_id":2}
```


### PUT /proxy/talk/api/switchboard/item

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- body: required (see example payload)


Example request:

```bash
curl -k -X PUT 'https://<UDM-IP>/proxy/talk/api/switchboard/item' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
  -H 'Content-Type: application/json' 
  --data '{"id":"swb_2","parent":null,"data":{"id":"swb_2","internal_id":2,"ext":"0010","type":"root","title":"Main Menu","numbers":["+12015550147"],"disabled":false,"greeting":"Hello, thank you for calling us.\nPlease select from...'
```

Example response (capture sample):

```json
{"id":2}
```


### PUT /proxy/talk/api/switchboard/item/swb_{id}/users

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- path: id (required)
- body: required (see example payload)


Example request:

```bash
curl -k -X PUT 'https://<UDM-IP>/proxy/talk/api/switchboard/item/swb_<id>/users' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
  -H 'Content-Type: application/json' 
  --data '[{"ulp_user":"a1b2c3d4-1111-4abc-8def-aabbccddeeff","disabled":false,"action":"ring"}]'
```

Example response (capture sample):

```json
["a1b2c3d4-1111-4abc-8def-aabbccddeeff"]
```


### DELETE /proxy/talk/api/switchboard/item/swb_{id}

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- path: id (required)


Example request:

```bash
curl -k -X DELETE 'https://<UDM-IP>/proxy/talk/api/switchboard/item/swb_<id>' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
OK
```


### DELETE /proxy/talk/api/switchboard/item/swb_{id}/user/{uuid}

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- path: uuid (required)
- path: id (required)


Example request:

```bash
curl -k -X DELETE 'https://<UDM-IP>/proxy/talk/api/switchboard/item/swb_<id>/user/<uuid>' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
OK
```


### PUT /proxy/talk/api/switchboard/time_column

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- body: required (see example payload)


Example request:

```bash
curl -k -X PUT 'https://<UDM-IP>/proxy/talk/api/switchboard/time_column' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
  -H 'Content-Type: application/json' 
  --data '{"parent_id":4,"items":[{"data":{"type":"time","title":"Non-Business Hours","greeting_type":"none","is_default_time_node":true,"holidays_enabled":false}},{"data":{"type":"time","title":"Business Hours","greeting_type":"n...'
```

Example response (capture sample):

```json
OK
```


### PUT /proxy/talk/api/group/{id}

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- path: id (required)
- body: required (see example payload)


Example request:

```bash
curl -k -X PUT 'https://<UDM-IP>/proxy/talk/api/group/<id>' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
  -H 'Content-Type: application/json' 
  --data '{"id":1,"name":"Ring Group 1","member_list":["a1b2c3d4-1111-4abc-8def-aabbccddeeff"],"member_list_meta":[{"member_id":"a1b2c3d4-1111-4abc-8def-aabbccddeeff","sequential_call_order":0,"sequential_call_leg_timeout":30,"gro...'
```

Example response (capture sample):

```json
1
```


### POST /proxy/talk/api/parking_lots/delete

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- body: required (see example payload)


Example request:

```bash
curl -k -X POST 'https://<UDM-IP>/proxy/talk/api/parking_lots/delete' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
  -H 'Content-Type: application/json' 
  --data '{"uuids":["4a79fac1-0ba7-405d-be45-1be6e300aedf"]}'
```

Example response (capture sample):

```json
OK
```


## Voicemail, TTS & Audio Assets


### GET /proxy/talk/api/user/vm_greeting_info/{id}

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- path: id (required)


Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/user/vm_greeting_info/<id>' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
{"custom_greeting_path":null,"is_user_recorded":false}
```


### GET /proxy/talk/api/user/vm_greeting_file/{id}

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- path: id (required)


Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/user/vm_greeting_file/<id>' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
no vm greeting
```


### POST /proxy/talk/api/user/vm_greeting/{uuid}

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- path: uuid (required)


Example request:

```bash
curl -k -X POST 'https://<UDM-IP>/proxy/talk/api/user/vm_greeting/<uuid>' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
{"greeting_filename":"custom_greeting_a1b2c3d4-1111-4abc-8def-aabbccddeeff.mp3","waveform_data":null}
```


### POST /proxy/talk/api/group/{id}/vm_greeting

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- path: id (required)


Example request:

```bash
curl -k -X POST 'https://<UDM-IP>/proxy/talk/api/group/<id>/vm_greeting' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
{"filename":"group_greeting_1_77b8c901-7777-4012-e435-001122445566.mp3","waveform_data":null}
```


### POST /proxy/talk/api/setting/generate_tts_file

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- body: required (see example payload)


Example request:

```bash
curl -k -X POST 'https://<UDM-IP>/proxy/talk/api/setting/generate_tts_file' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
  -H 'Content-Type: application/json' 
  --data '{"file_name":"generated-greeting.mp3","text":"Hello, you have reached Test User. Please leave a message and your contact information and I will get back to you as soon as I can.","voice_type":"voice1","voice_language":"e...'
```

Example response (capture sample):

```json
null
```


### POST /proxy/talk/api/setting/hold_music/upload

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- none


Example request:

```bash
curl -k -X POST 'https://<UDM-IP>/proxy/talk/api/setting/hold_music/upload' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
OK
```


### PUT /proxy/talk/api/setting/ringback

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- body: required (see example payload)


Example request:

```bash
curl -k -X PUT 'https://<UDM-IP>/proxy/talk/api/setting/ringback' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
  -H 'Content-Type: application/json' 
  --data '{"title":"Serene.wav","type":"standard"}'
```

Example response (capture sample):

```json
null
```


### GET /proxy/talk/api/call_recording_rule/audio/{id}

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- path: id (required)


Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/call_recording_rule/audio/<id>' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
null
```


### PUT /proxy/talk/api/call_recording_rule/{id}

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- path: id (required)


Example request:

```bash
curl -k -X PUT 'https://<UDM-IP>/proxy/talk/api/call_recording_rule/<id>' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
OK
```


## Calls, Logs & Transcript


### GET /proxy/talk/api/call_log/user/{uuid}

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- path: uuid (required)
- query: limit (required in observed UI call; example `5`)
- query: offset (required in observed UI call; example `0`)


Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/call_log/user/<uuid>?limit=5&offset=0' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
{"calls":[{"uuid":"e5f6a7b8-5555-4e0f-c213-eeff00223344","from":"0009","to":"+12015550182","direction":"out","status":"accepted","time":"2026-05-08T03:21:38.108Z","duration":40,"recording":false,"quality_score":100,"from...
```


### GET /proxy/talk/api/transcript

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- query: page (required in observed UI call; example `1`)
- query: size (required in observed UI call; example `25`)
- query: sortBy (required in observed UI call; example `call_time`)
- query: sortDirection (required in observed UI call; example `DESC`)


Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/transcript?page=1&size=25&sortBy=call_time&sortDirection=DESC' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
{"transcripts":[],"total_count":0}
```


### GET /proxy/talk/api/transcript/countries

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- none


Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/transcript/countries' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
null
```


### POST /proxy/talk/api/system_log/list

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- none


Example request:

```bash
curl -k -X POST 'https://<UDM-IP>/proxy/talk/api/system_log/list' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
{"events":[{"id":339,"event_time":"2026-05-08T04:46:17.961Z","event_type":"system","event_name":"call_settings_updated","event_level":"0","event_data":{"context":{"value":true,"setting":"acr_remote_socket_fast_timeout"},...
```


## Numbers, Billing & Compliance


### GET /proxy/talk/api/number/search

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- query: country_code (required in observed UI call; example `US`)


Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/number/search?country_code=US' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
["+13362341014","+13852334266","+13852334685","+13852336359","+13852382453","+14055169500","+14055261817","+14055262443","+14055262594","+15716774792","+15716774879","+15716778145","+15716778714","+15717137806","+1651204...
```


### POST /proxy/talk/api/number/delete_blocked

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- body: required (see example payload)


Example request:

```bash
curl -k -X POST 'https://<UDM-IP>/proxy/talk/api/number/delete_blocked' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
  -H 'Content-Type: application/json' 
  --data '{"ids":[1]}'
```

Example response (capture sample):

```json
OK
```


### GET /proxy/talk/api/lock/number/check/{e164}

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- path: e164 (required, plus-prefixed E.164 number)


Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/lock/number/check/<e164>' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
{"did":"+12015550163","lock_exp":null,"lock_mac":null}
```


### GET /proxy/talk/api/number_porting/subacc_sid

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- none


Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/number_porting/subacc_sid' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
AC<redacted>
```


### GET /proxy/talk/api/stripe/upcoming_payment

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- none


Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/stripe/upcoming_payment' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
{"upcoming_payment":9.99,"metered_amount_minutes":0,"metered_amount_sms":0,"metered_amount_cnam":0,"metered_amount_softphone":0,"subscription_amount":9.99,"subscription_plans":{"standard":{"amount":9.99,"count":1},"premi...
```


## Device & Integration


### PUT /proxy/talk/api/device/third_party

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- body: required (see example payload)


Example request:

```bash
curl -k -X PUT 'https://<UDM-IP>/proxy/talk/api/device/third_party' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
  -H 'Content-Type: application/json' 
  --data '{"device_name":"test","user_uuid":"c3d4e5f6-3333-4cde-a0f1-ccddee00ff11"}'
```

Example response (capture sample):

```json
{"device_id":"d4e5f6a7-4444-4def-b102-ddeeff112233"}
```


### PUT /proxy/talk/api/device/third_party/{uuid}

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- path: uuid (required)
- body: required (see example payload)


Example request:

```bash
curl -k -X PUT 'https://<UDM-IP>/proxy/talk/api/device/third_party/<uuid>' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
  -H 'Content-Type: application/json' 
  --data '{"device_name":"test","user_uuid":"c3d4e5f6-3333-4cde-a0f1-ccddee00ff11"}'
```

Example response (capture sample):

```json
{"device_id":"d4e5f6a7-4444-4def-b102-ddeeff112233"}
```


### GET /proxy/talk/api/protect/cameras/{hex}/snapshot

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- path: hex (required, camera id)


Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/protect/cameras/<hex>/snapshot' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
null
```


### GET /proxy/talk/api/access/doors

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- none


Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/access/doors' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
[]
```


### GET /proxy/talk/api/uids/softphone

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- none


Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/uids/softphone' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
{"available":0,"assigned":[],"maxSoftphones":0,"regionSupportsSoftphone":true}
```


### GET /proxy/talk/api/user/teleport_data/{uuid}

- Observed status: `200`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- path: uuid (required)


Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/user/teleport_data/<uuid>' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
{"min_net_version":"7.4.106","net_version_ok":true,"net_application_available":true,"teleport_feature_supported":true,"teleport_data":{},"available_sites":[{"description":"Default","id":"6244d3de6ed0410519019de6","name":...
```


## Observed But Unavailable On This Console (404)


### GET /proxy/talk/api/account/cloud_env

- Observed status: `404`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- none

- Notes: called by UI flow but returns `404` on this console/app build. Treat as unavailable/feature-gated.


Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/account/cloud_env' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
null
```


### GET /proxy/talk/api/account/cloud_urls

- Observed status: `404`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- none

- Notes: called by UI flow but returns `404` on this console/app build. Treat as unavailable/feature-gated.


Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/account/cloud_urls' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
Request failed with status code 404
```


### GET /proxy/talk/api/user/has_resources_assigned/{uuid}

- Observed status: `404`

- Authentication: `TOKEN` cookie + `X-CSRF-Token` header

- Required parameters:

- path: uuid (required)

- Notes: called by UI flow but returns `404` on this console/app build. Treat as unavailable/feature-gated.


Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/user/has_resources_assigned/<uuid>' 
  -H 'Cookie: TOKEN=<jwt>' 
  -H 'X-CSRF-Token: <csrf>'
```

Example response (capture sample):

```json
Not Found
```


---

## Session 2 Additions (2026-05-08 — Second Live Capture)

These endpoints were first observed in the second CDP capture session and were not present in the original gap-fill above.


## Ring Groups (Create)


### PUT /proxy/talk/api/group

Create a new ring group (no ID in path — server assigns and returns the integer ID).

- Observed status: `200`
- Authentication: `TOKEN` cookie + `X-CSRF-Token` header
- Method: `PUT`
- Body: required (JSON — full group object without `id`)
- Returns: integer group ID

Key body fields:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Display name for the group |
| `member_list` | string[] | User UUIDs to include |
| `member_list_meta` | object[] | Per-member config (`sequential_call_order`, `sequential_call_leg_timeout`) |
| `did_list` | string[] | E.164 DIDs assigned to the group |
| `ext_list` | string[] | Internal extensions (leave `[]` on create) |
| `group_type` | string | `"ring_group"` or `"call_queue"` |
| `call_handling` | string | `"simultaneous"` \| `"sequential"` \| `"random"` |
| `no_answer_action` | string | `"voicemail"` \| `"transfer"` \| `"drop_call"` |
| `simultaneous_ring_timeout` | int | Seconds (0 = use per-member timeout) |
| `greeting_type` | string | `"default"` \| `"generated"` \| `"custom"` |
| `voice_type` | string | TTS voice, e.g. `"voice1"` |
| `voice_language` | string | BCP-47 tag, e.g. `"en-US"` |
| `generated_greeting_text` | string | Text for TTS greeting |

Example request:

```bash
curl -k -X PUT 'https://<UDM-IP>/proxy/talk/api/group' \
  -H 'Cookie: TOKEN=<jwt>' \
  -H 'X-CSRF-Token: <csrf>' \
  -H 'Content-Type: application/json' \
  --data '{
    "name": "Ring Group 1",
    "member_list": ["a1b2c3d4-1111-4abc-8def-aabbccddeeff"],
    "member_list_meta": [{"member_id": "a1b2c3d4-1111-4abc-8def-aabbccddeeff", "sequential_call_order": 0, "sequential_call_leg_timeout": 30}],
    "did_list": ["+12015550147"],
    "ext_list": [],
    "vm_receiver_uuids": [],
    "group_type": "ring_group",
    "call_handling": "simultaneous",
    "no_answer_action": "voicemail",
    "vm_greeting": {},
    "simultaneous_ring_timeout": 0,
    "greeting_file_updated": false,
    "greeting_file": null,
    "greeting_type": "default",
    "voice_type": "voice1",
    "voice_language": "en-US",
    "generated_greeting_text": "Hello, thank you for calling us."
  }'
```

Example response:

```json
1
```

> Returns the newly created group's integer ID. Use `PUT /group/{id}` to update after creation.


## SIP Trunk Management


### PUT /proxy/talk/api/third_party_sip/gateway

Create or update a third-party SIP trunk gateway. When `id` is present in the body, this is an update; without `id` it creates a new gateway.

- Observed status: `200`
- Authentication: `TOKEN` cookie + `X-CSRF-Token` header
- Method: `PUT`
- Body: required (JSON — full gateway config object)
- Returns: `OK`

Key body fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Omit for create; set for update |
| `data.predefined_provider_id` | string | `"custom"` or a predefined provider slug |
| `data.name` | string | Display name |
| `data.enabled` | bool | Enable/disable the trunk |
| `data.gateway_params.proxy` | string | SIP proxy FQDN or IP |
| `data.gateway_params.username` | string | SIP username |
| `data.gateway_params.password` | string | SIP password |
| `data.gateway_params.register` | string | `"true"` \| `"false"` |
| `data.did_list` | string[] | E.164 DIDs routed over this trunk |
| `data.route_all_countries` | bool | Route all international calls |
| `data.route_country_alpha_2_list` | string[] | Countries to route (ISO 3166-1 alpha-2) |
| `data.acl_ip_cidr_list` | string[] | IP CIDRs to allow inbound traffic from |

Example request:

```bash
curl -k -X PUT 'https://<UDM-IP>/proxy/talk/api/third_party_sip/gateway' \
  -H 'Cookie: TOKEN=<jwt>' \
  -H 'X-CSRF-Token: <csrf>' \
  -H 'Content-Type: application/json' \
  --data '{
    "id": 1,
    "data": {
      "predefined_provider_id": "custom",
      "id": 1,
      "name": "My SIP Trunk",
      "enabled": true,
      "gateway_params": {
        "proxy": "sip.example.com",
        "username": "myuser",
        "password": "mypassword",
        "register": "true"
      },
      "did_list": ["+12015550147"],
      "route_all_countries": false,
      "route_country_alpha_2_list": ["US"],
      "acl_ip_cidr_list": ["203.0.113.0/24"]
    }
  }'
```

Example response:

```json
OK
```


## Parking Lot Management


### PUT /proxy/talk/api/parking_lot

Create or update a single parking lot. Uses singular path (vs. `GET /parking_lots` plural for listing). When no `uuid` field is in the body this creates a new lot; with `uuid` it updates.

- Observed status: `200`
- Authentication: `TOKEN` cookie + `X-CSRF-Token` header
- Method: `PUT`
- Body: required (JSON)
- Returns: `OK`

Key body fields:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Display name |
| `user_uuids` | string[] | Users allowed to park/retrieve calls |
| `group_ids` | int[] | Ring group IDs allowed to use this lot |
| `park_timeout` | int | Seconds before timeout action fires |
| `on_timeout_action` | string | `"drop_call"` \| `"transfer"` \| `"voicemail"` |
| `playback_track` | object | Music on hold: `{"title":"Piano.wav","type":"standard"}` |

Example request:

```bash
curl -k -X PUT 'https://<UDM-IP>/proxy/talk/api/parking_lot' \
  -H 'Cookie: TOKEN=<jwt>' \
  -H 'X-CSRF-Token: <csrf>' \
  -H 'Content-Type: application/json' \
  --data '{
    "name": "Sales Parking",
    "user_uuids": [],
    "group_ids": [1],
    "park_timeout": 300,
    "on_timeout_action": "drop_call",
    "playback_track": {"title": "Electronic.wav", "type": "standard"}
  }'
```

Example response:

```json
OK
```


## Number Blocking


### PUT /proxy/talk/api/number/blocked

Add a blocked number rule.

- Observed status: `200`
- Authentication: `TOKEN` cookie + `X-CSRF-Token` header
- Method: `PUT`
- Body: required (JSON)
- Returns: `{"id": {"id": <rule_id>}}`

Key body fields:

| Field | Type | Description |
|-------|------|-------------|
| `number` | string | E.164 number to block |
| `rule_type` | string | `"external"` \| `"internal"` |
| `pattern_type` | string | `"full-number"` \| `"prefix"` \| `"area-code"` |
| `direction` | string | `"in"` \| `"out"` \| `"in+out"` |
| `all_users` | bool | Apply to all users |
| `all_groups` | bool | Apply to all ring groups |
| `all_smart_attendants` | bool | Apply to all smart attendants |
| `user_ids` | int[] | Specific user IDs if `all_users=false` |
| `group_ids` | int[] | Specific group IDs if `all_groups=false` |
| `notes` | string | Optional description |

Example request:

```bash
curl -k -X PUT 'https://<UDM-IP>/proxy/talk/api/number/blocked' \
  -H 'Cookie: TOKEN=<jwt>' \
  -H 'X-CSRF-Token: <csrf>' \
  -H 'Content-Type: application/json' \
  --data '{
    "rule_type": "external",
    "pattern_type": "full-number",
    "direction": "in+out",
    "number": "+12015550199",
    "user_ids": [],
    "group_ids": [],
    "all_users": true,
    "all_groups": true,
    "all_smart_attendants": true,
    "notes": ""
  }'
```

Example response:

```json
{"id": {"id": 1}}
```


## Global Settings Mutations


### PUT /proxy/talk/api/setting/voicemail_greeting

Set or update the global voicemail greeting. Request body is typically a multipart form upload or empty when confirming a previously uploaded TTS file.

- Observed status: `200`
- Authentication: `TOKEN` cookie + `X-CSRF-Token` header
- Method: `PUT`
- Body: multipart form data (audio file) or empty JSON `{}`
- Returns: `{"greeting_filename": "<filename>.mp3"}`

Example request (empty confirm):

```bash
curl -k -X PUT 'https://<UDM-IP>/proxy/talk/api/setting/voicemail_greeting' \
  -H 'Cookie: TOKEN=<jwt>' \
  -H 'X-CSRF-Token: <csrf>'
```

Example request (upload file):

```bash
curl -k -X PUT 'https://<UDM-IP>/proxy/talk/api/setting/voicemail_greeting' \
  -H 'Cookie: TOKEN=<jwt>' \
  -H 'X-CSRF-Token: <csrf>' \
  -F 'file=@greeting.mp3'
```

Example response:

```json
{"greeting_filename": "global_greeting.mp3"}
```


### PUT /proxy/talk/api/setting/hold_music

Set the active hold music track (standard or custom).

- Observed status: `200`
- Authentication: `TOKEN` cookie + `X-CSRF-Token` header
- Method: `PUT`
- Body: required (JSON)
- Returns: `OK`

Body fields:

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Track filename, e.g. `"Piano.wav"` |
| `type` | string | `"standard"` \| `"custom"` |

Example request:

```bash
curl -k -X PUT 'https://<UDM-IP>/proxy/talk/api/setting/hold_music' \
  -H 'Cookie: TOKEN=<jwt>' \
  -H 'X-CSRF-Token: <csrf>' \
  -H 'Content-Type: application/json' \
  --data '{"title": "Piano.wav", "type": "standard"}'
```

Example response:

```json
OK
```

> Standard tracks available: `Piano.wav`, `Electronic.wav`, `Serene.wav` (and others returned by `GET /setting/hold_music`).
> Download standard track: `GET /setting/hold_music/standard/<title>`
> Upload custom track: `POST /setting/hold_music/upload` (multipart)


### PUT /proxy/talk/api/setting/default_area_code

Set the default area code used when dialing 7-digit numbers.

- Observed status: `200`
- Authentication: `TOKEN` cookie + `X-CSRF-Token` header
- Method: `PUT`
- Body: required (JSON)
- Returns: `OK`

Example request:

```bash
curl -k -X PUT 'https://<UDM-IP>/proxy/talk/api/setting/default_area_code' \
  -H 'Cookie: TOKEN=<jwt>' \
  -H 'X-CSRF-Token: <csrf>' \
  -H 'Content-Type: application/json' \
  --data '{"area_code": "415"}'
```

Example response:

```json
OK
```


## Call Recording Rules


### GET /proxy/talk/api/call_recording_rule

List all call recording rules.

- Observed status: `200`
- Authentication: `TOKEN` cookie + `X-CSRF-Token` header
- Method: `GET`
- Returns: array of recording rule objects

Response fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Rule ID (used in PUT/audio endpoints) |
| `dids` | string[] | E.164 DIDs this rule applies to |
| `direction` | string | `"in"` \| `"out"` \| `"in+out"` |
| `record_announcement_text` | string | Announcement text (empty = none) |
| `record_announcement_file_path` | string\|null | Path to announcement audio |
| `should_record_internal_calls` | bool | Whether internal calls are recorded |
| `play_record_announcement_for_internal_calls` | bool | Play announcement for internal calls |

Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/call_recording_rule' \
  -H 'Cookie: TOKEN=<jwt>' \
  -H 'X-CSRF-Token: <csrf>'
```

Example response:

```json
[
  {
    "id": 1,
    "dids": ["+12015550147"],
    "direction": "in+out",
    "record_announcement_text": "",
    "record_announcement_file_path": null,
    "should_record_internal_calls": true,
    "play_record_announcement_for_internal_calls": false
  }
]
```


## Contacts


### POST /proxy/talk/api/contacts

Create or upsert one or more contacts. Pass an array; use empty string `""` for `id` on new contacts.

- Observed status: `200`
- Authentication: `TOKEN` cookie + `X-CSRF-Token` header
- Method: `POST`
- Body: required — `{"contacts": [...]}`
- Returns: `{"inserted_uuids": [...]}`

Contact object fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Leave `""` for new; supply UUID to update |
| `first_name` | string | First name |
| `last_name` | string | Last name |
| `email` | string | Email address |
| `organization` | string | Company name |
| `title` | string | Job title |
| `avatar_filename` | string | Avatar filename or `""` |
| `contactLists` | int[] | Contact list IDs to add this contact to |
| `numbers` | object[] | Array of `{"did": "<E.164>", "label": "mobile"\|"other"\|...}` |

Example request:

```bash
curl -k -X POST 'https://<UDM-IP>/proxy/talk/api/contacts' \
  -H 'Cookie: TOKEN=<jwt>' \
  -H 'X-CSRF-Token: <csrf>' \
  -H 'Content-Type: application/json' \
  --data '{
    "contacts": [
      {
        "id": "",
        "avatar_filename": "",
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane@example.com",
        "organization": "Acme Corp",
        "title": "Engineer",
        "contactLists": [],
        "numbers": [{"did": "+12025551234", "label": "mobile"}]
      }
    ]
  }'
```

Example response:

```json
{"inserted_uuids": ["f6a7b8c9-6666-4f10-d324-ff0011334455"]}
```


### POST /proxy/talk/api/contact_list

Create a named contact list.

- Observed status: `200`
- Authentication: `TOKEN` cookie + `X-CSRF-Token` header
- Method: `POST`
- Body: required (JSON)
- Returns: the created contact list object with assigned `id`

Body fields:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Display name for the list |
| `contacts` | int[] | Contact IDs to include |

Example request:

```bash
curl -k -X POST 'https://<UDM-IP>/proxy/talk/api/contact_list' \
  -H 'Cookie: TOKEN=<jwt>' \
  -H 'X-CSRF-Token: <csrf>' \
  -H 'Content-Type: application/json' \
  --data '{"name": "VIP Customers", "contacts": [1, 2]}'
```

Example response:

```json
{"id": 1, "name": "VIP Customers", "contacts": [1, 2]}
```


## Dashboard & Analytics


### GET /proxy/talk/api/dashboard/service_health

Returns a 20-minute-bucketed health timeline for the Talk service. Used by the dashboard health graph.

- Observed status: `200`
- Authentication: `TOKEN` cookie + `X-CSRF-Token` header
- Method: `GET`
- Query params: `presetTime` — time window, e.g. `"1D"`, `"7D"`, `"30D"`
- Returns: `{"health_data": [...]}`

Response fields per bucket:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp_start` | int | Unix epoch (bucket start) |
| `timestamp_end` | int | Unix epoch (bucket end) |
| `health_score` | int | 0–100 (100 = fully healthy) |
| `events` | object[] | Monitoring events in this bucket (id, event_time, event_type, event_name, event_level, event_data) |

Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/dashboard/service_health?presetTime=1D' \
  -H 'Cookie: TOKEN=<jwt>' \
  -H 'X-CSRF-Token: <csrf>'
```

Example response (truncated):

```json
{
  "health_data": [
    {"timestamp_start": 1778127600, "timestamp_end": 1778128800, "health_score": 100, "events": []},
    {"timestamp_start": 1778208000, "timestamp_end": 1778209200, "health_score": 10, "events": [
      {"id": 230, "event_time": "2026-05-08T02:54:32.026Z", "event_type": "monitoring",
       "event_name": "pbx_restarted_too_frequent", "event_level": "3", "event_data": {},
       "event_sub_category": "status"}
    ]}
  ]
}
```

> `event_level` values: `"0"` = info, `"1"` = warning, `"3"` = critical.
> `event_name` examples: `pbx_restarted`, `pbx_restarted_too_frequent`, `registration_failed`.


### GET /proxy/talk/api/stats/calls/series

Returns call count statistics as a time series. Used by the dashboard call analytics chart.

- Observed status: `200`
- Authentication: `TOKEN` cookie + `X-CSRF-Token` header
- Method: `GET`
- Query params:
  - `presetTime` — `"1D"` \| `"7D"` \| `"30D"`
  - `tz` — UTC offset string, e.g. `"-06:00"`
- Returns: time-series call stats object (schema not captured — empty on test system)

Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/stats/calls/series?presetTime=7D&tz=-06:00' \
  -H 'Cookie: TOKEN=<jwt>' \
  -H 'X-CSRF-Token: <csrf>'
```


### GET /proxy/talk/api/billing/usage

Returns current billing usage metrics (minutes, SMS, etc.).

- Observed status: `200`
- Authentication: `TOKEN` cookie + `X-CSRF-Token` header
- Method: `GET`
- Returns: billing usage object (response body not captured — no usage on test system)

Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/billing/usage' \
  -H 'Cookie: TOKEN=<jwt>' \
  -H 'X-CSRF-Token: <csrf>'
```


## Payment Terms


### GET /proxy/talk/api/acceptance/payments

Check whether the account owner has accepted the payments/ToS agreement, and retrieve the terms URL.

- Observed status: `200`
- Authentication: `TOKEN` cookie + `X-CSRF-Token` header
- Method: `GET`
- Returns: `{"terms_url": "<url>", "accepted": <bool>}`

Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/acceptance/payments' \
  -H 'Cookie: TOKEN=<jwt>' \
  -H 'X-CSRF-Token: <csrf>'
```

Example response:

```json
{"terms_url": "https://vault.pactsafe.io/s/.../legal.html?g=37064", "accepted": true}
```


## Audio File Retrieval


### GET /proxy/talk/api/voicemail/greeting/{filename}

Download a voicemail greeting audio file (MP3). Used for both user and group voicemail greetings.

- Observed status: `200`
- Authentication: `TOKEN` cookie + `X-CSRF-Token` header
- Method: `GET`
- Path param: `filename` — MP3 filename returned by `POST /user/vm_greeting/{uuid}` or `POST /group/{id}/vm_greeting`
- Returns: binary MP3 audio

Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/voicemail/greeting/group_greeting_1_77b8c901.mp3' \
  -H 'Cookie: TOKEN=<jwt>' \
  -H 'X-CSRF-Token: <csrf>' \
  --output greeting.mp3
```


## SMS


### GET /proxy/talk/api/sms/trigger_sms_fetch

Triggers an immediate SMS fetch from the cloud backend. The UI calls this on load to ensure the local SMS store is current.

- Observed status: `200`
- Authentication: `TOKEN` cookie + `X-CSRF-Token` header
- Method: `GET`
- Returns: empty body (or `null`)

Example request:

```bash
curl -k -X GET 'https://<UDM-IP>/proxy/talk/api/sms/trigger_sms_fetch' \
  -H 'Cookie: TOKEN=<jwt>' \
  -H 'X-CSRF-Token: <csrf>'
```
