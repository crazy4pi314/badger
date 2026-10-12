import importlib.util
import pathlib
import unittest


MODULE_PATH = (
    pathlib.Path(__file__).parents[1]
    / "badge"
    / "apps"
    / "safe_cracker"
    / "gesture.py"
)
SPEC = importlib.util.spec_from_file_location("safe_cracker_gesture", MODULE_PATH)
gesture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gesture)


class GestureRecognizerTests(unittest.TestCase):
    def calibrated_recognizer(self, minimum_motion_ms=20):
        recognizer = gesture.GestureRecognizer(
            calibration_ms=100,
            quiet_ms=40,
            minimum_motion_ms=minimum_motion_ms,
        )
        for now in range(0, 121, 20):
            recognizer.update((1000, 0, 0, 0, 0, 0), now)
        self.assertTrue(recognizer.calibrated)
        return recognizer

    def perform(self, recognizer, axis, peak):
        sample = [1000, 0, 0, 0, 0, 0]
        sample[axis + 3] = peak
        recognizer.update(tuple(sample), 140)
        recognizer.update(tuple(sample), 180)
        recognizer.update((1000, 0, 0, 0, 0, 0), 200)
        return recognizer.update((1000, 0, 0, 0, 0, 0), 250)

    def test_classifies_each_supported_direction(self):
        cases = (
            (0, -40, "TIP_UP"),
            (0, 40, "TIP_DOWN"),
            (1, -40, "TURN_LEFT"),
            (1, 40, "TURN_RIGHT"),
            (2, -40, "ROLL_LEFT"),
            (2, 40, "ROLL_RIGHT"),
        )
        for axis, peak, expected in cases:
            with self.subTest(expected=expected):
                result = self.perform(self.calibrated_recognizer(), axis, peak)
                self.assertEqual(expected, result["label"])
                self.assertGreaterEqual(result["confidence"], 0.35)

    def test_ignores_short_motion(self):
        recognizer = self.calibrated_recognizer(minimum_motion_ms=100)
        recognizer.update((1000, 0, 0, 0, 40, 0), 140)
        recognizer.update((1000, 0, 0, 0, 0, 0), 145)
        result = recognizer.update((1000, 0, 0, 0, 0, 0), 190)
        self.assertIsNone(result)

    def test_calibration_uses_observed_noise(self):
        recognizer = gesture.GestureRecognizer(calibration_ms=100)
        for index, now in enumerate(range(0, 121, 20)):
            wobble = -2 if index % 2 else 2
            recognizer.update((1000 + wobble, 0, 0, wobble, 0, 0), now)
        self.assertGreaterEqual(recognizer.accel_thresholds[0], 24)
        self.assertGreaterEqual(recognizer.gyro_thresholds[0], 24)


if __name__ == "__main__":
    unittest.main()
