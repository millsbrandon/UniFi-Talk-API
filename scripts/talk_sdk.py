#!/usr/bin/env python3
"""
talk_sdk.py — UniFi Talk Python SDK.

A clean, typed interface over the confirmed UniFi Talk REST API.
Reverse-engineered against Talk v5.1.2 on UDM-Pro.

Quick start:
    from scripts.talk_sdk import TalkClient

    c = TalkClient("192.168.1.1")
    c.login("localadmin", "yourpassword")

    info    = c.get_info()
    users   = c.get_users()
    calls   = c.get_all_call_logs()
    numbers = c.get_numbers()
    config  = c.get_config()

Authentication notes:
    - Local accounts ONLY. Cloud/SSO accounts require a different OAuth flow.
    - After ~5 failed logins the server rate-limits for ~3 minutes.
    - TOKEN JWT expires in 2 hours. The client auto-re-authenticates on 401.
    - TLS: UDM-Pro uses a self-signed cert; verify_ssl=False is the default.
"""

from __future__ import annotations

import base64
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError as exc:
    raise ImportError("Install requests: pip3 install requests") from exc

# ── Types ─────────────────────────────────────────────────────────────────────

JsonDict = dict[str, Any]
JsonList = list[JsonDict]


# ── Client ────────────────────────────────────────────────────────────────────

