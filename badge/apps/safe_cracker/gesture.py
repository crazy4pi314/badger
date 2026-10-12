class GestureRecognizer:
    CALIBRATING = 0
    READY = 1
    MOVING = 2

    def __init__(
        self,
        calibration_ms=1200,
        quiet_ms=180,
        minimum_motion_ms=120,
        maximum_motion_ms=1200,
    ):
        self.calibration_ms = calibration_ms
        self.quiet_ms = quiet_ms
        self.minimum_motion_ms = minimum_motion_ms
        self.maximum_motion_ms = maximum_motion_ms
        self.reset(0)

    def reset(self, now):
        self.state = self.CALIBRATING
        self.started_at = now
        self.updated_at = now
        self.last_active_at = now
        self.sample_count = 0
        self.sums = [0] * 6
        self.minimums = [0] * 6
        self.maximums = [0] * 6
        self.baseline = [0] * 6
        self.noise = [0] * 6
        self.gyro_thresholds = [1] * 3
        self.accel_thresholds = [1] * 3
        self.motion_started_at = 0
        self.motion_peaks = [0] * 3
        self.last_sample = [0] * 6

    @property
    def calibrated(self):
        return self.state != self.CALIBRATING

    @property
    def calibration_progress(self):
        if self.state != self.CALIBRATING:
            return 1.0
        elapsed = self.updated_at - self.started_at
        return min(1.0, max(0.0, elapsed / self.calibration_ms))

    def update(self, sample, now):
        self.updated_at = now
        self.last_sample = list(sample)

        if self.state == self.CALIBRATING:
            self._calibrate(sample, now)
            return None

        accel_delta = [
            sample[index] - self.baseline[index]
            for index in range(3)
        ]
        gyro_delta = [
            sample[index + 3] - self.baseline[index + 3]
            for index in range(3)
        ]
        active = self._is_active(accel_delta, gyro_delta)

        if self.state == self.READY:
            if active:
                self.state = self.MOVING
                self.motion_started_at = now
                self.last_active_at = now
                self.motion_peaks = list(gyro_delta)
            return None

        self._record_peaks(gyro_delta)
        if active:
            self.last_active_at = now

        duration = now - self.motion_started_at
        if duration >= self.maximum_motion_ms:
            return self._finish_motion(duration)
        if not active and now - self.last_active_at >= self.quiet_ms:
            return self._finish_motion(duration)
        return None

    def _calibrate(self, sample, now):
        if self.sample_count == 0:
            self.minimums = list(sample)
            self.maximums = list(sample)

        for index, value in enumerate(sample):
            self.sums[index] += value
            self.minimums[index] = min(self.minimums[index], value)
            self.maximums[index] = max(self.maximums[index], value)
        self.sample_count += 1

        if now - self.started_at < self.calibration_ms:
            return

        self.baseline = [
            total / self.sample_count
            for total in self.sums
        ]
        self.noise = [
            maximum - minimum
            for minimum, maximum in zip(self.minimums, self.maximums)
        ]
        accel_reference = max(1, max(abs(value) for value in self.baseline[:3]))
        self.accel_thresholds = [
            max(noise * 6, accel_reference * 0.08, 1)
            for noise in self.noise[:3]
        ]
        self.gyro_thresholds = [
            max(noise * 6, 1)
            for noise in self.noise[3:]
        ]
        self.state = self.READY

    def _is_active(self, accel_delta, gyro_delta):
        for value, threshold in zip(gyro_delta, self.gyro_thresholds):
            if abs(value) >= threshold:
                return True
        for value, threshold in zip(accel_delta, self.accel_thresholds):
            if abs(value) >= threshold:
                return True
        return False

    def _record_peaks(self, gyro_delta):
        for index, value in enumerate(gyro_delta):
            if abs(value) > abs(self.motion_peaks[index]):
                self.motion_peaks[index] = value

    def _finish_motion(self, duration):
        self.state = self.READY
        if duration < self.minimum_motion_ms:
            return None

        axis = max(range(3), key=lambda index: abs(self.motion_peaks[index]))
        peak = self.motion_peaks[axis]
        if abs(peak) < self.gyro_thresholds[axis]:
            return None

        labels = (
            ("TIP_UP", "TIP_DOWN"),
            ("TURN_LEFT", "TURN_RIGHT"),
            ("ROLL_LEFT", "ROLL_RIGHT"),
        )
        label = labels[axis][0 if peak < 0 else 1]
        confidence = min(1.0, abs(peak) / (self.gyro_thresholds[axis] * 4))
        return {
            "label": label,
            "confidence": confidence,
            "duration": duration,
        }
