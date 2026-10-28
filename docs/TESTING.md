# Testing Guide

## Automated tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

The test suite does not require a live camera, Arduino, or model download. It
uses fakes and generated frames to verify:

- person-only filtering, confidence thresholds, and single-pass inference;
- zero, one, and multiple current-frame counts;
- camera timeouts and reconnection behavior;
- serial protocol formatting, heartbeat throttling, reconnection, and cleanup;
- optional serial mode and CLI validation;
- dashboard page availability, JSON state, stale data, and MJPEG delivery.

## Manual validation checklist

Run these on your own hardware and do not include private hosts or images in
public reports:

- [ ] Camera stream opens from the laptop.
- [ ] Dashboard video shows human boxes and confidence labels.
- [ ] Dashboard count matches the accepted person boxes.
- [ ] Boxes, labels, and fullscreen controls behave correctly.
- [ ] Arduino LCD count matches the dashboard count.
- [ ] Camera loss reports an unavailable state and LCD offline message.
- [ ] Arduino disconnection leaves detection and dashboard running.
- [ ] Restarting the Arduino causes the current count to resume after serial recovery.

## Before opening a pull request

1. Run the full test command.
2. Check `git diff --check` for whitespace errors.
3. Review staged changes for secrets and private addresses.
4. State exactly which manual tests you performed and which remain untested.
