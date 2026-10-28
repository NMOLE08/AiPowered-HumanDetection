# Sentinel Vision

**Local AI human detection, live monitoring, and optional Arduino LCD output.**

Sentinel Vision turns an ESP32-CAM stream into a privacy-conscious local
monitoring interface. It runs pretrained YOLO11n on a laptop, detects people,
shows the current visible-person count in a browser dashboard, and can send the
same count to an Arduino Uno with a 16×2 I²C LCD.

> The count represents people visible in the latest valid processed frame. It is
> not a unique-visitor, entry/exit, or total-occupancy system.

## Features

- Pretrained YOLO11n person-only detection; no model training required
- One camera and inference worker with bounded latest-frame buffering
- Professional local FastAPI dashboard with live annotated MJPEG video
- Live count, measured FPS, inference timing, system health, and session events
- Browser controls for boxes, labels, and fullscreen video
- Camera recovery states that do not present stale data as valid
- Optional nonblocking Arduino Uno serial integration at 115200 baud
- I²C LCD firmware with `COUNT`, `CAMERA OFFLINE`, and `NO DATA` states
- No cloud service, database, telemetry, or public camera exposure by default

## Architecture

```text
ESP32-CAM → CameraStream → YOLO11n on laptop → Current person count
                                                    ├─ Local web dashboard
                                                    └─ Arduino Uno → 16×2 I²C LCD
```

The full system, lifecycle, and data-flow diagrams are in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Quick start

### 1. Create a Python environment

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Start the web dashboard

Replace `CAMERA_HOST` with your own camera host locally. Do not commit it.

```powershell
.\.venv\Scripts\python.exe -m app.main --source "http://CAMERA_HOST:81/stream" --ui web
```

Open the local address printed by the terminal.

### 3. Include the Arduino LCD (optional)

```powershell
.\.venv\Scripts\python.exe -m app.main --source "http://CAMERA_HOST:81/stream" --serial-port COM_PORT --ui web
```

Use the Arduino Uno's port for `COM_PORT`, not a camera programming adapter.

## Documentation

| Guide | Contents |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | System design, lifecycle, and data flow |
| [Hardware](docs/HARDWARE.md) | Circuit diagrams, wiring tables, and safety notes |
| [Configuration](docs/CONFIGURATION.md) | Privacy-safe camera, dashboard, and serial configuration |
| [Dashboard](docs/DASHBOARD.md) | Interface behavior, video controls, and local API |
| [Arduino LCD](docs/ARDUINO_LCD.md) | Firmware, protocol, display states, and test utility |
| [Testing](docs/TESTING.md) | Automated and manual validation |
| [Privacy](docs/PRIVACY.md) | Local data handling and responsible use |
| [Security](SECURITY.md) | Vulnerability reporting and sensitive-data policy |
| [Contributing](CONTRIBUTING.md) | Development workflow and pull request expectations |

## Hardware summary

```text
ESP32-CAM ── local Wi-Fi video ──> Laptop
Laptop ── USB serial ──> Arduino Uno ── I²C ──> 16×2 LCD
```

The ESP32-CAM and Arduino do not need a direct data wire. See the complete
wiring tables in [docs/HARDWARE.md](docs/HARDWARE.md).

## Commands

| Task | Command |
|---|---|
| Run all tests | `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` |
| Dashboard mode | `.\.venv\Scripts\python.exe -m app.main --source "http://CAMERA_HOST:81/stream" --ui web` |
| OpenCV mode | `.\.venv\Scripts\python.exe -m app.main --source "http://CAMERA_HOST:81/stream" --ui opencv` |
| Arduino LCD test | `.\.venv\Scripts\python.exe tools\test_lcd_serial.py --port COM_PORT` |

Run `python -m app.main --help` for all configuration options.

## Open source and contributions

This repository is available under the [MIT License](LICENSE). Contributions are
welcome; please read [CONTRIBUTING.md](CONTRIBUTING.md),
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md), and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) before opening an issue or pull
request.

The MIT License covers this repository's original code and documentation only.
YOLO weights, Ultralytics, and other dependencies have their own terms; review
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) before commercial use.

## Privacy and security

The project is local by default and does not include cloud storage, analytics,
or telemetry. Never commit network hosts, Wi-Fi credentials, API keys, model
weights, captured media, logs with personal data, or serial identifiers. Use
placeholders such as `CAMERA_HOST` and `COM_PORT` in public examples.

See [docs/PRIVACY.md](docs/PRIVACY.md) for responsible-use guidance.
