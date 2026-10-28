"""Pretrained YOLO11n person-only detection."""

from __future__ import annotations

from typing import Any, Iterable, Sequence, TypedDict


PERSON_CLASS_ID = 0


class Detection(TypedDict):
    """A single accepted person detection."""

    bbox: list[int]
    confidence: float
    class_id: int
    label: str


def _to_list(value: Any) -> list[Any]:
    """Convert a Torch-like tensor or a regular sequence to a Python list."""
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "tolist"):
        return value.tolist()
    return list(value)


def filter_person_detections(
    boxes: Iterable[Sequence[float]],
    confidences: Iterable[float],
    class_ids: Iterable[float],
    confidence_threshold: float,
) -> list[Detection]:
    """Return only COCO class 0 detections at or above the threshold."""
    detections: list[Detection] = []
    for box, confidence, class_id in zip(boxes, confidences, class_ids):
        confidence_value = float(confidence)
        class_id_value = int(class_id)
        if class_id_value != PERSON_CLASS_ID or confidence_value < confidence_threshold:
            continue
        if len(box) != 4:
            raise ValueError("Each bounding box must contain x1, y1, x2, and y2.")
        detections.append(
            {
                "bbox": [int(round(float(coordinate))) for coordinate in box],
                "confidence": confidence_value,
                "class_id": PERSON_CLASS_ID,
                "label": "person",
            }
        )
    return detections


class PersonDetector:
    """Load YOLO once and perform one person-only inference per input frame."""

    def __init__(
        self,
        model_path: str = "yolo11n.pt",
        confidence: float = 0.35,
        image_size: int = 640,
        device: str = "cpu",
        *,
        model: Any | None = None,
    ) -> None:
        if not 0.0 < confidence <= 1.0:
            raise ValueError("confidence must be greater than 0 and at most 1.")
        if image_size <= 0:
            raise ValueError("image_size must be positive.")

        if model is None:
            try:
                from ultralytics import YOLO

                model = YOLO(model_path)
            except Exception as exc:
                raise RuntimeError(
                    f"Unable to load YOLO model '{model_path}'. On first use, "
                    "connect to the internet so Ultralytics can download it."
                ) from exc

        self.model = model
        self.confidence = confidence
        self.image_size = image_size
        self.device = device

    def detect(self, frame: Any) -> list[Detection]:
        """Run YOLO once and return a plain list of accepted people."""
        try:
            results = self.model.predict(
                source=frame,
                classes=[PERSON_CLASS_ID],
                conf=self.confidence,
                imgsz=self.image_size,
                device=self.device,
                verbose=False,
            )
        except Exception as exc:
            raise RuntimeError(f"YOLO inference failed: {exc}") from exc

        if not results:
            return []
        boxes = getattr(results[0], "boxes", None)
        if boxes is None or len(boxes) == 0:
            return []

        return filter_person_detections(
            boxes=_to_list(boxes.xyxy),
            confidences=_to_list(boxes.conf),
            class_ids=_to_list(boxes.cls),
            confidence_threshold=self.confidence,
        )
