# Keith, Lester, and Jessica join-class choice

The development builder changes the three pre-initialized commander records at
`0x05E64A` so the characters first become available at their tier-1 class and
stored LV10.  The stock LV10 progression gate then opens the ordinary tier-2
class-choice screen; no Runestone-only recovery path is required.

| Commander | Stock start | New start | Tier-2 choices |
| --- | --- | --- | --- |
| Keith | Hawk Knight LV1, EXP5 | Hawk Knight LV10, EXP5 | Lord / Hawk Lord / Healer |
| Lester | Crocoknight LV7, EXP15 | Crocoknight LV10, EXP15 | Knight / Croco Lord / Shaman |
| Jessica | Sorcerer LV5, EXP0 | Warlock LV10, EXP0 | Healer / Sorcerer / Lord |

The pre-join roster record retains its original residual EXP and
identity/equipment fields.  MP, AT, and DF are back-calculated so replaying the
original branch's ordinary level growth reproduces the Japanese joining stats.
Promoted-class ability and mercenary bits are replaced with the proper tier-1
values before the choice, preventing unselected tier-2 benefits from leaking
into the tier-1 record.  The post-choice grant deliberately does not carry that
residual bar forward: Keith, Lester, and Jessica receive fixed raw amounts
`0x00`, `0x90`, and `0x60`, respectively.  Those values reconstruct only the
original tier-2 level floor, are identical across profiles and selected
branches, and leave each selected class's own EXP gauge to determine the result.
There is no Hard-only bonus or target-level refill loop.

The source-locked LV10 gate at `0x014848` branches to the stock class-choice
path.  The normal selection handler writes the chosen class at `0x014C36` and
resets the level to 1 at `0x014C3A`.

## v1.3.1 to v1.3.6 public regression history

`v1.3.0` was a non-public development tag, not a player release. The save
compatibility cases below therefore begin with released v1.3.1; references to
the development-only v1.3.0 are retained only when explaining the code's
origin.

The released v1.3.1 BPS stored Keith and Lester as Fighter LV10 and retained
their Fighter class-change records.  Earlier documentation generalized Keith's
successful Scenario 7 result to Lester, but a reconstructed v1.3.1 fresh-SRAM
Scenario 10 run disproved that claim: Lester remained Fighter LV10 and gained
only EXP15 -> EXP25 without opening class choice.

v1.3.2 introduced dedicated Hawk Lord and Croco Lord class IDs.  It changed
fresh initial records to Hawk Knight/Crocoknight LV10 and reused each
commander's physical Fighter transition slot for the new Lord transition.
The same change attempted to migrate an older Fighter save inside the exact
LV10 visibility gate.  If the progression scan had already advanced Lester to
Fighter LV11, the initial `cmpi.b #10,$2E(a0)` skipped the migration forever;
the removed Fighter transition then allowed LV12, LV13, and later levels
without any class-choice screen.  v1.3.3 retained that logic unchanged.

v1.3.4 identifies Keith/Lester before the exact-level comparison.  On or after
the first player scenario, and only for a real on-map record, a legacy Fighter
at LV10 or higher is restored to the clean tier-1 LV10 boundary: class, MP,
level, residual EXP, AT, and DF.  The same scan then reaches the stock LV10
class-choice path.  Pre-join NPCs, hidden preparation records, off-map
reinforcements, and a Runestone Fighter below LV10 are left untouched.

That repair solved the damaged-save migration but did not solve Lester's
natural Scenario 10 result.  After the LV10 visibility gate, stock code at
`0x014B2C` applies an ownership-bit filter.  Keith and Jessica arrive with
runtime side value 3 (bit 0 set); Lester's event-owned record retains value 4
(bit 0 clear), so stock result processing skipped only Lester.  Fresh-SRAM
runtime captures on v1.3.6 close all three cases: Keith and Jessica open and
apply their choices, while Lester stays Crocoknight LV10 and gains only ten
EXP.

Runtime and structural evidence for the v1.3.4 recovery is recorded by the
focused join-class tests and the isolated Scenario 11 BlastEm run.

The initial-roster patch applies automatically to new games.  v1.3.4 also
repairs the specific released v1.3.1 Fighter LV10 and v1.3.2/v1.3.3 Fighter
LV11+ save states at runtime; the user's `.srm` does not need to be edited by
an external migration tool. A commander who already selected a non-Fighter
class is never rewritten.

## v1.3.7 Scenario 10 result ownership repair

The ownership filter is now wrapped without changing Lester's scenario record
or side value.  The hook at `0x014B2C` calls the bounded helper at `0x31E380`,
which preserves the original bit test for every ordinary case and grants the
missing fallthrough only when all three conditions hold: commander ID 9,
active Scenario 10, and the outer stock result callback `0x00CEC4` at the top
of the scheduler stack.  The helper also reproduces the displaced
`subq.w #1,d1` before returning to unmodified class-chain handling.

