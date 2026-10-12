# Universe Badge 2026 Concepts

## Goal
Develop an offline-first set of seven design briefs for potential GitHub Universe 2026 badge apps, supported by reusable gesture-recognition and badge-to-badge IR design documents. Compare the concepts and recommend one or two to build.

## Shared design documents
- **Gesture recognition:** define a reusable approach for recording, calibrating, recognizing, and triggering motion gestures across apps.
- **IR protocol:** define a reusable approach for pairing badges and exchanging small messages, with verification of the transmit path before depending on it.

## App briefs
1. **Gesture Snowglobe:** combine a gesture trainer with a digital snowglobe; different recognized gestures trigger different snowglobe effects.
2. **Fork & Flora:** grow and exchange plants reflecting broad geographic regions and native flora.
3. **Mona accessibility companion:** let users set their current feeling, stimulation level, and desired interaction level; show a companion status while keeping a private journal on the badge.
4. **Bop-it-style gesture game:** provide solo high-score play and a versus mode where two badges start together over IR and compare scores.
5. **Secret Handshake:** pair badges, copy a sequence of movements, and save the handshake under a fun name.
6. **IR Courier:** send small messages or postcards between badges.
7. **Safe Cracker:** open a virtual safe by solving a motion-based combination puzzle.

## Decisions and constraints
- Fork & Flora starts offline with attendee selection from about 12 broad regions. Country selection and a companion web page are stretch goals.
- Mona has both a visible status and a private on-badge journal.
- Versus play starts both badges together over IR, then compares scores.
- Design gesture and IR mechanisms once for reuse across apps.
- Every brief should distinguish MVP from stretch scope and document hardware/API dependencies plus unresolved feasibility checks.
- Use current Universe 2026 documentation; do not treat legacy 2025 runtime examples as authoritative.
- IMU units/scaling are undocumented in the available app source; calibrate against relative readings. There is no magnetometer, so avoid absolute compass-heading claims.
- Touch is exposed as discrete logical inputs, not pressure or a continuous trackpad.
- IR transmit-path support must be verified; the existing `quest` example demonstrates reception, not complete two-way transport.

## Planned output structure
- `universe-badge-2026/README.md` — comparison and recommendation.
- `universe-badge-2026/GESTURE-RECOGNITION.md`
- `universe-badge-2026/IR-PROTOCOL.md`
- `universe-badge-2026/ideas/01-gesture-snowglobe.md` through `07-safe-cracker.md` — consistent design briefs.

## Progress
The delegated implementation session reported all 10 Markdown deliverables complete, with local links checked and hardware feasibility caveats documented. The files live in the separate `experiments` folder project.
