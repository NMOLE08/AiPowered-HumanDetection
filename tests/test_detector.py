"""Tests for person filtering and single-pass inference."""

import unittest

from app.detector import PersonDetector, filter_person_detections


class FakeBoxes:
    def __init__(self) -> None:
        self.xyxy = [[1.2, 2.4, 30.6, 40.8], [5, 6, 7, 8], [9, 10, 11, 12]]
        self.conf = [0.91, 0.99, 0.20]
        self.cls = [0, 2, 0]

    def __len__(self) -> int:
        return len(self.xyxy)


class FakeResult:
    boxes = FakeBoxes()


class FakeModel:
    def __init__(self) -> None:
        self.calls = []

    def predict(self, **kwargs):
        self.calls.append(kwargs)
        return [FakeResult()]


class PersonDetectorTests(unittest.TestCase):
    def test_filter_keeps_only_people_above_confidence(self) -> None:
        detections = filter_person_detections(
            boxes=[[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]],
            confidences=[0.9, 0.8, 0.2],
            class_ids=[0, 2, 0],
            confidence_threshold=0.35,
        )
        self.assertEqual(
            detections,
            [
                {
                    "bbox": [1, 2, 3, 4],
                    "confidence": 0.9,
                    "class_id": 0,
                    "label": "person",
                }
            ],
        )

    def test_detector_runs_one_inference_and_returns_plain_data(self) -> None:
        model = FakeModel()
        detector = PersonDetector(
            confidence=0.35,
            image_size=640,
            device="cpu",
            model=model,
        )
        detections = detector.detect(frame="fake-frame")

        self.assertEqual(len(model.calls), 1)
        self.assertEqual(model.calls[0]["classes"], [0])
        self.assertEqual(model.calls[0]["imgsz"], 640)
        self.assertEqual(model.calls[0]["device"], "cpu")
        self.assertEqual(
            detections,
            [
                {
                    "bbox": [1, 2, 31, 41],
                    "confidence": 0.91,
                    "class_id": 0,
                    "label": "person",
                }
            ],
        )

    def test_empty_model_result_is_safe(self) -> None:
        class EmptyModel:
            @staticmethod
            def predict(**kwargs):
                return []

        detector = PersonDetector(model=EmptyModel())
        self.assertEqual(detector.detect(frame="fake-frame"), [])

    def test_invalid_detector_settings_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "confidence"):
            PersonDetector(confidence=0.0, model=FakeModel())


if __name__ == "__main__":
    unittest.main()