class TalkClient:
    """
    Authenticated client for the UniFi Talk API.

    All methods return parsed JSON (dict or list) on success and raise
    TalkAPIError on non-2xx responses.
    """

    AUTH_BASE  = "/api/auth"
    TALK_BASE  = "/proxy/talk/api"

    def __init__(self, host: str, verify_ssl: bool = False, timeout: int = 15):
        self.host       = host
        self.verify_ssl = verify_ssl
        self.timeout    = timeout
        self._session   = requests.Session()
        self._session.verify = verify_ssl
        self._username: str = ""
        self._password: str = ""
        self._token: str    = ""
        self._csrf: str     = ""

    # ── Auth ──────────────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> JsonDict:
        """
        Authenticate with UniFi OS using a local account.

        Returns the parsed login response body. Sets TOKEN cookie and
        X-CSRF-Token header on the internal session for all future requests.

        Raises:
            TalkAuthError  — bad credentials or rate-limited
            TalkAPIError   — unexpected HTTP error
        """
        self._username = username
        self._password = password

        url  = f"https://{self.host}{self.AUTH_BASE}/login"
        body = {"username": username, "password": password, "rememberMe": False}

        resp = self._session.post(url, json=body, timeout=self.timeout)

        if resp.status_code == 429:
            raise TalkAuthError(
                "Rate-limited after too many failed logins. Wait ~3 minutes.",
                status=429,
            )
        if resp.status_code not in (200, 201):
            raise TalkAuthError(
                f"Login failed: HTTP {resp.status_code} — {resp.text[:200]}",
                status=resp.status_code,
            )

        self._token = resp.cookies.get("TOKEN", "")
        # CSRF is in the response header (body csrf_token is always empty)
        self._csrf  = (
            resp.headers.get("x-updated-csrf-token")
            or self._extract_csrf_from_jwt(self._token)
            or ""
        )

        self._session.cookies.set("TOKEN", self._token)
        self._session.headers.update({"X-CSRF-Token": self._csrf})

        return resp.json()

    def logout(self) -> None:
        """Invalidate the current session."""
        self._request("POST", f"{self.AUTH_BASE}/logout")
        self._token = ""
        self._csrf  = ""
        self._session.cookies.clear()
        self._session.headers.pop("X-CSRF-Token", None)

    @property
    def token_expires_at(self) -> datetime | None:
        """Return the TOKEN JWT expiry time as a UTC datetime, or None."""
        if not self._token:
            return None
        try:
            payload_b64 = self._token.split(".")[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.b64decode(payload_b64))
            exp = payload.get("exp")
            if exp:
                return datetime.fromtimestamp(exp, tz=timezone.utc)
        except Exception:
            pass
        return None

    @property
    def is_authenticated(self) -> bool:
        """True if a token is present and not yet expired."""
        if not self._token:
            return False
        exp = self.token_expires_at
        if exp and datetime.now(tz=timezone.utc) >= exp:
            return False
        return True

    # ── System / info ─────────────────────────────────────────────────────────

    def get_info(self) -> JsonDict:
        """
        GET /proxy/talk/api/info

        Returns Talk version, region, feature flags, and system identity.

        Key fields:
            version          — Talk version string (e.g. "5.1.2")
            setup_complete   — bool; False if onboarding not done
            default_country  — 2-letter ISO country code (e.g. "US")
            default_area_code
            controller_region / controller_region_code
            has_custom_gateways
            call_recordings_available
            host_device_name / host_device_model / host_device_serial
            update_channel   — "release" | "beta" | "alpha"
        """
        return self._get("info")

    def get_app_owner(self) -> JsonDict:
        """
        GET /proxy/talk/api/info/app_owner

        Returns: {"owner_ulp_id": "<uuid>"}
        """
        return self._get("info/app_owner")

    def get_install(self) -> JsonDict:
        """
        GET /proxy/talk/api/install

        Returns installation/billing status.

        Key fields:
            calling_status   — "active" | "suspended" | "trial"
            payment_status
            blocked          — bool; True if account is blocked
            notifications    — Slack/Teams/email notification URLs and flags
        """
        return self._get("install")

    def get_setup_complete(self) -> JsonDict:
        """
        GET /proxy/talk/api/setup_complete

        Returns: {"setup_complete": true}
        """
        return self._get("setup_complete")

    def get_ucore_system_info(self) -> JsonDict:
        """
        GET /proxy/talk/api/ucore/system_info

        Returns raw UniFi OS core system info: name, timezone, location,
        backup schedule, firmware versions, etc.
        """
        return self._get("ucore/system_info")

    def get_dashboard(self) -> JsonDict:
        """
        GET /proxy/talk/api/dashboard/consolidated_info

        Returns dashboard summary:
            consoleName / consoleShortname
            gatewayIp
            talkVersion / uosVersion
            talkServiceEnabled
            serviceHealth — array of health score buckets (hourly, last 24h)
        """
        return self._get("dashboard/consolidated_info")

    def get_most_active_users(self) -> JsonDict:
        """
        GET /proxy/talk/api/dashboard/most_active_users

        Returns top callers by call count.
        """
        return self._get("dashboard/most_active_users")

    def get_peer_consoles(self) -> JsonList:
        """
        GET /proxy/talk/api/peer_consoles

        Returns list of peer UniFi consoles discovered on the LAN.
        """
        return self._get("peer_consoles")

    def get_applications(self) -> JsonList:
        """
        GET /proxy/talk/api/applications

        Returns list of installed UniFi applications with name, version,
        isInstalled, isRunning, isConfigured.
        """
        return self._get("applications")

    def get_updates(self) -> JsonDict:
        """
        GET /proxy/talk/api/updates

        Returns available updates:
            host_suggested_version  — UDM firmware update (or null)
            talk_latest_version     — Talk update (or null)
        """
        return self._get("updates")

    # ── Call log ──────────────────────────────────────────────────────────────

    def get_call_log(
        self,
        page: int = 1,
        per_page: int = 50,
        direction: str | None = None,
        status: str | None = None,
        did: str | None = None,
    ) -> JsonDict:
        """
        GET /proxy/talk/api/call_log

        Paginated call history. Returns {"records": [...], ...}.

        Args:
            page      — 1-based page number (required; omitting returns 400)
            per_page  — records per page (default 50)
            direction — "in" | "out" (optional filter)
            status    — "answered" | "missed" | "voicemail" | "refused" |
                        "forwarded" (optional filter)
            did       — E.164 DID to filter by (e.g. "+12125551234")

        Record fields: time, from, to, answered_by, status, duration,
            recording_filename, is_video_call, is_intercom_call, direction,
            uuid, country, recording, quality_score, vm_data, call_events.
        """
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if direction:
            params["direction"] = direction
        if status:
            params["status"] = status
        if did:
            params["did"] = did
        return self._get("call_log", params=params)

    def get_all_call_logs(
        self,
        per_page: int = 50,
        direction: str | None = None,
        status: str | None = None,
        did: str | None = None,
        max_pages: int = 500,
    ) -> JsonList:
        """
        Fetch ALL call log records by paginating through every page.

        Returns a flat list of call record dicts.
        """
        all_records: JsonList = []
        for page in range(1, max_pages + 1):
            data = self.get_call_log(
                page=page,
                per_page=per_page,
                direction=direction,
                status=status,
                did=did,
            )
            records = data.get("records", [])
            if not records:
                break
            all_records.extend(records)
            if len(records) < per_page:
                break
        return all_records

    def get_voicemails(self) -> JsonList:
        """
        Convenience: return all call log records where status == "voicemail".
        Each record includes vm_data with the server-side file_path.
        """
        return self.get_all_call_logs(status="voicemail")

    def get_call_log_countries(self) -> JsonList:
        """
        GET /proxy/talk/api/call_log/countries

        Returns list of {"country": "US", "count": "748"} dicts.
        """
        return self._get("call_log/countries")

    def get_call_recording_rules(self) -> JsonList:
        """
        GET /proxy/talk/api/call_recording_rule

        Returns list of recording rule configs:
            id, dids, direction ("in+out" | "in" | "out"),
            record_announcement_text, should_record_internal_calls.
        """
        return self._get("call_recording_rule")

    def download_recording(self, call_uuid: str) -> bytes:
        """
        GET /proxy/talk/api/call_log/recording/<uuid>

        Downloads the call recording as raw MP3 bytes.
        Only available for calls where recording=True in the call log.
        Returns 404 if the call was not recorded.

        The recording file lives at /srv/unifi-talk/recordings/<uuid>.mp3
        on the UDM filesystem.

        Example:
            with open(f'{call_uuid}.mp3', 'wb') as f:
                f.write(c.download_recording(call_uuid))
        """
        resp = self._raw_request("GET", f"call_log/recording/{call_uuid}")
        if resp.status_code == 404:
            raise TalkAPIError(
                f"No recording found for call {call_uuid}. "
                "Check that recording=True in the call log record.",
                status=404,
            )
        resp.raise_for_status()
        return resp.content

    def get_recording_waveform(self, call_uuid: str) -> JsonDict:
        """
        GET /proxy/talk/api/call_log/audio_data/<uuid>

        Returns waveform peaks data for rendering an audio waveform in a UI.
        Also returns the recording_file_type ("mp3" or "wav").

        Response fields:
            peaks_data         — {version, channels, sample_rate,
                                  samples_per_pixel, bits, length, data[]}
            recording_file_type — "mp3" | "wav"
        """
        return self._get(f"call_log/audio_data/{call_uuid}")

    def get_call_flow(self, call_uuid: str) -> JsonList:
        """
        GET /proxy/talk/api/call_log/flow/<uuid>

        Returns the full ordered event timeline for a specific call.
        Similar to call_events in the call_log record but standalone and
        includes additional internal routing events.

        Event types include: call_started, seq_call_trying_endpoints,
            call_answered, call_ended, call_missed, call_sent_to_voicemail,
            skipped_endpoints, call_forwarded, call_refused.
        """
        return self._get(f"call_log/flow/{call_uuid}")

    def get_call_transcription(self, call_uuid: str) -> JsonDict:
        """
        GET /proxy/talk/api/call_log/transcription/<uuid>

        Returns AI transcription data for a call.
        Returns {status: null, transcript: null} if transcription is not
        enabled or not yet available.

        Fields: status, transcript, version, call_uuid
        """
        return self._get(f"call_log/transcription/{call_uuid}")

    def export_call_log_csv(
        self,
        page: int = 1,
        items_per_page: int = 50,
        direction: str | None = None,
        status: str | None = None,
        did: str | None = None,
    ) -> str:
        """
        GET /proxy/talk/api/call_log/csv

        Returns call log as a CSV string.

        ⚠️  Parameter is `items_per_page` (NOT `per_page` as in the JSON endpoint).

        CSV columns:
            time, from, to, answered_by, status, duration,
            recording_filename, is_video_call, is_intercom_call,
            is_group_intercom_call, queue_name

        Example:
            csv_data = c.export_call_log_csv(page=1, items_per_page=500)
            with open('calls.csv', 'w') as f:
                f.write(csv_data)
        """
        params: dict[str, Any] = {"page": page, "items_per_page": items_per_page}
        if direction:
            params["direction"] = direction
        if status:
            params["status"] = status
        if did:
            params["did"] = did
        resp = self._raw_request("GET", "call_log/csv", params=params)
        resp.raise_for_status()
        return resp.text

    def delete_recording(self, call_uuid: str) -> Any:
        """
        DELETE /proxy/talk/api/call_log/recording/<uuid>

        Deletes the recording file for a specific call.
        ⚠️  This is irreversible.
        """
        return self._delete(f"call_log/recording/{call_uuid}")

    def delete_recordings_bulk(self, call_uuids: list[str]) -> Any:
        """
        POST /proxy/talk/api/call_log/recording/delete

        Bulk delete recording files. Body: {uuids: [...]}
        ⚠️  This is irreversible.
        """
        return self._post("call_log/recording/delete", {"uuids": call_uuids})

    def delete_call_log_entry(self, call_uuid: str) -> Any:
        """
        DELETE /proxy/talk/api/call_log/<uuid>

        Deletes a single call log record.
        ⚠️  This is irreversible.
        """
        return self._delete(f"call_log/{call_uuid}")

    def delete_call_logs_bulk(self, call_uuids: list[str]) -> Any:
        """
        POST /proxy/talk/api/delete_call_logs

        Bulk delete call log records. Body: {uuids: [...]}
        ⚠️  This is irreversible.
        """
        return self._post("delete_call_logs", {"uuids": call_uuids})

    # ── Devices ───────────────────────────────────────────────────────────────

    def get_devices(self) -> JsonList:
        """
        GET /proxy/talk/api/devices

        Returns all adopted Talk hardware devices (phones, ATAs).

        Fields: mac, ip, model, version, last_seen, uptime,
            con_status, hashed_key, anonymous_device_id, additional_data.
        """
        return self._get("devices")

    def get_device_call_quality(self) -> JsonDict:
        """
        GET /proxy/talk/api/device/24h_call_quality

        Returns 24-hour call quality metrics per device.
        """
        return self._get("device/24h_call_quality")

    def get_drive_status(self) -> JsonList:
        """
        GET /proxy/talk/api/drive_status

        Returns storage drive status.
        """
        return self._get("drive_status")

    def get_pcap_status(self) -> JsonDict:
        """
        GET /proxy/talk/api/debug/pcap/status

        Returns packet capture status:
            status  — "no_external_storage" | "running" | "idle"
            end_time
        """
        return self._get("debug/pcap/status")

    # ── Users & numbers ───────────────────────────────────────────────────────

    def get_users(self) -> JsonList:
        """
        GET /proxy/talk/api/users

        Returns all Talk users.

        Fields: _id, unique_id, first_name, last_name, full_name, email,
            avatar_relative_path, status, employee_number, create_time,
            local_account_exist, extensions (if any).
        """
        return self._get("users")

    def get_user_info(self) -> JsonDict:
        """
        GET /proxy/talk/api/user/info

        Returns the currently authenticated user's Talk role and permissions:
            role — "super_administrator" | "administrator" | "viewer" | "user"
            id   — UniFi OS user UUID
            user_has_talk_manage_permissions
            user_has_talk_view_permissions
        """
        return self._get("user/info")

    def get_numbers(self) -> JsonList:
        """
        GET /proxy/talk/api/number/list

        Returns all DIDs (phone numbers) with associated user, device,
        extension, and SIP gateway data.

        Fields per number: did (E.164), sip_gateway_id, sip_gateway_name,
            user_data (full user object), group_data, total_seconds.
        """
        return self._get("number/list")

    def get_blocked_numbers(self) -> JsonList:
        """
        GET /proxy/talk/api/number/blocked

        Returns list of blocked caller IDs.
        """
        return self._get("number/blocked")

    def get_number_porting_list(self) -> JsonList:
        """GET /proxy/talk/api/number/porting/list"""
        return self._get("number/porting/list")

    def get_number_porting_request_count(self) -> JsonDict:
        """
        GET /proxy/talk/api/number/porting/request_count

        Returns: {count, actual_count, limit, porting_requests_enabled}
        """
        return self._get("number/porting/request_count")

    def get_contacts(self) -> JsonList:
        """GET /proxy/talk/api/contacts — shared contact directory."""
        return self._get("contacts")

    def get_contact_list(self) -> JsonList:
        """GET /proxy/talk/api/contact_list — alternate contact directory path."""
        return self._get("contact_list")

    def get_voicemail_data(self, vm_uuid: str) -> JsonDict:
        """
        GET /proxy/talk/api/voicemail/data/<uuid>

        Returns standalone voicemail metadata by UUID (same data as vm_data
        inside a call_log record, but accessible directly).

        Fields: uuid, read_at, duration, file_path, received_at,
            vm_left_for_ext, vm_receiver_uuid, recipient_user_uuids,
            fs_db_vm_uuids_ext_mapping.

        Note: The file_path is a server-side filesystem path. The voicemail
        audio is not downloadable via HTTP API — use SSH/SCP to retrieve:
            /srv/unifi-talk/voicemail/talk.com/<ext>/<filename>.mp3
        """
        return self._get(f"voicemail/data/{vm_uuid}")

    def delete_voicemail(self, vm_uuid: str, ext: str) -> Any:
        """
        POST /proxy/talk/api/call_log/<uuid>/delete  body: {ext: "0002"}

        Deletes a voicemail for a specific extension.
        ⚠️  This is irreversible.
        """
        return self._post(f"call_log/{vm_uuid}/delete", {"ext": ext})

    def delete_voicemails_bulk(self, vm_uuids: list[str]) -> Any:
        """
        POST /proxy/talk/api/voicemail/delete  body: {uuids: [...]}

        Bulk delete voicemails.
        ⚠️  This is irreversible.
        """
        return self._post("voicemail/delete", {"uuids": vm_uuids})

    # ── SMS ───────────────────────────────────────────────────────────────────

    def get_sms_conversations(self, page: int = 1) -> JsonList:
        """
        GET /proxy/talk/api/sms/conversations

        Returns list of SMS conversations.
        Supports ?page= pagination.
        """
        return self._get("sms/conversations", params={"page": page})

    # ── Call routing ──────────────────────────────────────────────────────────

    def get_ring_flow(self) -> JsonList:
        """
        GET /proxy/talk/api/ring_flow

        Returns ring flow / call routing schedule configurations.
        """
        return self._get("ring_flow")

    def get_ring_groups(self) -> JsonList:
        """GET /proxy/talk/api/group/list — ring group configurations."""
        return self._get("group/list")

    def get_queues(self) -> JsonList:
        """GET /proxy/talk/api/queues — call queue configurations."""
        return self._get("queues")

    def get_call_center_queue(self) -> JsonList:
        """GET /proxy/talk/api/call_center/queue — active call center queue."""
        return self._get("call_center/queue")

    def get_parking_lots(self) -> JsonList:
        """GET /proxy/talk/api/parking_lots — call parking lot configurations."""
        return self._get("parking_lots")

    def get_switchboard(self) -> JsonDict:
        """
        GET /proxy/talk/api/switchboard

        Returns switchboard/receptionist console configuration with
        node-based entity tree.
        """
        return self._get("switchboard")

    def get_phone_designer(self) -> JsonList:
        """GET /proxy/talk/api/phone_designer — phone screen layout configs."""
        return self._get("phone_designer")

    def get_phone_wallpapers(self) -> JsonList:
        """
        GET /proxy/talk/api/phone_designer/wallpaper/list

        Returns list of available phone wallpapers (standard + custom):
            filename, orientation, type, predefined_text_color.
        """
        return self._get("phone_designer/wallpaper/list")

    # ── SIP / Trunking ────────────────────────────────────────────────────────

    def get_sip_gateways(self) -> JsonList:
        """
        GET /proxy/talk/api/third_party_sip/gateway_list

        Returns SIP trunk/gateway configurations.

        ⚠️  Response includes plaintext SIP credentials (password field).
            Treat this data as secret.

        Fields: id, name, enabled, gateway_params (proxy, username, password,
            register), acl_ip_cidr_list, route_all_countries,
            route_country_alpha_2_list.
        """
        return self._get("third_party_sip/gateway_list")

    # ── Settings ──────────────────────────────────────────────────────────────

    def get_config(self) -> JsonDict:
        """
        GET /proxy/talk/api/setting/config

        Returns the full Talk system configuration.

        Key fields: nat_needs_static_port, static_port, call_log_recording_enabled,
            voicemail_enabled, voicemail_email_enabled, voicemail_slack_enabled,
            voicemail_teams_enabled, voicemail_email_transcriptions_enabled,
            global_voicemail_timeout, emergency_status, audio_codec_list,
            owner_full_name, owner_email, logging_level.
        """
        return self._get("setting/config")

    def get_emergency_status(self) -> JsonDict:
        """
        GET /proxy/talk/api/setting/emergency_status

        Returns E911 address registration status per DID.
        """
        return self._get("setting/emergency_status")

    def get_emergency_addresses(self) -> JsonList:
        """GET /proxy/talk/api/emergency_address/list"""
        return self._get("emergency_address/list")

    def get_default_area_code(self) -> JsonDict:
        """GET /proxy/talk/api/setting/default_area_code"""
        return self._get("setting/default_area_code")

    def get_dialing_country(self) -> JsonDict:
        """GET /proxy/talk/api/setting/dialing_country"""
        return self._get("setting/dialing_country")

    def get_hold_music(self) -> JsonList:
        """
        GET /proxy/talk/api/setting/hold_music

        Returns list of hold music tracks:
            title, type ("standard" | "custom").
        """
        return self._get("setting/hold_music")

    def get_ringtones(self) -> JsonList:
        """
        GET /proxy/talk/api/setting/ringtones

        Returns list of available ringtones:
            title, type ("standard" | "custom").
        """
        return self._get("setting/ringtones")

    def get_voicemail_greeting(self) -> bytes:
        """
        GET /proxy/talk/api/setting/voicemail_greeting_file

        Returns the global voicemail greeting as raw MP3 bytes.

        Example — save to file:
            with open("greeting.mp3", "wb") as f:
                f.write(c.get_voicemail_greeting())
        """
        resp = self._raw_request("GET", "setting/voicemail_greeting_file")
        return resp.content

    # ── Billing ───────────────────────────────────────────────────────────────

    def get_billing_balance(self) -> JsonDict:
        """
        GET /proxy/talk/api/billing/coupons/balance

        Returns: {"amount": 0, "enabled": false}
        """
        return self._get("billing/coupons/balance")

    # ── Identity / compliance ─────────────────────────────────────────────────

    def get_identity_status(self) -> JsonDict:
        """
        GET /proxy/talk/api/identity_status

        Returns KYC/business profile status:
            business_profile — null if not submitted.
        """
        return self._get("identity_status")

    def get_regulatory_bundle(self) -> JsonDict:
        """
        GET /proxy/talk/api/regulatory_bundle

        Returns regulatory bundle (A2P/CNAM/STIR-SHAKEN) status.
        """
        return self._get("regulatory_bundle")

    def get_lock_usage(self) -> JsonDict:
        """
        GET /proxy/talk/api/lock/usage

        Returns seat/license usage: {"remaining": null | int}
        """
        return self._get("lock/usage")

    def get_owner_transfer_state(self) -> JsonDict | None:
        """
        GET /proxy/talk/api/owner_transfer/transfer_state

        Returns the current owner transfer state, or None if no transfer
        is in progress.
        """
        return self._get("owner_transfer/transfer_state")

    # ── Integrations ──────────────────────────────────────────────────────────

    def get_protect_cameras(self) -> JsonList:
        """
        GET /proxy/talk/api/protect/cameras

        Returns UniFi Protect cameras available for video/intercom calling.

        Fields: cameraId, mac, name, status, adoptedInAccessApp,
            consoleMac, consoleName.
        """
        return self._get("protect/cameras")

    # ── Audio export ──────────────────────────────────────────────────────────

    def get_audio_export_status(self) -> dict:
        """
        GET /proxy/talk/api/exports/audio_data_archive

        Returns the current audio export download if one is ready.
        Returns HTTP 500 when no export has been queued.

        Use trigger_audio_export() first, then poll this endpoint.
        """
        resp = self._raw_request("GET", "exports/audio_data_archive")
        if resp.status_code == 500:
            return {"status": "no_export_queued", "raw": resp.text[:200]}
        resp.raise_for_status()
        ct = resp.headers.get("content-type", "")
        if "json" in ct:
            return resp.json()
        return {"status": "ready", "content_type": ct, "size": len(resp.content)}

    def trigger_audio_export(self) -> dict:
        """
        POST /proxy/talk/api/prepare_audio_data  (candidate — not yet confirmed)

        Triggers a bulk audio data export. Poll get_audio_export_status()
        until status changes from "processing" to ready.
        """
        resp = self._raw_request("POST", "prepare_audio_data", json={})
        return self._parse_response(resp)

    # ── Low-level helpers ─────────────────────────────────────────────────────

    def _get(self, path: str, params: dict | None = None) -> Any:
        resp = self._raw_request("GET", path, params=params)
        return self._parse_response(resp)

    def _post(self, path: str, body: dict | None = None) -> Any:
        resp = self._raw_request("POST", path, json=body or {})
        return self._parse_response(resp)

    def _put(self, path: str, body: dict | None = None) -> Any:
        resp = self._raw_request("PUT", path, json=body or {})
        return self._parse_response(resp)

    def _delete(self, path: str) -> Any:
        resp = self._raw_request("DELETE", path)
        return self._parse_response(resp)

    def _raw_request(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> requests.Response:
        """Make a request with auto-reauth on 401."""
        url = self._build_url(path)
        resp = self._session.request(method, url, timeout=self.timeout, **kwargs)
        if resp.status_code == 401 and self._username:
            self._reauth()
            resp = self._session.request(method, url, timeout=self.timeout, **kwargs)
        return resp

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"https://{self.host}{path}"
        resp = self._session.request(method, url, timeout=self.timeout, **kwargs)
        if resp.status_code == 401 and self._username:
            self._reauth()
            resp = self._session.request(method, url, timeout=self.timeout, **kwargs)
        return resp

    def _build_url(self, path: str) -> str:
        if path.startswith("/"):
            return f"https://{self.host}{path}"
        return f"https://{self.host}{self.TALK_BASE}/{path}"

    def _parse_response(self, resp: requests.Response) -> Any:
        if resp.status_code == 401:
            raise TalkAuthError("Unauthorized — token expired or invalid.", status=401)
        if resp.status_code == 403:
            raise TalkAuthError("Forbidden — insufficient permissions.", status=403)
        if not resp.ok:
            raise TalkAPIError(
                f"HTTP {resp.status_code}: {resp.text[:300]}",
                status=resp.status_code,
            )
        if not resp.content:
            return None
        ct = resp.headers.get("content-type", "")
        if "json" in ct:
            return resp.json()
        return resp.text

    def _reauth(self) -> None:
        if self._username and self._password:
            try:
                self.login(self._username, self._password)
            except TalkAuthError:
                pass

    @staticmethod
    def _extract_csrf_from_jwt(token: str) -> str:
        try:
            payload_b64 = token.split(".")[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.b64decode(payload_b64))
            return payload.get("csrfToken", "")
        except Exception:
            return ""


# ── Exceptions ────────────────────────────────────────────────────────────────

class TalkAPIError(Exception):
    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


class TalkAuthError(TalkAPIError):
    pass


# ── CLI demo ──────────────────────────────────────────────────────────────────

def _demo(host: str, username: str, password: str) -> None:
    import pprint
    c = TalkClient(host)
    c.login(username, password)
    print(f"\n[+] Authenticated as: {c.get_user_info()}")

    info = c.get_info()
    print(f"\n[+] Talk version: {info.get('version')}  |  Host: {info.get('host_device_name')}")

    users = c.get_users()
    print(f"\n[+] Users ({len(users)}):")
    for u in users:
        print(f"    {u['full_name']}  <{u.get('email', '')}>"
              f"  (id={u['unique_id'][:8]}...)")

    numbers = c.get_numbers()
    print(f"\n[+] Phone numbers ({len(numbers)}):")
    for n in numbers:
        owner = n.get("user_data") or n.get("group_data") or {}
        print(f"    {n['did']}  →  {owner.get('full_name', 'unassigned')}"
              f"  (via {n.get('sip_gateway_name', '?')})")

    calls = c.get_call_log(page=1, per_page=5)
    records = calls.get("records", [])
    print(f"\n[+] Last {len(records)} calls:")
    for r in records:
        print(f"    [{r['direction'].upper()}] {r['from']} → {r['to']}"
              f"  {r['status']}  {r['duration']}s  {r['time'][:10]}")

    config = c.get_config()
    print(f"\n[+] Config: recording={'ON' if config.get('call_log_recording_enabled') else 'OFF'}"
          f"  voicemail={'ON' if config.get('voicemail_enabled') else 'OFF'}"
          f"  codecs={config.get('audio_codec_list')}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="UniFi Talk SDK demo")
    parser.add_argument("--host", required=True)
    parser.add_argument("--username", "-u", required=True)
    parser.add_argument("--password", "-p", required=True)
    args = parser.parse_args()
    _demo(args.host, args.username, args.password)
