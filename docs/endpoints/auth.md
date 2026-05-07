# Authentication

> **Base URL for Talk API**: `https://<UDM-IP>/proxy/talk/api`  
> **Base URL for UniFi OS auth**: `https://<UDM-IP>/api/auth`  
> All Talk endpoints sit behind the `/proxy/talk/` reverse proxy on the UDM/UDM-Pro.

---

## POST `/api/auth/login`

**Status**: ✅ Confirmed — live-tested against UDM-Pro running UniFi OS with Talk v5.1.2

> ⚠️ **Local accounts only**: This endpoint only works with accounts created as **Local Access Only** on the console. Cloud/SSO (Ubiquiti account) users require a separate OAuth flow that is not scriptable the same way.

> ⚠️ **Rate Limit**: After ~5 failed login attempts the server returns `429 AUTHENTICATION_FAILED_LIMIT_REACHED`. Wait ~3 minutes for the lockout to clear before retrying.

### Request

```http
POST https://<UDM-IP>/api/auth/login
Content-Type: application/json

{
  "username": "localadmin",
  "password": "yourpassword",
  "rememberMe": false
}
```

### Response

**HTTP 200 OK**

```json
{
  "uniqueId": "b2c3d4e5-2222-3333-4444-555566667777",
  "username": "localadmin",
  "csrf_token": ""
}
```

> ⚠️ **Important**: The `csrf_token` field in the response body is **always empty string**. The real CSRF token is delivered two ways:
> 1. **Response header** `x-updated-csrf-token: <uuid>` — grab this value.
> 2. **Inside the JWT cookie** — base64-decode the `TOKEN` cookie middle segment; the `csrfToken` claim contains the same UUID.

**Set-Cookie header**:
```
TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...; Path=/; HttpOnly; SameSite=Strict
```

### JWT Payload Structure

```json
{
  "userId": "b2c3d4e5-2222-3333-4444-555566667777",
  "passwordRevision": 1778106242,
  "isRemembered": false,
  "csrfToken": "f0959a86-9a25-4f34-9354-689d3be51c29",
  "iat": 1778106861,
  "exp": 1778114061,
  "jti": "308b3a97-4f81-4bfd-a4f7-6a804c7eb864"
}
```

Token lifetime: ~2 hours (`exp - iat = 7200 seconds`).

### Required Headers for All Subsequent Requests

```http
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrfToken from JWT payload or x-updated-csrf-token header>
```

Both headers are required for **all** Talk API requests. Most GETs silently succeed without the CSRF header but it should always be included to avoid unexpected 401s on POST/PUT/DELETE.

---

## POST `/api/auth/logout`

**Status**: ✅ Confirmed (standard UniFi OS)

```http
POST https://<UDM-IP>/api/auth/logout
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

Clears the `TOKEN` cookie and invalidates the session server-side.

---

## GET `/proxy/talk/api/user/info`

**Status**: ✅ Confirmed — returns current authenticated user's Talk role and permissions

```http
GET https://<UDM-IP>/proxy/talk/api/user/info
Cookie: TOKEN=<jwt>
X-CSRF-Token: <csrf>
```

### Response

```json
{
  "role": "super_administrator",
  "id": "b2c3d4e5-2222-3333-4444-555566667777",
  "user_has_talk_manage_permissions": true,
  "user_has_talk_view_permissions": true
}
```

**Roles observed**: `super_administrator`

---

## Python Authentication Example

```python
import requests, base64, json

HOST = "192.168.1.1"
s = requests.Session()
s.verify = False  # self-signed cert on LAN

resp = s.post(
    f"https://{HOST}/api/auth/login",
    json={"username": "localadmin", "password": "yourpassword", "rememberMe": False},
)
resp.raise_for_status()

# CSRF token is in the response header, NOT the body
csrf = resp.headers.get("x-updated-csrf-token")
s.headers.update({"X-CSRF-Token": csrf})

# TOKEN cookie is automatically managed by requests.Session
# All further calls to s.get/post/put/delete are now authenticated

# Verify authentication
me = s.get(f"https://{HOST}/proxy/talk/api/user/info")
print(me.json())
```

---

## Error Responses

| HTTP Status | Body | Meaning |
|---|---|---|
| `401` | `{"code":"INVALID_PAYLOAD"}` | Wrong username or password |
| `429` | `{"code":"AUTHENTICATION_FAILED_LIMIT_REACHED"}` | Rate limited; wait ~3 min |
| `401` | `{"code":"CSRF_TOKEN_IS_INVALID"}` | Missing or wrong X-CSRF-Token |
| `401` | `{"code":"TOKEN_EXPIRED"}` | TOKEN cookie expired; re-login |
