"""Tests for the local FastAPI dashboard and shared live state."""

from __future__ import annotations

import time
import unittest

import numpy as np
from fastapi.testclient import TestClient

from app.config import parse_config
from app.live_state import LiveState
from app.web_server import MJPEG_BOUNDARY, create_dashboard_app, multipart_frame


def detection() -> dict:
    return {
        "bbox": [10, 15, 80, 100],
        "confidence": 0.91,
        "class_id": 0,
        "label": "person",
    }


class WebDashboardTests(unittest.TestCase):
    def make_app(self):
        config = parse_config(
            ["--source", "http://camera.local:81/stream", "--ui", "web"]
        )
        state = LiveState(config.source or "", stale_after_seconds=0.5)
        state.set_model_status("ready")
        state.set_camera_status("connected")
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        state.record_detection(frame, [detection()], 1, 8.5, 42.2)
        return create_dashboard_app(config, state=state, start_service=False), state

    def test_dashboard_page_and_status_api_use_observed_state(self) -> None:
        app, _ = self.make_app()
        with TestClient(app) as client:
            page = client.get("/")
            status = client.get("/api/status")
            health = client.get("/health")

        self.assertEqual(page.status_code, 200)
        self.assertIn("Sentinel Vision", page.text)
        self.assertEqual(status.status_code, 200)
        payload = status.json()
        self.assertEqual(payload["human_count"], 1)
        self.assertTrue(payload["count_valid"])
        self.assertEqual(payload["camera"], "connected")
        self.assertEqual(payload["resolution"], {"width": 320, "height": 240})
        self.assertEqual(health.json(), {"status": "ok", "healthy": True})

    def test_video_endpoint_delivers_one_annotated_mjpeg_frame(self) -> None:
        app, _ = self.make_app()
        with TestClient(app) as client:
            response = client.get("/video_feed?boxes=true&labels=true&once=true")

        self.assertEqual(response.status_code, 200)
        self.assertIn("multipart/x-mixed-replace", response.headers["content-type"])
        self.assertIn(f"--{MJPEG_BOUNDARY}".encode(), response.content)
        self.assertIn(b"Content-Type: image/jpeg", response.content)
        self.assertIn(b"\xff\xd8", response.content)

    def test_stale_detection_hides_count_instead_of_returning_old_value(self) -> None:
        state = LiveState("mock://camera", stale_after_seconds=0.01)
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        state.record_detection(frame, [detection()], 1, 5.0, 80.0)
        time.sleep(0.02)

        payload = state.status_snapshot()
        self.assertIsNone(payload["human_count"])
        self.assertFalse(payload["count_valid"])
        self.assertTrue(payload["count_stale"])

    def test_multipart_helper_includes_boundary_and_jpeg_length(self) -> None:
        payload = multipart_frame(b"abc")
        self.assertIn(f"--{MJPEG_BOUNDARY}".encode(), payload)
        self.assertIn(b"Content-Length: 3", payload)
        self.assertTrue(payload.endswith(b"abc\r\n"))


if __name__ == "__main__":
    unittest.main()
