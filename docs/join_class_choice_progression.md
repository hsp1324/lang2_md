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

The patch retains residual EXP and identity/equipment fields.  MP, AT, and DF
are back-calculated so replaying the original branch's ordinary level growth
reproduces the Japanese joining stats.  Promoted-class ability and mercenary
bits are replaced with the proper tier-1 values before the choice, preventing
unselected tier-2 benefits from leaking into the tier-1 record.

The source-locked LV10 gate at `0x014848` branches to the stock class-choice
path.  The normal selection handler writes the chosen class at `0x014C36` and
resets the level to 1 at `0x014C3A`.

## v1.3.1 to v1.3.3 regression

The released v1.3.1 BPS stored Keith and Lester as Fighter LV10 and retained
their Fighter class-change records.  This is why an existing save displayed
Fighter LV10 and opened class choice correctly when the commander joined.

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

Runtime and structural evidence for the v1.3.4 recovery is recorded by the
focused join-class tests and the isolated Scenario 11 BlastEm run.

The initial-roster patch applies automatically to new games.  v1.3.4 also
repairs the specific v1.3.0/v1.3.1 Fighter LV10 and v1.3.2/v1.3.3 Fighter
LV11+ save states at runtime; the user's `.srm` does not need to be edited by
an external migration tool.  A commander who already selected a non-Fighter
class is never rewritten.

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
