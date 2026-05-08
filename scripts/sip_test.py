#!/usr/bin/env python3
"""
UniFi Talk SIP Registration & Call Control Test

Raw-socket SIP implementation — no third-party SIP library needed.
Handles FreeSWITCH compact headers (v: f: t: i: l: k:) correctly.

Credentials loaded from .local/sip_credentials.json
Test phone number loaded from .local/secrets.json (externalTestPhoneNumber)

Usage:
  python3 scripts/sip_test.py                     # register only
  python3 scripts/sip_test.py --call 0002         # call internal extension
  python3 scripts/sip_test.py --call external     # call externalTestPhoneNumber from secrets
  python3 scripts/sip_test.py --call +17195551234 # call explicit E.164 number
  python3 scripts/sip_test.py --hangup-after 10   # stay connected N seconds before BYE
"""

import argparse
import hashlib
import json
import logging
import os
import random
import re
import select
import socket
import sys
import time
import uuid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

ROOT = os.path.join(os.path.dirname(__file__), "..")

# ── RFC 3261 compact header map (single-char → full name) ────────────────────
COMPACT_HEADERS = {
    "v": "Via", "f": "From", "t": "To", "i": "Call-ID",
    "m": "Contact", "l": "Content-Length", "c": "Content-Type",
    "s": "Subject", "e": "Content-Encoding", "o": "Event",
    "u": "Allow-Events", "r": "Refer-To", "b": "Referred-By",
    "k": "Supported",
}


# ── Config loading ────────────────────────────────────────────────────────────

def load_config() -> dict:
    """Load SIP credentials and optional test number from .local/ files."""
    cred_file = os.path.join(ROOT, ".local", "sip_credentials.json")
    secrets_file = os.path.join(ROOT, ".local", "secrets.json")

    if not os.path.exists(cred_file):
        sys.exit(
            f"Missing {cred_file}\n"
            "Create it with: {\"host\": \"192.168.1.1\", \"ext\": \"0001\", \"password\": \"<sip_password>\"}\n"
            "Get sip_password from: GET /proxy/talk/api/v1/users"
        )

    with open(cred_file) as f:
        cfg = json.load(f)

    # Merge optional fields from secrets.json
    if os.path.exists(secrets_file):
        with open(secrets_file) as f:
            secrets = json.load(f)
        cfg.setdefault("externalTestPhoneNumber", secrets.get("externalTestPhoneNumber"))

    return cfg


# ── SIP helpers ───────────────────────────────────────────────────────────────

