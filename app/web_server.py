"""FastAPI dashboard and the single shared live-detection worker."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from threading import Event, Thread, current_thread
from time import perf_counter
from typing import Iterator

import cv2
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.camera import CameraReadTimeout, CameraStream
from app.config import AppConfig
from app.counter import PersonCounter
from app.detector import Detection, PersonDetector
from app.lcd_serial import CAMERA_OFFLINE, LCDSerial
from app.live_state import LiveState
from app.visualizer import FPSMeter, Visualizer


FRONTEND_ROOT = Path(__file__).resolve().parents[1] / "frontend"
TEMPLATES = Jinja2Templates(directory=str(FRONTEND_ROOT / "templates"))
MJPEG_BOUNDARY = "sentinel-frame"


def normalize_camera_status(status: str) -> str:
    """Translate CameraStream labels into compact dashboard status values."""
    return {
        "CONNECTED": "connected",
        "RECONNECTING": "reconnecting",
        "DISCONNECTED": "disconnected",
    }.get(status, "reconnecting")


def multipart_frame(jpeg: bytes) -> bytes:
    """Encode one JPEG in the multipart format used by browser MJPEG images."""
    return (
        f"--{MJPEG_BOUNDARY}\r\n"
        "Content-Type: image/jpeg\r\n"
        f"Content-Length: {len(jpeg)}\r\n\r\n"
    ).encode("ascii") + jpeg + b"\r\n"


class DetectionService:
    """Own exactly one camera/inference/LCD pipeline for dashboard clients."""

    def __init__(self, config: AppConfig, detector: PersonDetector, state: LiveState) -> None:
        self.config = config
        self.detector = detector
        self.state = state
        self._stop = Event()
        self._thread: Thread | None = None
        self._camera: CameraStream | None = None
        self._lcd: LCDSerial | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self.state.set_model_status("ready")
        self._thread = Thread(
            target=self._run,
            name="sentinel-detection-worker",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._camera is not None:
            self._camera.close()
        thread = self._thread
        if thread is not None and thread is not current_thread():
            thread.join(timeout=3.0)
        if self._lcd is not None:
            self._lcd.close()
        self._thread = None

    def _update_arduino_state(self, lcd: LCDSerial) -> None:
        if not lcd.enabled:
            self.state.set_arduino_status("not_configured")
        elif lcd.connected:
            self.state.set_arduino_status("connected")
        else:
            self.state.set_arduino_status("reconnecting")

    def _run(self) -> None:
        assert self.config.source is not None
        camera = CameraStream(
            self.config.source,
            max_reconnect_attempts=self.config.reconnect_attempts,
            reconnect_delay=self.config.reconnect_delay,
        )
        lcd = LCDSerial(self.config.serial_port, self.config.serial_baud)
        counter = PersonCounter()
        fps_meter = FPSMeter()
        detections: list[Detection] = []
        frame_number = 0
        needs_inference = True
        self._camera = camera
        self._lcd = lcd
        self._update_arduino_state(lcd)

        try:
            self.state.set_camera_status("connecting")
            camera.open()
            self.state.set_camera_status("connected")
            while not self._stop.is_set():
                self._update_arduino_state(lcd)
                try:
                    frame = camera.read(timeout=self.config.read_timeout)
                except CameraReadTimeout:
                    counter.clear()
                    detections = []
                    lcd.publish_status(CAMERA_OFFLINE)
                    self.state.mark_detection_unavailable(normalize_camera_status(camera.status))
                    needs_inference = True
                    continue

                should_infer = needs_inference or (
                    frame_number % (self.config.frame_skip + 1) == 0
                )
                if should_infer:
                    inference_started = perf_counter()
                    detections = self.detector.detect(frame)
                    inference_ms = (perf_counter() - inference_started) * 1000.0
                    count = counter.update(detections)
                    fps = fps_meter.update()
                    self.state.record_detection(
                        frame, detections, count, fps, inference_ms
                    )
                    needs_inference = False
                else:
                    self.state.record_display_frame(frame, detections)

                frame_number += 1
                # Publish the same accepted current-frame count used by LiveState.
                lcd.publish_count(counter.current_count)

        except ConnectionError as exc:
            counter.clear()
            lcd.publish_status(CAMERA_OFFLINE)
            self.state.mark_detection_unavailable("disconnected", str(exc))
            self.state.add_event("Camera worker stopped after connection failure", "error")
        except RuntimeError as exc:
            counter.clear()
            lcd.publish_status(CAMERA_OFFLINE)
            self.state.set_model_status("error", str(exc))
            self.state.mark_detection_unavailable("disconnected", str(exc))
            self.state.add_event("Detection worker stopped after inference failure", "error")
        finally:
            camera.close()
            lcd.close()
            self._update_arduino_state(lcd)


def mjpeg_stream(
    state: LiveState, show_boxes: bool, show_labels: bool, *, once: bool = False
) -> Iterator[bytes]:
    """Yield dashboard-rendered JPEGs from the shared newest frame only."""
    version = -1
    while True:
        snapshot = state.get_frame_after(version, timeout=1.0)
        if snapshot is None:
            if once:
                return
            continue
        version, frame, detections = snapshot
        annotated = Visualizer.annotate_for_web(
            frame,
            detections,
            show_boxes=show_boxes,
            show_labels=show_labels,
        )
        encoded, jpeg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if encoded:
            yield multipart_frame(jpeg.tobytes())
        if once:
            return


def create_dashboard_app(
    config: AppConfig,
    detector: PersonDetector | None = None,
    *,
    state: LiveState | None = None,
    start_service: bool = True,
) -> FastAPI:
    """Create the local FastAPI application without duplicating the pipeline."""
    live_state = state or LiveState(config.source or "")
    service = (
        DetectionService(config, detector, live_state)
        if start_service and detector is not None
        else None
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if service is not None:
            service.start()
        try:
            yield
        finally:
            if service is not None:
                service.stop()

    app = FastAPI(title="Sentinel Vision", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(FRONTEND_ROOT / "static")), name="static")
    app.state.live_state = live_state

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        return TEMPLATES.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={"title": "Sentinel Vision"},
        )

    @app.get("/api/status")
    async def status() -> JSONResponse:
        return JSONResponse(live_state.status_snapshot())

    @app.get("/health")
    async def health() -> JSONResponse:
        snapshot = live_state.status_snapshot()
        healthy = snapshot["model"] == "ready" and snapshot["camera"] == "connected"
        return JSONResponse({"status": "ok" if healthy else "degraded", "healthy": healthy})

    @app.get("/video_feed")
    async def video_feed(
        boxes: bool = True, labels: bool = True, once: bool = False
    ) -> StreamingResponse:
        return StreamingResponse(
            mjpeg_stream(live_state, boxes, labels, once=once),
            media_type=f"multipart/x-mixed-replace; boundary={MJPEG_BOUNDARY}",
            headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
        )

    return app


def run_dashboard(config: AppConfig, detector: PersonDetector) -> int:
    """Run one local dashboard process and one detection worker."""
    app = create_dashboard_app(config, detector)
    url = f"http://{config.web_host}:{config.web_port}"
    print(f"Sentinel Vision dashboard: {url}")
    print("Open the URL in a browser. Press Ctrl+C in this terminal to stop.")
    uvicorn.run(app, host=config.web_host, port=config.web_port, workers=1, log_level="info")
    return 0
