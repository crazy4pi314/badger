# Fork & Flora

An offline prototype for Universe 2026 and the stock Tufty
[browser simulator](https://try.badgewa.re/). Choose or skip a broad region,
plant candidate species in a tray of six pots, care for them through four
stages, move blooming plants out to a shared garden, and collect local sample
seeds. Plants never die or lose progress while away.

## Try it in the browser

Select Tufty if asked. Create a Python file in the simulator editor and paste
the **entire contents of `__init__.py`** into it, then press Run/F5. No supporting
modules or assets are required. Click the badge to give keyboard input focus.

| Action | Simulator key | Universe control |
| --- | --- | --- |
| Previous option | Left (Up outside the tray) | Left |
| Next option | Right | Right |
| Select / confirm | Space (B) | Select |
| Choose pot (tray only) | Up / Down | Up / Down |
| Back / cancel | Down outside the tray | Back, or Down outside the tray |
| Leave app | Escape (Home) | Home |

The explicit stock-Tufty adapter maps A/B/C to previous/select/next; it does
not assume stock physical wiring matches the Universe board. Menu navigation
uses press events, not repeated holds. Everything fits the default 160x120
logical surface. Persistence uses `/state/fork_flora.json`; rerunning should
restore the garden. Browser-site storage clearing removes simulator files.

Walkthrough: Select to begin, choose a region or Skip, select a species,
then Select to plant. The main screen is a **tray of six pots** (3x2 grid).
Up/Down chooses a pot; its name and stage appear in the header, and blooming
pots show a small sun marker. Actions apply to the selected pot and appear as
a cycling icon bar at the bottom of the screen (Care, Inspect, Move to garden,
View garden, New plant, Seed box, Change region, Trade, Sample seed); the
selected icon's name is shown above it. Use Left/Right to browse actions.

Select on **Care** starts a one-minute care session with falling water drops,
a rotating sun, and a progress bar; the plant grows one stage when it
finishes. Down stops care without penalty, and leaving the app cancels an
unfinished session. Blooming plants cannot be cared for further.

**New plant** fills the selected pot if empty, otherwise the first empty pot.
If all six pots are full it asks before replacing the selected pot;
cancelling preserves it. **Move to garden** moves a blooming plant out of the
tray, freeing its pot. **View garden** shows every moved flower overlapping on
one meadow screen, back to front, at stable deterministic positions (up to
30 flowers). **Change region** changes suggestions, not existing plants. Skip
gives access to the entire catalog.

**Sample seed** adds a clearly labeled local test seed to the six-slot seed
box. Open Seed box, inspect a seed, and plant it into an open pot (or replace
the selected pot when the tray is full) or discard it. The inbox rejects
duplicates and full inboxes without removing another seed.

**Trade (IR)** is an honest unavailable screen, not a simulated success.
No IR hardware, networking, location inference, or motion APIs are accessed.
Actual attendee trading remains a future milestone requiring two real badges
and verified transmit/receive support. Future exchanges should copy a seed,
not remove the sender's plant, and preserve species/seed/recipe identity.

## Architecture

This first vertical slice is intentionally self-contained for paste-and-run
testing. Pure `Garden`, `App` scene transitions, validation, and
`plant_recipe()` are independent of the badge; `start()` supplies drawing,
input adaptation, and persistence. These boundaries can become separate modules
once simulator packaging is settled.

The renderer caches one deterministic rectangle recipe per species, seed,
and stage. A fixed 32-bit PRNG (not Python's hash) gives reproducible bounded
variation. Four stylized growth habits distinguish silhouettes. All art is
generated from verified rectangle primitives; no external plant sprites load.
Recipe version 1 is reserved in saved seed records for future compatibility.

Saves use schema 2 (`tray` of six pots plus a `garden` list). Schema 1 saves
with a single `plant` migrate automatically into pot 1.

Bad or incompatible saves produce an explicit message and a temporary garden,
without overwriting the original save. Write failures are reported; this visit
then continues in memory. State writes are read back because some Badgeware
`State.save` implementations silently swallow filesystem errors. To recover
from a bad save in the simulator, back up then remove only
`/state/fork_flora.json` from its Files pane and rerun.

## Draft botanical content

The twelve regions and twelve species are **prototype candidates**, not
reviewed assertions of native range. One species per region currently exercises
selection; expand to 2-3 reviewed species per region before a public release.
The date palm particularly illustrates why cultivation and uncertain origin
must not be confused with native distribution. Geographic partitions are
coarse browsing suggestions, not a country-level ecological model.

All illustrations are stylized, not field-identification guides. Names and
morphology copy need botanical review. For each candidate, verify accepted
scientific name, native distribution and fact against
[Plants of the World Online](https://powo.science.kew.org/) and an appropriate
regional flora; record source and reviewer before treating it as approved.
No seed trades should encode attendee region or personal identity.

## Checks

From the repository root:

```powershell
python -m unittest discover -s tests -p test_fork_flora.py
```

The stock browser simulator cannot establish correctness of custom Universe
touch, automatic inversion, or IR wiring. Those require the actual 2026 badge.
No claim of real hardware validation is made by running the browser version.
