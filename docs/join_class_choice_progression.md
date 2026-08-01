# Keith, Lester, and Jessica join-class choice

The development builder changes the three pre-initialized commander records at
`0x05E64A` so the characters first become available at their tier-1 class and
stored LV10.  The stock LV10 progression gate then opens the ordinary tier-2
class-choice screen; no Runestone-only recovery path is required.

| Commander | Stock start | New start | Tier-2 choices |
| --- | --- | --- | --- |
| Keith | Hawk Knight LV1, EXP5 | Fighter LV10, EXP5 | Lord / Hawk Knight / Healer |
| Lester | Crocoknight LV7, EXP15 | Fighter LV10, EXP15 | Knight / Crocoknight / Shaman |
| Jessica | Sorcerer LV5, EXP0 | Warlock LV10, EXP0 | Healer / Sorcerer / Lord |

The patch retains each commander's original MP, residual EXP, AT, DF, identity
sprite, and equipment identity fields.  Promoted-class ability and mercenary
bits are replaced with the proper tier-1 values before the choice, preventing
unselected tier-2 benefits from leaking into the tier-1 record.

The source-locked LV10 gate at `0x014848` branches to the stock class-choice
path.  The normal selection handler writes the chosen class at `0x014C36` and
resets the level to 1 at `0x014C3A`.

Runtime evidence on the current development ROM reached Keith's real Scenario
7 activation path and displayed Lord / Hawk Knight / Healer.  Selecting Hawk
Knight wrote runtime class `0x06` and returned safely to the map.  The Lester
and Jessica tier-1 candidate sets are also covered by the existing current
class-change UI probes and by source-chain regression tests.

This initial-roster patch applies automatically to new games.  An SRAM whose
manual slot was created by an older ROM already contains copied commander
records, so updating only the ROM does not rewrite those saved records.  Such a
save needs an explicit one-time migration if the player wants the new choice
for a commander who has not yet joined.  Do not migrate an already-joined and
progressed commander without the player's approval, because that would replace
their selected class/level state.
