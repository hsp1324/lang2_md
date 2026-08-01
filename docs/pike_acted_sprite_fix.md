# Pike acted-gray sprite correction

The reported unit is the hireable mercenary class `파이크` (`0x62`), not a
generic spearman label. Pike owns the first ordinary mercenary acted-gray
cache entry: tiles `0x03B0..0x03B3`, VRAM `0x7600..0x767F`.

The prior battle name/class dynamic pool assigned slot 10 to `0x03B0`.
Drawing a Korean status field could therefore replace Pike's upper-left gray
tile with a Hangul bitmap. The battle pool now uses 16 ownership-audited high
tiles that avoid all ordinary mercenary graphics:

- active frame 0: `0x0348..0x0387`;
- active frame 1: `0x0448..0x0487`;
- acted-gray silhouettes: `0x03B0..0x03EF`;
- live H-scroll: `0x07A0..0x07BF`.

`tools/run_pike_acted_surface_probe.py` performs the missing runtime test. It
enters Scenario 12, makes Sherry hire six Pikes, deploys them, moves one Pike
from `(9,27)` to `(8,27)`, and requires its acted flag to change from 0 to 1.
It then compares the four visible Pike tiles and the complete 16-class
ordinary acted-gray cache with the original ROM silhouettes.

Both non-release candidates pass:

- normal checksum `CB53`, SHA-256
  `00f0dec38c01db6489d061476648504164b206d1ef73d57bcb9ec7b63e14d371`;
- hard checksum `E15E`, SHA-256
  `f3d5e050eb84999571c9b575f9236ef01076bbba67542e8af183bf62223bf7ad`.

Pike's expected and actual gray payload SHA-256 is
`0fe0987d6d93be4842ad899ae0dedbf85f1342b86efc6957e53fde7f76aee0a8`.
All 16 ordinary gray entries match source both before and after the move.
Exact state and screenshot hashes are recorded in
`localization/pike_acted_surface_regression.json`. No release ROM or visible
version was changed.
