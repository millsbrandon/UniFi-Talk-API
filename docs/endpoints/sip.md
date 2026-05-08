# SIP Protocol — Programmatic Call Control

**Status**: ✅ Fully confirmed — registration, outbound internal calls, and outbound PSTN calls all verified live.

UniFi Talk runs **FreeSWITCH 1.10.12-release~64bit** internally. Every Talk user has a native SIP extension with credentials available via the REST API. Any SIP UA (softphone, script, hardphone) that registers with these credentials gains full call control: originate calls, answer calls, hang up, and receive real-time call state.

---

## SIP Server Details

| Parameter | Value |
|---|---|
| **Software** | FreeSWITCH 1.10.12-release~64bit (`mod_sofia`) |
| **Host** | `<UDM-IP>` (same as REST/WebSocket gateway) |
| **Port UDP** | `5060` ✅ Confirmed open |
| **Port TLS/TCP** | `5061` ✅ Confirmed open |
| **SIP domain** | `talk.com` (internal; used in From/To headers) |
| **Auth** | RFC 3261 Digest MD5 |
| **Header style** | RFC 3261 **compact headers** (`v:`, `f:`, `t:`, `i:`, `l:`, `k:`) |

> **Important**: FreeSWITCH uses compact header names in all responses. SIP libraries that only parse `"Name: value"` format (splitting on `": "`) will crash with an `IndexError`. Always expand compact headers before parsing. See the mapping table below.

### Compact Header Map

| Compact | Full Name |
|---|---|
| `v` | `Via` |
| `f` | `From` |
| `t` | `To` |
| `i` | `Call-ID` |
| `m` | `Contact` |
| `l` | `Content-Length` |
| `c` | `Content-Type` |
| `s` | `Subject` |
| `e` | `Content-Encoding` |
| `o` | `Event` |
| `u` | `Allow-Events` |
| `r` | `Refer-To` |
| `b` | `Referred-By` |
| `k` | `Supported` |

---

## Getting SIP Credentials

SIP credentials are returned by the REST API for every user. No separate provisioning step is needed.

