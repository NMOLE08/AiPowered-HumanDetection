# System Architecture

Sentinel Vision is a local, single-process computer-vision application. It
performs inference on the laptop; the ESP32-CAM only captures and streams video.

```mermaid
flowchart TB
    CAM[ESP32-CAM camera] -->|MJPEG over local Wi-Fi| STREAM[CameraStream]
    STREAM -->|latest frame only| WORKER[Detection worker]
    WORKER --> YOLO[YOLO11n model]
    YOLO --> FILTER[Filter COCO person class 0]
    FILTER --> COUNTER[PersonCounter]
    COUNTER --> STATE[LiveState]
    STATE --> API[FastAPI]
    API --> WEB[Browser dashboard]
    COUNTER --> SERIAL[LCDSerial]
    SERIAL --> UNO[Arduino Uno]
    UNO --> LCD[16×2 I²C LCD]
```

## Single source of truth

The detection worker owns one `CameraStream`, one `PersonDetector`, and one
`PersonCounter`. After each accepted detection cycle, it publishes the count,
detections, measurements, and latest frame to `LiveState`.

- The dashboard reads the latest state through FastAPI.
- The dashboard's MJPEG endpoint draws overlays from the same detections.
- `LCDSerial` receives the same accepted `current_count`.
- Browser clients do not trigger model inference, camera reads, or Arduino writes.

This design prevents duplicate YOLO work and prevents a growing frame queue.

## Camera and inference lifecycle

```mermaid
stateDiagram-v2
    [*] --> Connecting
    Connecting --> Streaming: camera opens
    Connecting --> Disconnected: opening fails
    Streaming --> Detecting: newest frame available
    Detecting --> Streaming: result published
    Streaming --> Reconnecting: frame timeout
    Reconnecting --> Streaming: camera recovers
    Reconnecting --> Disconnected: retries exhausted
    Disconnected --> [*]
```

`CameraStream` retains one decoded newest frame. If inference takes longer than
capture, older frames are replaced rather than queued. The count becomes
unavailable when the camera is reconnecting or a detection result becomes stale;
the dashboard does not turn that condition into a count of zero.

## Dashboard data flow

```mermaid
sequenceDiagram
    participant C as ESP32-CAM
    participant W as Detection worker
    participant S as LiveState
    participant A as FastAPI
    participant B as Browser
    participant L as Arduino LCD

    C->>W: newest MJPEG frame
    W->>W: YOLO11n and person count
    W->>S: frame, detections, count, timing, status
    W->>L: COUNT:n newline
    B->>A: GET /api/status
    A->>S: snapshot
    S-->>A: current observed state
    A-->>B: compact JSON
    B->>A: GET /video_feed
    A->>S: newest frame and detections
    A-->>B: annotated multipart MJPEG
```

## Important boundaries

- The ESP32-CAM does not run YOLO.
- The Arduino does not decide the human count; it displays the laptop's latest
  accepted value.
- The browser is a presentation layer, not a second detection pipeline.
- No database, cloud service, telemetry, or public internet exposure is required.
