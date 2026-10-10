# Light/dark buttons — release 2026.10.3

## Scope and behavior

- App, manual and privacy pages share exactly two native icon buttons in the **Weergave** group: a sun for **Licht** and a crescent for **Donker**. Inline local 24px SVGs use consistent strokes and are decorative; Dutch accessible labels and titles name the buttons, and `aria-pressed` exposes selection.
- Both buttons are 44px square with keyboard Tab/Enter/Space support, visible focus and an inset selected border in addition to background color. The chooser is not a dropdown and has no System mode.
- `theme.js` runs in the head before rendering. Without a valid stored choice the default is light. OS preference is never consulted or followed; without JavaScript all pages stay light and hide the disabled, ineffective buttons.
- Only `pupillentrainer-theme` stores appearance. Valid `light`/`dark` values are retained; absent, removed, invalid and legacy `system` values resolve to light without writing on load or migrating other records. Real localStorage events synchronize tabs, including clear; unrelated keys and sessionStorage are ignored. Blocked reads and full/blocked writes are caught only inside theme handling; a failed write retains the choice for the current page.
- The existing inline app script, inline app CSS, `schedule.js` and logo assets are unchanged. Team/match storage, JSON format, undo and pitch geometry are unchanged. Appearance is neither exported nor restored with team backups.
- Existing screen palettes are retained. Theme icons use foreground tokens against their actual card/selected backgrounds; ordinary app action buttons retain dark fills behind white text.
- Print/PDF always uses light colors and hides appearance controls on every page, including table states, keeper/legend and informational-page warnings.
- Existing Docker COPY lines deliver both theme assets. No dependency, framework, remote script, remote asset or build step was added.

## Verification

Theme regression tests were run red before the implementation changes, then green with the full suite. Run with external Playwright/Chromium tooling (not an app dependency):

```sh
node --test
/path/to/external/python scripts/verify-theme.py \
  --chromium /path/to/chromium --output /path/to/evidence/theme
/path/to/external/python scripts/verify-matchday.py \
  --chromium /path/to/chromium --output /path/to/evidence/matchday
/path/to/external/python scripts/verify-matchday-blockers.py \
  --chromium /path/to/chromium --output /path/to/evidence/blockers
/path/to/external/python scripts/verify-category-timing.py \
  --chromium /path/to/chromium --output /path/to/evidence/category
/path/to/external/python scripts/verify-footer-privacy.py \
  --chromium /path/to/chromium --output /path/to/evidence/footer
```

Verified locally with fictional records:

- Node: 98 passing tests, including 13 theme tests.
- Theme: nine acceptance groups; complete records and persisted undo survive theme changes, navigation, reload and real JSON download/restore. Theme-only SecurityError/QuotaExceededError injections leave normal match storage working. A MutationObserver confirms light selection while the document is still loading, despite a dark OS preference.
- Existing browser suites: 12 matchday, seven blocker, seven category and 16 footer/privacy checks pass. No unexpected external requests or page errors.
- Both themes at 320px, 375px, 844px landscape and 1280px; 200% text on all three pages without document overflow. Two actual button clicks, sequential Tab/Enter/Space, pressed state, invalid and legacy values, real cross-tab synchronization/removal/clear, sessionStorage exclusion, no-JavaScript light behavior and light print/PDF checked.
- Existing light computed colors, borders and pitch/token dimensions exactly match the unchanged inline CSS baseline.
- Contrast uses computed colors with alpha backgrounds composed through ancestors. 5,776 text samples have a minimum ratio of 5.00:1; sampled control borders/focus have a minimum of 3.128:1. Semantic SVG icons are measured against actual button backgrounds, with a minimum of 10.531:1 (required 3:1). These focused checks are not a whole-app accessibility certification; disabled native controls are excluded from the normal-text threshold.
- Desktop/phone screenshots in both themes, full-page captures, three print PDFs and JSON reports are emitted outside the repository for review. The eight shipped manual screenshots crop sections that do not contain the header chooser, so none needs recapturing.

## Limitations and review hold

- Tested browser engine: Chromium; no Safari/Firefox runtime claim.
- Existing circular field tokens can clip portions of multiword names on phones. The inherited geometry is unchanged, not redesigned here.
- Docker CLI is installed but its daemon is unavailable. Static COPY coverage passes; no image build is claimed.
- Privacy remains a pre-publication draft. Provider policy, planned hosting, domain registration, mailbox and unresolved legal/mail-retention facts are unchanged.
- Feature PR only: independent parent review remains required. No merge or deployment performed.
