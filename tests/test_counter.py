"""Tests for current-frame person counting."""

import unittest

from app.counter import PersonCounter


def person(confidence: float = 0.9) -> dict:
    return {
        "bbox": [1, 2, 30, 40],
        "confidence": confidence,
        "class_id": 0,
        "label": "person",
    }


class PersonCounterTests(unittest.TestCase):
    def test_zero_one_and_multiple_people(self) -> None:
        counter = PersonCounter()
        self.assertEqual(counter.update([]), 0)
        self.assertEqual(counter.update([person()]), 1)
        self.assertEqual(counter.update([person(), person(0.8)]), 2)

    def test_clear_removes_stale_count_after_disconnect(self) -> None:
        counter = PersonCounter()
        counter.update([person(), person()])
        self.assertEqual(counter.clear(), 0)
        self.assertEqual(counter.current_count, 0)

    def test_non_person_input_is_not_counted(self) -> None:
        counter = PersonCounter()
        other = {
            "bbox": [0, 0, 10, 10],
            "confidence": 0.9,
            "class_id": 2,
            "label": "car",
        }
        self.assertEqual(counter.update([other]), 0)


if __name__ == "__main__":
    unittest.main()
