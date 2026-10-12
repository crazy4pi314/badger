# Safe Cracker

Safe Cracker is a motion-or-button sequence game for the Universe 2026 badge.
It uses short badge-relative turns and tips rather than compass directions or
security-sensitive input.

## Controls

- On the title screen, use Left/Right to select motion or button input.
- Use Up/Down to select streak or untimed practice play.
- Press Select to start and confirm the memorized combination.
- Press Back during a game to return to the title screen.
- Press Menu to show motion diagnostics. The diagnostic screen reports the
  current gyroscope readings, calibrated baseline, and adaptive thresholds.

Motion mode calibrates from a short still sample before each combination.
Button mode is a complete fallback and maps the four sequence symbols directly
to the directional controls.

## Hardware tuning

The recognizer deliberately treats `badge.imu()` values as relative readings
because the firmware does not document their physical scale. Before release,
use the diagnostics screen on multiple physical badges to verify axis signs,
thresholds, ordinary-handling false triggers, and comfortable movements in
both badge orientations.
