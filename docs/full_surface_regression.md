# Full surface regression

`tools/run_full_surface_regression.py` runs the normal and hard candidates
through the complete preparation/battle surface matrix without modifying a
release ROM or SRAM.

The default scope is Scenario 1 through 31. It keeps six isolated Xvfb +
BlastEm workers per profile (12 emulators total) and assigns scenarios to the
next free worker. Giving all 62 profile/scenario combinations their own live
emulator at once is possible in principle, but it oversubscribes CPU and makes
timed controller input less reliable; bounded parallelism is faster and
repeatable on this host.

The regression covers:

- every allied commander root page and offered mercenary-hire page;
- a static lifetime check for 64,890 normal, hard, latent-roster, class-change,
  and synthetic all-mercenary text combinations, so an identically corrupted
  pre/post screen cannot pass merely because both captures match;
- every preparation-visible allied, NPC, and enemy detail page;
- every requested scenario is identified again from its loaded fixed-record
  runtime groups before a capture is accepted, so a missed selector input
  cannot silently validate the wrong scenario;
- commander/class/mercenary labels and arrangement roster pages before and
  after a real shop round trip;
- a synthetic, isolated commander save that offers all 16 mercenaries across
  six pages (the ROM and release saves remain unchanged);
- Cross and Necklace shop rows with exact accepted-image comparison;
- one real Elwin/Fighter move and gray acted sprite in every scenario;
- a separate Scenario 12 route that hires six actual Pikes, moves one Pike,
  and compares all 16 ordinary mercenary gray silhouettes with their original
  ROM source before and after that action;
- fixed and dynamic mercenary sprite-cache rows, both animation frames, and
  their exact ROM source bytes.

Preview the commands without launching emulators:

```sh
python3 tools/run_full_surface_regression.py plan \
  --normal-rom tmp/candidate-normal.md \
  --hard-rom tmp/candidate-hard.md \
  --run-id candidate-full01
```

Run the matrix:

```sh
python3 tools/run_full_surface_regression.py run \
  --normal-rom tmp/candidate-normal.md \
  --hard-rom tmp/candidate-hard.md \
  --run-id candidate-full01
```

The consolidated result is written under
`tmp/full_surface_regression/<run-id>/summary.json`; every failed scenario
also retains its PNGs, controller log, and GST state for diagnosis.

## Current regression findings

- `battle-glyph-full01` exposed an automation error: scenario entry may leave
  `용병고용` focused on the right, and C (not B) enters the left commander
  list. The runner now observes the cursor and uses the correct transition.
- A B1.0.2 playtest then showed a stronger failure that exact pre/post image
  comparison could not detect: `쉐리` initially appeared as `제리`, `키스` as
  `메스`, and Hangul blocks covered Monk/Ballista icons. The renderer keeps
  latent roster-page glyphs alive, and its low scratch cells overlapped the
  ordinary mercenary icon cache. The static lifetime verifier now checks all
  such co-resident glyphs, while both preparation and battle use scratch tiles
  outside `0x0348..0x0387`.
- The first `glyph-lifetime-full01` run also exposed two false gates in the
  harness itself. Fast Scenario-select taps made the requested Scenario 3 open
  Scenario 1, and a dropped shop-list tap labeled Runestone as Cross. Selector
  and shop inputs now use explicit 120 ms press/release events; preparation
  captures are rejected unless the loaded scenario identity matches, and the
  shop capture gets a longer startup window plus one automatic retry.
- A corrected Scenario 3 can be combined with an otherwise valid existing run
  through `--normal-run-id-overrides` and `--hard-run-id-overrides` in
  `tools/verify_preparation_scenario_identity.py` and
  `tools/verify_battle_mercenary_sprite_cache.py`. This avoids rerunning all 31
  scenarios when only one captured scenario was invalid.
- The user's acted-unit capture was an actual `파이크` (`0x62`), which the
  earlier Elwin/Fighter move did not cover. Its first gray tile is `0x03B0`,
  exactly the former dynamic Hangul slot 10. The battle pool now avoids the
  complete ordinary gray range `0x03B0..0x03EF`. Fresh normal (`CB53`) and
  hard (`E15E`) Scenario 12 probes each hire six Pikes and move one from
  `(9,27)` to `(8,27)` with acted flag `0 -> 1`; all 16 ordinary gray cache
  entries match source before and after the move. See
  `localization/pike_acted_surface_regression.json`.