```http
GET https://<UDM-IP>/proxy/talk/api/users
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

Each user object contains:

```json
{
  "id": 1,
  "ext": "0001",
  "sip_password": "EQiHCi1aF9hr",
  "custom_sip_provider_id": null,
  ...
}
```

| Field | Description |
|---|---|
| `ext` | SIP username / extension number (zero-padded 4-digit string, e.g. `"0001"`) |
| `sip_password` | SIP digest password (plain text) |
| `custom_sip_provider_id` | If set, this user routes via a third-party SIP trunk instead of Twilio |

> **Security**: `sip_password` is returned in plaintext to any authenticated admin API call. Treat these credentials with the same care as API tokens. Do not log or expose them.

---

## SIP REGISTER

FreeSWITCH requires digest authentication. The first `REGISTER` returns `401 Unauthorized` with a `WWW-Authenticate` challenge; the second includes `Authorization: Digest`.

### Flow

```
Client → Server:  REGISTER sip:<UDM-IP> SIP/2.0
Server → Client:  SIP/2.0 401 Unauthorized  (WWW-Authenticate: Digest realm="<UDM-IP>", nonce="...", algorithm=MD5, qop="auth")
Client → Server:  REGISTER sip:<UDM-IP> SIP/2.0  (Authorization: Digest ...)
Server → Client:  SIP/2.0 200 OK
```

### Example REGISTER request (first attempt)

```sip
REGISTER sip:192.168.1.1 SIP/2.0
Via: SIP/2.0/UDP 192.168.1.75:5067;branch=z9hG4bKabc123;rport
From: <sip:0001@192.168.1.1>;tag=abc12345
To: <sip:0001@192.168.1.1>
Call-ID: 605e55e3ddcd4fb5bb9cdf4ebb41692c
CSeq: 1 REGISTER
Contact: <sip:0001@192.168.1.75:5067>
Max-Forwards: 70
Expires: 300
Content-Length: 0
```

### Example 401 challenge response (compact headers)

```sip
SIP/2.0 401 Unauthorized
v:SIP/2.0/UDP 192.168.1.75:5067;branch=z9hG4bKabc123;rport=5067
f:<sip:0001@192.168.1.1>;tag=reg001
t:<sip:0001@192.168.1.1>;tag=N160Sjt85Hc5m
i:605e55e3ddcd4fb5bb9cdf4ebb41692c
CSeq:1 REGISTER
User-Agent:FreeSWITCH-mod_sofia/1.10.12-release~64bit
Allow:INVITE,ACK,BYE,CANCEL,OPTIONS,MESSAGE,INFO,UPDATE,REGISTER,REFER,NOTIFY,PUBLISH,SUBSCRIBE
k:timer,path,replaces
WWW-Authenticate:Digest realm="192.168.1.1",nonce="151b3e04-0d3d-4bf8-b247-4fb77a29676f",algorithm=MD5,qop="auth"
l:0
```

### Digest computation (MD5 + qop=auth)

```
HA1 = MD5("<ext>:<realm>:<sip_password>")
HA2 = MD5("REGISTER:sip:<UDM-IP>")
response = MD5("<HA1>:<nonce>:<nc>:<cnonce>:auth:<HA2>")
```

---

## SIP INVITE (Outbound Call)

FreeSWITCH uses **407 Proxy Authentication Required** (not 401) for INVITE challenges. The `Proxy-Authenticate` header carries the challenge; the re-sent INVITE must include `Proxy-Authorization`.

> **Key difference from REGISTER**: REGISTER uses `401` + `WWW-Authenticate` / `Authorization`. INVITE uses `407` + `Proxy-Authenticate` / `Proxy-Authorization`.

### Flow — call answered

```
Client → Server:  INVITE sip:<destination>@<UDM-IP> SIP/2.0  (with SDP offer)
Server → Client:  SIP/2.0 407 Proxy Authentication Required
Client → Server:  ACK  (acknowledge the 407)
Client → Server:  INVITE sip:<destination>@<UDM-IP> SIP/2.0  (with Proxy-Authorization)
Server → Client:  SIP/2.0 100 Trying
Server → Client:  SIP/2.0 183 Session Progress  (or 180 Ringing)
Server → Client:  SIP/2.0 200 OK  (answered)
Client → Server:  ACK
  ... call in progress (RTP audio exchange) ...
Client → Server:  BYE
Server → Client:  SIP/2.0 200 OK
```

### Destinations

| Destination format | Example | Description |
|---|---|---|
| Internal extension | `0002` | Calls another UniFi Talk user by extension |
| E.164 PSTN number | `+17195551234` | Routes outbound via configured SIP trunk (Twilio etc.) |

Both formats use the same `sip:<destination>@<UDM-IP>` request-URI.

### SDP offer (minimum working)

```sdp
v=0
o=0001 123456 123456 IN IP4 192.168.1.75
s=unifi-talk-re
c=IN IP4 192.168.1.75
t=0 0
m=audio 10000 RTP/AVP 0 101
a=rtpmap:0 PCMU/8000
a=rtpmap:101 telephone-event/8000
a=fmtp:101 0-15
a=sendrecv
```

---

## MWI NOTIFY (Voicemail)

FreeSWITCH pushes Message Waiting Indicator (`NOTIFY` with `Event: message-summary`) to registered UAs automatically. These arrive on the same UDP socket as call responses and must be handled, otherwise the socket read loop will misinterpret them as call responses.

**Required behavior**: Always reply `200 OK` to any inbound `NOTIFY` or `OPTIONS` request.

### Example MWI NOTIFY

```sip
NOTIFY sip:0001@192.168.1.75:5067 SIP/2.0
v:SIP/2.0/UDP 192.168.1.1;rport;branch=z9hG4bK1839pg0p21QXD
Max-Forwards:70
f:sip:0001@talk.com;tag=481mm8pXtQtXj
t:sip:0001@talk.com
i:150d18aa-c534-123f-2995-2ef03c8ec63e
CSeq:114552362 NOTIFY
m:sip:mod_sofia@192.168.1.1:5060
o:message-summary
Subscription-State:terminated;reason=noresource
c:application/simple-message-summary
l:60

