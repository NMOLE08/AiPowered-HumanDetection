# Contributing to Sentinel Vision

Thank you for improving Sentinel Vision. Contributions to code, documentation,
tests, hardware notes, accessibility, and reproducible bug reports are welcome.

## Before you begin

- Read the [security policy](SECURITY.md) and do not publish credentials,
  private stream addresses, serial identifiers, logs containing personal data,
  or model weights.
- Use a placeholder such as `CAMERA_HOST` in public examples.
- Keep the ESP32-CAM firmware, Python pipeline, and Arduino protocol compatible
  unless the pull request explicitly documents a migration.

## Development setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

The test suite uses fakes for camera, model, and serial devices. Do not require
physical hardware for ordinary unit tests.

## Pull requests

1. Create a focused branch from the default branch.
2. Keep each change limited to one problem when practical.
3. Add or update tests for changed Python behavior.
4. Run the complete test suite and describe the result in the pull request.
5. Explain any hardware validation separately from mocked validation.
6. Update documentation whenever setup, wiring, protocol, or CLI behavior changes.

Use clear, imperative commit messages, for example `Add camera reconnect event`.

## Code and hardware expectations

- Preserve one camera/inference worker per process in web mode.
- Do not create another YOLO inference path for the dashboard or LCD.
- Keep serial output nonblocking and retain only the newest state.
- Avoid hardcoded network hosts, passwords, API keys, device addresses, and COM ports.
- Do not commit `.env` files, pretrained weight files, local video captures, or generated output.

By contributing, you agree that your contribution is licensed under the
[MIT License](LICENSE).
