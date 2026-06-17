# Pi Telemetry Acceptance Testing

Use this checklist for manual verification before release or after dashboard UI changes.

## Setup

```bash
cd OpSecTools/tools/pi-telemetry
.venv/bin/python -m pi_telemetry.dashboard --host 127.0.0.1 --port 8788
```

Open `http://127.0.0.1:8788/`.

## Host View

- [ ] Host view loads with `feed-state` returning to `live`.
- [ ] CPU, temperature, memory, disk, load, network, health, and process cards populate.
- [ ] Manual browser resize pauses the feed briefly as `resizing`, then returns to `live`.
- [ ] Desktop width, snapped width, and narrow/mobile width do not horizontally overflow.

## LLM View

- [ ] LLM tab activates and hides the Host panel.
- [ ] Codex metadata populates when `~/.codex/state_5.sqlite` exists.
- [ ] Token count, model mix, recent threads, process pressure, and host pressure populate.
- [ ] With `PI_TELEMETRY_LLM=off`, the LLM view reports unavailable/disabled.
- [ ] With `PI_TELEMETRY_CODEX_PROCESS=ollama`, process matching follows that marker.

## Updates

- [ ] When a newer release exists, the dashboard shows an update banner at startup.
- [ ] The banner exposes a copyable command and a release-notes link.
- [ ] `PI_TELEMETRY_UPDATE_MODE=auto` completes a best-effort update before the dashboard starts.
- [ ] `PI_TELEMETRY_UPDATE_MODE=off` suppresses startup update checks.
- [ ] An unreleased git checkout still shows a working-tree prompt on open.
- [ ] `PI_TELEMETRY_RELEASE_FEED_URL` can surface beta/stable notices from a JSON feed.

## Privacy

Check the API payload:

```bash
curl -s http://127.0.0.1:8788/api/telemetry | python -m json.tool
```

Confirm the payload does not include:

- Prompt text
- Session JSONL contents
- Thread titles or previews
- Full `/home/...` workspace paths
- API keys, tokens, or environment variables

## Browser Console

Run:

```javascript
window.__piTelemetryStatus()
```

Confirm it reports `feedState`, `activeView`, `resizing`, `profile`, and canvas sizing.