Messages-Waiting: no
Message-Account: sip:0001@talk.com
```

Note the SIP domain in `From`/`To` is `talk.com`, not the UDM IP.

---

## Allow Header (Supported Methods)

FreeSWITCH advertises these methods in all responses:

```
INVITE, ACK, BYE, CANCEL, OPTIONS, MESSAGE, INFO, UPDATE,
REGISTER, REFER, NOTIFY, PUBLISH, SUBSCRIBE
```

---

## Python Implementation

`scripts/sip_test.py` provides a complete, dependency-free raw-socket SIP implementation with:

- Compact header expansion
- MD5 Digest auth for REGISTER (401) and INVITE (407)
- MWI NOTIFY auto-reply
- Provisional response (100/180/183) handling
- ACK and BYE flow

### Credentials setup

Create `.local/sip_credentials.json` (gitignored):

```json
{
  "host": "192.168.1.1",
  "ext": "0001",
  "password": "<sip_password from GET /users>"
}
```

Optionally add `externalTestPhoneNumber` to `.local/secrets.json` for PSTN testing:

```json
{
  "host": "192.168.1.1",
  "username": "admin",
  "password": "...",
  "externalTestPhoneNumber": "+1XXXXXXXXXX"
}
```

### Usage

```bash
# Register only (confirm credentials work)
python3 scripts/sip_test.py

# Call an internal extension
python3 scripts/sip_test.py --call 0002 --hangup-after 5

# Call the test PSTN number from secrets.json
python3 scripts/sip_test.py --call external --hangup-after 10

# Call any E.164 number
python3 scripts/sip_test.py --call +17195551234 --hangup-after 5
```

### Minimal registration example (Python)

```python
import hashlib, socket, uuid

HOST = "192.168.1.1"
EXT = "0001"
PASSWORD = "EQiHCi1aF9hr"  # from GET /proxy/talk/api/users
LOCAL_IP = "192.168.1.75"  # your machine's LAN IP
LOCAL_PORT = 5067

def md5(s): return hashlib.md5(s.encode()).hexdigest()

call_id = uuid.uuid4().hex
branch = "z9hG4bK" + uuid.uuid4().hex[:12]
tag = uuid.uuid4().hex[:8]

reg = (
    f"REGISTER sip:{HOST} SIP/2.0\r\n"
    f"Via: SIP/2.0/UDP {LOCAL_IP}:{LOCAL_PORT};branch={branch};rport\r\n"
    f"From: <sip:{EXT}@{HOST}>;tag={tag}\r\n"
    f"To: <sip:{EXT}@{HOST}>\r\n"
    f"Call-ID: {call_id}\r\n"
    f"CSeq: 1 REGISTER\r\n"
    f"Contact: <sip:{EXT}@{LOCAL_IP}:{LOCAL_PORT}>\r\n"
    f"Expires: 300\r\nMax-Forwards: 70\r\nContent-Length: 0\r\n\r\n"
)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LOCAL_IP, LOCAL_PORT))
sock.settimeout(5)
sock.sendto(reg.encode(), (HOST, 5060))
resp = sock.recv(8192).decode(errors="replace")

# Parse 401 challenge
import re
nonce = re.search(r'nonce="([^"]+)"', resp).group(1)
realm = re.search(r'realm="([^"]+)"', resp).group(1)

