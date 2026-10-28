# Configuration and Privacy-Safe Examples

## Camera source

The camera host is intentionally supplied at runtime. Do not place a private
network address in source code, screenshots, commits, issues, or documentation.

```powershell
.\.venv\Scripts\python.exe -m app.main --source "http://CAMERA_HOST:81/stream" --ui web
```

Replace `CAMERA_HOST` locally with the host printed by your ESP32-CAM serial
monitor. Keep the substituted command out of public terminal transcripts.

## Dashboard binding

The dashboard binds to `localhost` by default and is intended for the same
laptop that runs the detector.

```powershell
.\.venv\Scripts\python.exe -m app.main --source "http://CAMERA_HOST:81/stream" --ui web --web-port 8000
```

Avoid binding the dashboard to a network interface unless you understand the
security consequences of exposing a live camera view.

## Arduino serial

The Arduino port is optional and must be supplied explicitly:

```powershell
.\.venv\Scripts\python.exe -m app.main --source "http://CAMERA_HOST:81/stream" --serial-port COM_PORT --ui web
```

Use the port assigned to the Arduino Uno, not a camera programming adapter.

## Sensitive files

The `.gitignore` excludes virtual environments, model weights, `.env` files,
generated video, output folders, and the local implementation plan. Before
committing, inspect staged files with:

```powershell
git status --short
git diff --cached
```

Never commit Wi-Fi credentials, private addresses, tokens, camera captures, or
model files.
