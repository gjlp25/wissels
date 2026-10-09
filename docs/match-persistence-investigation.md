# Investigation: preserving prepared matches

Investigated on `main` (`1affda307686e9201c94f445b89d74e050d2bcb4`) in local Chromium sessions with fictional data. Robert's deployed URL and browser are unknown; this is not a diagnosis of his running version.

## What already worked

Five matches with different dates and opponents remained independently stored, including attendance, keepers, intervals, manually edited schedules and dragged positions. Switching matches and reloading left the stored records unchanged. Editing one match left the other four untouched. A further check retained 25 matches after reloading.

The app had and still has no fixed match-count limit. Browser storage is finite, however. The existing list fits within a 375-pixel-wide viewport with 25 matches; buttons wrap onto additional lines.

No match is selected after reloading. The saved matches are still listed. Matches with the same date and no opponent have identical visible button labels. That can be confusing, but the normal test showed no record loss. This PR leaves that display behavior unchanged.

## Reproduced defects and targeted fixes

1. **Opponent input still focused:** typing and immediately reloading without leaving the field lost the new text. The app saved this field only on `change`. Date and opponent now also save on `input`, without redrawing the inputs. In the tested Chromium version, filling the date field already committed its value; the additional handler covers both fields.
2. **Identical clock ticks:** 100 calls to the actual creation handler with a fixed `Date.now()` produced 100 records sharing one ID. Selection and editing find the first record with that ID, so the wrong record is changed. New IDs receive an unused suffix only when a collision occurs. Existing IDs are not changed.
3. **Stale second tab:** opening two tabs, preparing a match in the first and then creating a match in the second caused the second tab to write its old full database back, removing the preparation from storage. Before saving, the app now checks whether the stored snapshot still matches. On conflict, it leaves the latest storage intact, shows a warning and reloads the tab. The rejected last edit must be repeated.

The tab check guards against an already stale snapshot; it is not a synchronization or transaction system. Exactly concurrent writes between the check and `setItem` are not protected by an atomic lock. Use one active editing tab. No backend, migration or record deletion was added, and the `wissels-jo9` key and JSON format remain unchanged. Existing duplicate IDs are not automatically repaired.

## Verification

- Each defect had a failing Node regression test before its corresponding fix.
- `node --test` runs the full existing and new test suite.
- `matches.test.js` checks 100 separately named preparations within the same clock tick, reloading, editing one record without changing the other 99, input without blur and stale-tab storage.
- `scripts/verify-match-persistence.py` exercises the actual app with isolated browser storage: five complete preparations, 25 normal creations, 100 same-clock creations, input/reload and two tabs. It checks stored JSON as well as visible inputs and captures screenshots. The temporary local server shuts down at the end.

The optional browser check requires Python with `playwright` and an existing Chromium installation. Example from the repository:

```sh
python scripts/verify-match-persistence.py \
  --chromium /pad/naar/chromium \
  --output /pad/buiten/de/repository/bewijs
```

With `--root /pad/naar/ongewijzigde/main --baseline`, the same check confirms the defects on the old version. No CI workflow was added, this PR has not been merged and nothing has been deployed. Statistics and fairness calculations are outside this change.
