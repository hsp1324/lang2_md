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
