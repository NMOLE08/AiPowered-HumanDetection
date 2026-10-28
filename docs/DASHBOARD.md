# Sentinel Vision Dashboard

## Running locally

```powershell
.\.venv\Scripts\python.exe -m app.main --source "http://CAMERA_HOST:81/stream" --ui web
```

Open the local address printed by the terminal. Web mode starts FastAPI and a
single background detection worker; it does not use the OpenCV popup window.

## Main panels

- **Humans detected:** current visible person count from the latest valid YOLO result.
- **Connection status:** observed camera, model, and serial-port states.
- **AI metrics:** measured processing FPS, latest inference time, model name,
  source resolution, and last successful update time.
- **Recent activity:** small in-memory session history of count and connection changes.
- **CAM 01:** annotated latest MJPEG frame with responsive letterboxing.

The count is not a total number of visitors or an occupancy record. It is the
number of accepted person boxes in one processed frame.

## Video controls

| Control | Behavior |
|---|---|
| Boxes | Shows or hides person bounding boxes |
| Labels | Shows or hides person/confidence labels |
| Fullscreen | Expands the video panel using the browser Fullscreen API |

Changing a control creates no camera capture or model inference. It changes only
the rendering of the latest shared frame for that browser client.

## API

| Endpoint | Description |
|---|---|
| `/` | Dashboard HTML page |
| `/api/status` | Small JSON snapshot for polling clients |
| `/video_feed` | Annotated multipart MJPEG stream |
| `/health` | Process health summary |

`/api/status` reports `human_count` as `null` with `count_valid: false` if no
recent valid result exists. This distinction prevents an unavailable camera from
appearing as a valid zero-person scene.

The browser polls status every 500 milliseconds. The video is delivered as MJPEG
from the backend's shared latest frame.
