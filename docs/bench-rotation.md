# Bench rotation generation

## Priority and compatibility

New proposals honor present selected keepers and fill the category's field capacity (or use every present player if there are too few). They minimize the total number of player/adjacent-period pairs spent on the bench in both periods. Among choices that can still reach that minimum, selection uses current minutes, historical bench starts for the opening period, historical minute deficit, and fewer switches. Randomness breaks remaining ties.

A period is `m.interval`, not a keeper block. No new stored fields or storage keys are needed. Opening, restoring or switching a prepared match does not regenerate its slots. Existing regeneration triggers remain unchanged. Manual cell edits and field/bench dragging remain permitted. Warnings derive from the current slots on every render, so they also work for old preparations and disappear after a repair. Print/PDF includes the same warning.

Fairness is a local priority among minimum-repeat schedules, not a promise of globally equal minutes. Forced keeper minutes and the bench constraint can restrict the available choices. The original fairness assertions in `schedule.test.js` remain unchanged.

## Keeper-aware minimum

Let `N` be present players and `F` the field capacity. When `N = 2F`, zero bench overlap requires adjacent field sets to be exact complements. Thus keepers must belong to the alternating field groups. The same keeper in two adjacent periods makes zero overlap impossible, even though `N <= 2F`. For six field places and twelve players with one fixed keeper, at least one player repeats on the bench at every boundary. Eight five-minute periods therefore have a minimum of seven occurrences. At ten-minute intervals, alternating keepers A/B/A/B can produce zero occurrences and twenty minutes for every player.

The generator uses a backward dynamic program over subsets of the distinct selected keepers. There are at most four distinct selected keepers in the keeper-enabled categories, so at most sixteen states per period. This is a category property, not a player or match cap.

All other players are interchangeable for future feasibility. If there are `G` such players and consecutive states put `a` and `b` of them on the field, their minimum bench overlap is `max(0, G - a - b)`. Add the actual overlap among selected-keeper identities benched in both states. This gives each transition's exact minimum. Any previous ordinary field set can realize it by bringing its bench players on first, choosing fairly within each group. Future costs depend on the counts, not those identities, so this realization can be repeated inductively. Backward costs consider every allowed keeper state through the final period; greedy failure is never classified as mathematical impossibility.

The dynamic program minimizes occurrences across the entire schedule, including unavoidable cases. It does not minimize the longest bench run separately or globally optimize minute variance after that objective.

## Automated evidence

Run from the checkout:

```sh
node --test
git diff --check
```

The full suite passes 19 tests. The baseline passed 10 before this change. Initial TDD runs failed all five new generator tests; warning tests then failed before UI implementation. Replaying the final regression tests against unchanged main fails all nine feature tests while the three original persistence tests pass.

`bench.test.js` includes an independent exhaustive field-subset oracle over 672 scenarios, including all 81 four-block keeper sequences drawn from two players and no keeper for the small squads, plus tight-capacity, parity-conflict and oversized cases. Additional coverage includes 80 keeper seed scenarios, 280 category/interval/history scenarios, 26 boundary scenarios across four/six/eight field places, and fixed-keeper squads up to 65 players. Every generated schedule is checked for capacity, membership, unique field entries and mandatory keepers.

In a separate 100-seed comparison per setup, the nine-player fixed-keeper half-block case retains exactly 25 minutes for every nonkeeper. Rotating keepers at half-block intervals retain a maximum five-minute spread, and full-block intervals retain a maximum ten-minute spread. Baseline bench-repeat ranges were respectively 6, 5 to 8 and 2 to 3; feature schedules have zero in all three setups. These sampled comparisons are evidence for those setups, not universal fairness bounds.

## Real browser verification

Use an existing Playwright environment and discover its installed Chromium path before running:

```sh
python scripts/verify-bench-rotation.py --output /path/outside/repo --chromium /path/to/chrome
python scripts/verify-match-persistence.py --output /another/path/outside/repo --chromium /path/to/chrome
```

Both scripts run the actual static app on an ephemeral loopback server with fictional records and isolated browser storage. The bench probe verifies nine-present/six-field rotating keepers, twelve-present fixed keeper with the exact minimum seven repeats, twelve-present alternating full-block keepers with zero repeats, paired manual swaps and warning repair, desktop/mobile/print, restore/reload of an old prepared schedule, explicit regeneration and other-record isolation. There are no page errors or external requests.

The unchanged persistence probe verifies five fully prepared matches, 25 creations, 100 named same-clock preparations, complete-record reload equality, one-record editing without changing the other 99, pending inputs and stale-tab rejection.

Four affected instructional images (`03` through `06`) were recaptured from the existing fictional manual fixture. Repeated captures were byte-identical and all changed images were visually inspected. The manual explains interval-level rotation, keeper/capacity limitations, manual warnings and preservation until regeneration.

Local evidence is stored outside the repository at `/opt/data/cache/scratch/bench-evidence/` and `/opt/data/cache/scratch/bench-persistence-evidence/`. The repository has no configured CI workflow; local tests are not CI success. No Docker deployment was performed. Independent review and Robert's branch testing remain before merge.
