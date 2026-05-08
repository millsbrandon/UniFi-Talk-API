# Private Capture Workflow

This workflow keeps credentials and raw responses out of Git while allowing sanitized data to be promoted into tracked docs.

## 1) Local-only secrets

Create or edit `.local/secrets.json` (git-ignored):

```json
{
  "host": "192.168.1.1",
  "username": "your-username",
  "password": "your-password",
  "token": "",
  "csrf": ""
}
```

## 2) Capture to private storage

By default, capture scripts now write to `private_captures/` (git-ignored).

- WebSocket monitor:

```bash
python3 scripts/ws_monitor.py --scenario outbound-call-test
```

- Mutation capture via mitmproxy:

```bash
mitmdump -s scripts/capture_mutations.py --listen-port 8080 \
  --set udm_host=192.168.1.1 --set scenario=outbound-call-test
```

- Mutation endpoint probe:

```bash
python3 scripts/test_mutations.py --dry-run
```

You can override capture output location by setting `UNIFI_CAPTURE_DIR`.

## 3) Analyze call-control and recording signals

```bash
python3 scripts/analyze_ws_call_control.py \
  --input private_captures/ws_events.jsonl \
  --output private_captures/ws_call_control_summary.json
```

## 4) Sanitize before promotion

```bash
python3 scripts/sanitize_capture.py \
  --input private_captures/ws_events_focus.jsonl \
  --output analysis/sanitized/ws_events_focus.sanitized.jsonl
```

After review, copy sanitized output into tracked docs or analysis files as needed.