def _local_ip(server: str) -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((server, 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


def _branch() -> str:
    return "z9hG4bK" + uuid.uuid4().hex[:12]


def _call_id() -> str:
    return uuid.uuid4().hex


def _tag() -> str:
    return uuid.uuid4().hex[:8]


def _parse_headers(raw: bytes) -> dict:
    """
    Parse SIP response headers, expanding compact forms.
    Handles both 'Name: value' and compact 'n:value' (no space after colon).
    Returns a dict; Via is a list of values.
    """
    headers = {"Via": []}
    lines = raw.split(b"\r\n")
    for line in lines[1:]:  # skip status line
        if not line:
            continue
        decoded = line.decode("utf-8", errors="replace")
        # Split on first colon; strip surrounding whitespace from value
        if ":" not in decoded:
            continue
        name, _, value = decoded.partition(":")
        name = name.strip()
        value = value.strip()
        # Expand compact header names
        if len(name) == 1:
            name = COMPACT_HEADERS.get(name.lower(), name)
        if name == "Via":
            headers["Via"].append(value)
        else:
            headers[name] = value
    return headers


def _parse_status(raw: bytes) -> int:
    """Extract numeric status code from first line of SIP response."""
    try:
        first = raw.split(b"\r\n", 1)[0].decode("utf-8", errors="replace")
        return int(first.split(" ", 2)[1])
    except Exception:
        return 0


def _md5_digest(username: str, password: str, realm: str,
                nonce: str, method: str, uri: str, qop: str = None,
                nc: str = None, cnonce: str = None) -> str:
    ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()
    ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
    if qop in ("auth", "auth-int") and nc and cnonce:
        raw = f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}"
    else:
        raw = f"{ha1}:{nonce}:{ha2}"
    return hashlib.md5(raw.encode()).hexdigest()


def _parse_www_auth(header_val: str) -> dict:
    """Parse WWW-Authenticate / Proxy-Authenticate digest parameters."""
    result = {}
    for m in re.finditer(r'(\w+)="?([^",]+)"?', header_val):
        result[m.group(1)] = m.group(2)
    return result


def _build_auth_header(method: str, uri: str, username: str,
                       password: str, auth_info: dict,
                       proxy: bool = False) -> str:
    realm = auth_info.get("realm", "")
    nonce = auth_info.get("nonce", "")
    qop   = auth_info.get("qop", "").strip('"')
    algo  = auth_info.get("algorithm", "MD5")

    nc     = "00000001"
    cnonce = uuid.uuid4().hex[:8]

    response = _md5_digest(
        username, password, realm, nonce, method, uri,
        qop=qop or None, nc=nc if qop else None, cnonce=cnonce if qop else None,
    )

    parts = [
        f'Digest username="{username}"',
        f'realm="{realm}"',
        f'nonce="{nonce}"',
        f'uri="{uri}"',
        f'response="{response}"',
        f'algorithm={algo}',
    ]
    if qop:
        parts += [f'qop={qop}', f'nc={nc}', f'cnonce="{cnonce}"']
    prefix = "Proxy-Authorization" if proxy else "Authorization"
    return prefix + ": " + ",".join(parts) + "\r\n"


# ── Core SIP operations ───────────────────────────────────────────────────────

class SIPSession:
    def __init__(self, server: str, port: int, ext: str, password: str, local_ip: str, local_port: int = 5067):
        self.server = server
        self.port = port
        self.ext = ext
        self.password = password
        self.local_ip = local_ip
        self.local_port = local_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((local_ip, local_port))
        self.sock.settimeout(10)
        self._cseq = 1

    def close(self):
        self.sock.close()

    def _send_recv(self, msg: str) -> bytes:
        self.sock.sendto(msg.encode(), (self.server, self.port))
        return self._recv_response()

    def _recv_response(self) -> bytes:
        """Read packets until we get an actual SIP response (starts with SIP/2.0).
        Automatically replies 200 OK to any NOTIFY or OPTIONS requests in between."""
        while True:
            resp, addr = self.sock.recvfrom(8192)
            first = resp.split(b"\r\n", 1)[0].decode("utf-8", errors="replace")
            if first.startswith("SIP/2.0"):
                log.debug("RECV response:\n%s", resp.decode(errors="replace"))
                return resp
            # It's an in-dialog request (NOTIFY, OPTIONS, etc.) — auto-reply 200
            method = first.split(" ", 1)[0]
            log.debug("Received in-dialog %s — auto-replying 200 OK", method)
            hdrs = _parse_headers(resp)
            reply = (
                f"SIP/2.0 200 OK\r\n"
                f"Via: {hdrs.get('Via', [''])[0] if isinstance(hdrs.get('Via'), list) else hdrs.get('Via', '')}\r\n"
                f"From: {hdrs.get('From', '')}\r\n"
                f"To: {hdrs.get('To', '')}\r\n"
                f"Call-ID: {hdrs.get('Call-ID', '')}\r\n"
                f"CSeq: {hdrs.get('CSeq', '')}\r\n"
                f"Content-Length: 0\r\n\r\n"
            )
            self.sock.sendto(reply.encode(), addr)

    def _next_cseq(self) -> int:
        n = self._cseq
        self._cseq += 1
        return n

    def register(self) -> bool:
        """Perform SIP REGISTER with digest auth. Returns True on 200 OK."""
        call_id = _call_id()
        from_tag = _tag()
        cseq = self._next_cseq()
        uri = f"sip:{self.server}"
        contact = f"sip:{self.ext}@{self.local_ip}:{self.local_port}"
        branch = _branch()

        def build_register(auth_header: str = "") -> str:
            return (
                f"REGISTER {uri} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};branch={branch};rport\r\n"
                f"From: <sip:{self.ext}@{self.server}>;tag={from_tag}\r\n"
                f"To: <sip:{self.ext}@{self.server}>\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: {cseq} REGISTER\r\n"
                f"Contact: <{contact}>\r\n"
                f"Max-Forwards: 70\r\n"
                f"Expires: 300\r\n"
                f"User-Agent: unifi-talk-re/1.0\r\n"
                f"{auth_header}"
                f"Content-Length: 0\r\n\r\n"
            )

        # First attempt (no auth)
        resp = self._send_recv(build_register())
        status = _parse_status(resp)
        log.debug("REGISTER attempt 1: %d", status)

        if status == 401:
            hdrs = _parse_headers(resp)
            auth_info = _parse_www_auth(hdrs.get("WWW-Authenticate", ""))
            auth_hdr = _build_auth_header(
                "REGISTER", uri, self.ext, self.password, auth_info, proxy=False
            )
            cseq = self._next_cseq()
            resp = self._send_recv(build_register(auth_hdr))
            status = _parse_status(resp)
            log.debug("REGISTER attempt 2 (with auth): %d", status)

        if status == 200:
            log.info("REGISTER: 200 OK — registered as ext %s", self.ext)
            return True

        log.error("REGISTER failed with status %d", status)
        log.debug("Response:\n%s", resp.decode(errors="replace"))
        return False

    def invite(self, destination: str, hangup_after: int = 5) -> bool:
        """
        Send INVITE to destination (extension or E.164).
        Waits for call to be answered, stays connected hangup_after seconds, then BYE.
        Returns True if call connected and ended cleanly.
        """
        call_id = _call_id()
        from_tag = _tag()
        cseq = self._next_cseq()
        branch = _branch()
        rtp_port = random.randint(10000, 10099) * 2  # even port for RTP

        # Build minimal SDP offer
        sess_id = random.randint(100000, 999999)
        sdp = (
            f"v=0\r\n"
            f"o={self.ext} {sess_id} {sess_id} IN IP4 {self.local_ip}\r\n"
            f"s=unifi-talk-re\r\n"
            f"c=IN IP4 {self.local_ip}\r\n"
            f"t=0 0\r\n"
            f"m=audio {rtp_port} RTP/AVP 0 101\r\n"
            f"a=rtpmap:0 PCMU/8000\r\n"
            f"a=rtpmap:101 telephone-event/8000\r\n"
            f"a=fmtp:101 0-15\r\n"
            f"a=sendrecv\r\n"
        )
        sdp_bytes = sdp.encode()
        to_uri = f"sip:{destination}@{self.server}"
        from_uri = f"sip:{self.ext}@{self.server}"
        contact = f"sip:{self.ext}@{self.local_ip}:{self.local_port}"

        def build_invite(auth_header: str = "") -> str:
            return (
                f"INVITE {to_uri} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};branch={branch};rport\r\n"
                f"From: <{from_uri}>;tag={from_tag}\r\n"
                f"To: <{to_uri}>\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: {cseq} INVITE\r\n"
                f"Contact: <{contact}>\r\n"
                f"Max-Forwards: 70\r\n"
                f"User-Agent: unifi-talk-re/1.0\r\n"
                f"Content-Type: application/sdp\r\n"
                f"{auth_header}"
                f"Content-Length: {len(sdp_bytes)}\r\n\r\n"
                f"{sdp}"
            )

        def send_ack(to_tag: str, ack_cseq: int):
            ack = (
                f"ACK {to_uri} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};branch={_branch()};rport\r\n"
                f"From: <{from_uri}>;tag={from_tag}\r\n"
                f"To: <{to_uri}>;tag={to_tag}\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: {ack_cseq} ACK\r\n"
                f"Max-Forwards: 70\r\n"
                f"Content-Length: 0\r\n\r\n"
            )
            self.sock.sendto(ack.encode(), (self.server, self.port))
            log.info("ACK sent")

        def send_bye(to_tag: str):
            bye_cseq = self._next_cseq()
            bye = (
                f"BYE {to_uri} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};branch={_branch()};rport\r\n"
                f"From: <{from_uri}>;tag={from_tag}\r\n"
                f"To: <{to_uri}>;tag={to_tag}\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: {bye_cseq} BYE\r\n"
                f"Max-Forwards: 70\r\n"
                f"Content-Length: 0\r\n\r\n"
            )
            self.sock.sendto(bye.encode(), (self.server, self.port))
            log.info("BYE sent")

        # Send INVITE
        log.info("INVITE → %s", destination)
        resp = self._send_recv(build_invite())
        status = _parse_status(resp)
        log.debug("INVITE response: %d", status)

        # Handle 401/407 auth challenge (FreeSWITCH uses 407 for INVITE)
        if status in (401, 407):
            hdrs = _parse_headers(resp)
            proxy_auth = status == 407
            auth_hdr_name = "Proxy-Authenticate" if proxy_auth else "WWW-Authenticate"
            auth_info = _parse_www_auth(hdrs.get(auth_hdr_name, ""))
            auth_hdr = _build_auth_header(
                "INVITE", to_uri, self.ext, self.password, auth_info, proxy=proxy_auth
            )
            prev_cseq = cseq
            cseq = self._next_cseq()
            branch_new = _branch()
            # ACK the error response first (required by RFC 3261)
            to_hdr_407 = _parse_headers(resp).get("To", "")
            m407 = re.search(r"tag=([^\s;>]+)", to_hdr_407)
            to_tag_407 = m407.group(1) if m407 else ""
            self.sock.sendto(
                (
                    f"ACK {to_uri} SIP/2.0\r\n"
                    f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};branch={branch};rport\r\n"
                    f"From: <{from_uri}>;tag={from_tag}\r\n"
                    f"To: <{to_uri}>{';tag=' + to_tag_407 if to_tag_407 else ''}\r\n"
                    f"Call-ID: {call_id}\r\n"
                    f"CSeq: {prev_cseq} ACK\r\n"
                    f"Max-Forwards: 70\r\n"
                    f"Content-Length: 0\r\n\r\n"
                ).encode(),
                (self.server, self.port),
            )
            branch = branch_new
            resp = self._send_recv(build_invite(auth_hdr))
            status = _parse_status(resp)
            log.debug("INVITE (with auth): %d", status)

        # 100 Trying / 180 Ringing are provisional — keep reading
        to_tag = ""
        invite_cseq = cseq
        self.sock.settimeout(60)

        while status in (100, 180, 183):
            log.info("Call progress: %d %s", status,
                     resp.split(b"\r\n", 1)[0].decode(errors="replace").split(" ", 2)[-1].strip())
            resp = self._recv_response()
            status = _parse_status(resp)

        if status == 200:
            hdrs = _parse_headers(resp)
            to_hdr = hdrs.get("To", "")
            m = re.search(r"tag=([^\s;>]+)", to_hdr)
            to_tag = m.group(1) if m else ""
            send_ack(to_tag, invite_cseq)
            log.info("Call ANSWERED — staying connected %ds then hanging up", hangup_after)
            time.sleep(hangup_after)
            send_bye(to_tag)
            # Drain the 200 OK for BYE
            try:
                self.sock.settimeout(5)
                bye_resp, _ = self.sock.recvfrom(8192)
                log.info("BYE response: %d", _parse_status(bye_resp))
            except socket.timeout:
                pass
            return True

        elif status in (480, 486, 487, 603):
            log.info("Call not answered: %d %s", status,
                     resp.split(b"\r\n", 1)[0].decode(errors="replace").split(" ", 2)[-1].strip())
            # ACK the error response
            hdrs = _parse_headers(resp)
            to_hdr = hdrs.get("To", "")
            m = re.search(r"tag=([^\s;>]+)", to_hdr)
            to_tag = m.group(1) if m else ""
            send_ack(to_tag, invite_cseq)
            return False

        else:
            log.error("Unexpected INVITE response: %d\n%s", status,
                      resp.decode(errors="replace"))
            return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    cfg = load_config()

    parser = argparse.ArgumentParser(description="UniFi Talk SIP test client")
    parser.add_argument(
        "--call", metavar="DESTINATION",
        help=(
            "Who to call: an extension (e.g. 0002), E.164 number (+17195551234), "
            "or 'external' to use externalTestPhoneNumber from secrets.json"
        ),
    )
    parser.add_argument("--hangup-after", type=int, default=5,
                        help="Seconds to stay on an answered call before BYE (default: 5)")
    parser.add_argument("--host", help="Override SIP server host")
    args = parser.parse_args()

    host = args.host or cfg["host"]
    ext = cfg["ext"]
    password = cfg["password"]
    local_ip = _local_ip(host)

    log.info("SIP server   : %s:5060 (FreeSWITCH)", host)
    log.info("Registering  : ext %s", ext)
    log.info("Local IP     : %s", local_ip)

    sess = SIPSession(host, 5060, ext, password, local_ip)

    try:
        registered = sess.register()
        if not registered:
            sys.exit(1)

        destination = args.call
        if destination == "external":
            destination = cfg.get("externalTestPhoneNumber")
            if not destination:
                sys.exit("No externalTestPhoneNumber in secrets.json")
            log.info("Using external test number: %s", destination)

        if destination:
            sess.invite(destination, hangup_after=args.hangup_after)
        else:
            log.info("No --call argument. Use --call 0002, --call external, or --call +1XXXXXXXXXX")

    except KeyboardInterrupt:
        log.info("Interrupted.")
    except socket.timeout:
        log.error("Socket timed out waiting for SIP response.")
    finally:
        sess.close()
        log.info("Done.")


if __name__ == "__main__":
    main()