# Compute digest
ha1 = md5(f"{EXT}:{realm}:{PASSWORD}")
ha2 = md5(f"REGISTER:sip:{HOST}")
nc, cnonce = "00000001", uuid.uuid4().hex[:8]
response = md5(f"{ha1}:{nonce}:{nc}:{cnonce}:auth:{ha2}")
auth = (
    f'Authorization: Digest username="{EXT}",realm="{realm}",'
    f'nonce="{nonce}",uri="sip:{HOST}",response="{response}",'
    f'algorithm=MD5,qop=auth,nc={nc},cnonce="{cnonce}"\r\n'
)

reg2 = (
    f"REGISTER sip:{HOST} SIP/2.0\r\n"
    f"Via: SIP/2.0/UDP {LOCAL_IP}:{LOCAL_PORT};branch={branch};rport\r\n"
    f"From: <sip:{EXT}@{HOST}>;tag={tag}\r\n"
    f"To: <sip:{EXT}@{HOST}>\r\n"
    f"Call-ID: {call_id}\r\n"
    f"CSeq: 2 REGISTER\r\n"
    f"Contact: <sip:{EXT}@{LOCAL_IP}:{LOCAL_PORT}>\r\n"
    f"Expires: 300\r\nMax-Forwards: 70\r\n{auth}Content-Length: 0\r\n\r\n"
)
sock.sendto(reg2.encode(), (HOST, 5060))
resp2 = sock.recv(8192)
print("Registered!" if b"200 OK" in resp2 else resp2.decode(errors="replace"))
sock.close()
```

---

## Third-Party SIP Gateway API

Talk also exposes its **SIP trunk configuration** (outbound PSTN routing) via REST.

### GET `/proxy/talk/api/third_party_sip/gateway_list`

**Status**: ✅ Confirmed

```http
GET https://<UDM-IP>/proxy/talk/api/third_party_sip/gateway_list
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

**Response** (example — Twilio trunk):

```json
[
  {
    "id": 1,
    "name": "My Twilio Trunk",
    "enabled": true,
    "gateway_params": {
      "proxy": "twilio.pstn.twilio.com",
      "username": "twilio",
      "password": "<REDACTED>",
      "register": "false"
    },
    "acl_ip_cidr_list": [
      "54.172.60.0/32",
      "54.172.60.1/32",
      "54.172.60.2/32",
      "54.172.60.3/32"
    ],
    "route_all_countries": false,
    "route_country_alpha_2_list": ["US"],
    "did_list": ["+12125551234"]
  }
]
```

> ⚠️ **Security**: `gateway_params.password` is returned in plaintext. This is the SIP trunk credential for your PSTN provider (e.g. Twilio). Rotate this credential if it has been exposed or logged.

---

## Talk Relay (Third-Party PBX for Gen3 Phones)

**Talk Relay** is a separate product from classic UniFi Talk. It enables **UniFi Talk Gen3 phones** to be managed remotely while registered to a **third-party PBX** (Asterisk, 3CX, Zoom Phone, RingCentral, etc.).

This is distinct from using the internal FreeSWITCH SIP server described above.

| Feature | Classic UniFi Talk | Talk Relay |
|---|---|---|
| SIP server | Internal FreeSWITCH | Your own PBX |
| Phone models | UT-ATA, UVP, UVP-X, UVP-Pro | Gen3 phones only |
| Requires cloud | No (LAN only) | Yes (Official Hosting) |
| Call control via script | Yes (via internal FreeSWITCH) | Via your PBX's API |

For full Talk Relay setup, see: https://help.ui.com/hc/en-us/articles/29219614566679

---

## Known Limitations / Open Questions

| Item | Notes |
|---|---|
| Receiving inbound calls | Not yet tested — requires binding a full SIP UA and handling INVITE from server |
| Hold / transfer | SIP `REFER` and `re-INVITE` not yet tested against UniFi FreeSWITCH |
| TLS/SRTP (port 5061) | Port confirmed open; TLS cert and SRTP negotiation not yet tested |
| RTP audio | Script sends a valid SDP offer; RTP is not processed (call connects but no audio played) |
| Extension `0000` / operator | Behavior not tested |
| `sip_password` rotation | No confirmed REST API to rotate a user's SIP password |
