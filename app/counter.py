"""Current per-frame person counting."""

from __future__ import annotations

from collections.abc import Iterable

from app.detector import Detection


class PersonCounter:
    """Store the visible-person count for the latest processed frame."""

    def __init__(self) -> None:
        self.current_count = 0

    def update(self, detections: Iterable[Detection]) -> int:
        """Replace the current count with the accepted detections in one frame."""
        self.current_count = sum(
            1 for detection in detections if detection["class_id"] == 0
        )
        return self.current_count

    def clear(self) -> int:
        """Clear stale state when no current camera frame is available."""
        self.current_count = 0
        return self.current_count