This excludes ordinary/end-turn callbacks, pre-join scans, later scenarios,
Runestone restarts, and every other commander.  On the corrected candidate,
the same fresh-SRAM Scenario 10 path visibly opens
`나이트 / 크로코로드 / 샤먼`.  The one-time, branch-independent raw EXP grant
is `0x90` (the Japanese Crocoknight LV7 floor, excluding its residual EXP15),
so the selected class's own gauge determines the result: Knight reaches
LV5/EXP16, while Croco Lord and Shaman reach LV7/EXP0.  The result persists to
the Scenario 11 save, and all three release profiles are covered separately by
the runtime regression matrix.

### v1.3.7 cold/warm manual-load scenario context gate

The first v1.3.7 candidate treated WRAM word `0xA612` as the live scenario.
Source locking shows that this word is actually the scenario-selector scratch:
stock code copies persisted active scenario `0xA49C` into `0xA612` when the
selector opens and copies it back when a choice is confirmed. The ordinary
save descriptor serializes `0xA49C`, but not `0xA612`.

Consequently, loading an old SRAM from the title screen in a cold emulator
process left `0xA612=0` even though the active scenario had been restored. A
warm LOAD was more dangerous: `0xA612` could retain an unrelated nonzero value
from a previous selector or result. Testing only whether the scratch word was
zero therefore fixed cold LOAD but could still misclassify warm LOAD and an
ordinary Runestone scan.

The corrected guard starts with persisted `0xA49C` in every case. It
dereferences the scheduler stack pointer at `0xFFFF8000` and substitutes
`0xA612` only when the outer continuation is exactly the stock result scanner
`0x00CEC4`. All six literal entries to the progression scanner are
scheduler-owned; the two inner resume sites retain that valid frame. The A2
scratch register used for this check is overwritten by stock code at
`0x014AE4` on the level path or `0x014B3A` on the class-chain path before its
first subsequent use. Thus natural Scenario 7/10/11 results still see the next
scenario, while cold LOAD, warm LOAD with a stale nonzero selector, ordinary
turns, and Runestone use always see the saved active scenario. Public
v1.3.1-v1.3.6 SRAM needs neither editing nor an emulator state.

## v1.3.5 Runestone class-chain repair

The v1.3.2 join-only Hawk Lord and Croco Lord additions reused Keith's and
Lester's stock Fighter transition records.  That was sufficient for a normal
join from Hawk Knight/Crocoknight, but a Runestone always restarts its owner
from Fighter.  Consequently v1.3.2 through v1.3.4 displayed the join-only
promotion row after a Runestone: Keith saw Magic Knight / Dragon Knight /
Bishop instead of Lord / Hawk Knight / Healer, and Lester had the analogous
wrong branch.

v1.3.5 keeps the stock Fighter rows intact and relocates each longer join-only
class chain and commander sprite map into reserved expansion space.  The join
behavior and v1.3.4 legacy-save recovery remain unchanged, while a Runestone
restart now follows the original Fighter choices.  The three focused paths
were exercised on isolated Xvfb/BlastEm displays:

| Commander start | First choices after repair |
| --- | --- |
| Keith / Fighter | Lord / Hawk Knight / Healer |
| Lester / Fighter | Knight / Crocoknight / Shaman |
| Jessica / Warlock | Healer / Sorcerer / Lord |

Keith's Hard-mode test also equipped and consumed a real Runestone before the
class-choice screen was inspected; this was not only a menu-table check.

## Mounted Lord display and combat repair

The first v1.3.5 build gave the new Hawk Lord and Croco Lord IDs the complete
Dragon Knight and Serpent Knight class records.  Their status stats, EXP gauge,
and custom map appearance therefore belonged to those later classes.  The
otherwise-unused generic combat entries for the new IDs still pointed at
Cleric and Vampire graphics, which made Keith's Hawk Lord attack as a Sister.

The repaired build makes each named Lord an alias of its intended mounted
branch: Hawk Lord uses Keith's Hawk Knight class data, stronger Hawk Lord map
design, and Keith-specific Hawk Knight combat animation; Croco Lord likewise
uses Lester's Crocoknight data, stronger Croco Lord map design, and
Lester-specific Crocoknight combat animation.  Generic fallback combat
descriptors are corrected as well.

The Runestone restart row now uses the same second-tier choices as the join
boundary.  Keith therefore sees `로드 / 호크로드 / 힐러`, Lester sees
`나이트 / 크로코로드 / 샤먼`, and Jessica retains
`힐러 / 소서러 / 로드`, regardless of whether the stone is consumed from a
second-, third-, fourth-, or fifth-tier class.

The repaired normal candidate (MD checksum `1E84`) was exercised on isolated
virtual display `:622`.  A real item `0x1A` was equipped before the stock
level-up handler for all twelve representative states: Keith
`호크로드/매직나이트/드래곤로드/드래곤마스터`, Lester
`크로코로드/서펜나이트/서펜로드/서펜마스터`, and Jessica
`소서러/비숍/아크메이지/자베라`.  Every run displayed the three expected
second-tier choices, consumed the item, and applied the first choice at
`LV1/EXP0`.  Separate fifth-tier runs navigated the unmodified live UI to the
second row and applied Keith's Hawk Lord (`0x2B`) and Lester's Croco Lord
(`0x2C`) at `LV1/EXP0`.
