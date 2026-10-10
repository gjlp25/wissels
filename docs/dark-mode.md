# Dark mode — release 2026.10.2

## Scope and behavior

- App, manual and privacy pages share a labelled native **Weergave** selector: Systeem / Licht / Donker. The default follows the OS, including live changes. Explicit choices override OS changes.
- `theme.js` runs in the head before rendering; `theme.css` provides the same system-dark fallback without JavaScript. The selector is hidden when JavaScript is unavailable rather than presenting a nonfunctional control.
- Only `pupillentrainer-theme` stores the appearance choice. Invalid values fall back to system. Other tabs synchronize theme-key changes and site-storage clears. Blocked reads and full/blocked writes are caught only inside theme handling; a failed write retains the choice for the current page.
- The existing inline app script and `schedule.js` are byte-identical to main. Team/match storage, JSON format, undo and pitch geometry are unchanged. Theme choices are not exported or restored with team backups.
- Dark-mode buttons retain dark green/blue fills behind white text; bright green is reserved for links, accents and boundaries. The original logo file is unchanged and has a light backing in dark mode.
- Print/PDF always uses light colors, including table states, keeper/legend and informational-page warnings. Existing print isolation and footer links are retained.
- `Dockerfile` and static-host instructions include both local theme assets. No runtime dependency, framework, build step or network integration was added.

## Verification

Write failing theme behavior tests before implementation (`theme.test.js`), then run:

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

Verified locally in Chromium with fictional records:

- Node: 95 passing tests, including 10 theme tests.
- Theme: nine acceptance groups; complete records and persisted undo survive appearance changes, navigation, reload and actual JSON download/restore. Theme-only SecurityError/QuotaExceededError injections leave ordinary match storage working. A MutationObserver confirms initial dark selection while the document is still loading.
- Existing suites: 12 matchday, seven blocker, seven category and 16 footer/privacy browser checks pass; no unexpected external requests or page errors.
- Both themes at 320, 375, 844 landscape and 1280 pixels; 200% text on all three pages without document overflow. Native selector label, keyboard focus, invalid preference, cross-tab updates, disabled JavaScript and light print/PDF checked.
- Existing light computed colors, borders and pitch/token dimensions match the unchanged baseline inline CSS.
- Contrast uses real computed colors with alpha backgrounds composed through ancestors, including normal/hover buttons, warnings, table states, sticky names, keeper cells, fairness, legends, tokens, inputs/placeholders and match mode. Sampled normal-text contrast is at least 5.00:1; sampled input/select boundaries and theme focus are at least 3.128:1. These focused checks are not a whole-app accessibility certification. Native disabled controls are excluded from the normal-text threshold.
- Actual app desktop/phone light and dark screenshots, manual/privacy dark screenshots and PDFs are emitted beside the JSON report. Evidence is review-only, outside production assets. Existing manual screenshots remain light illustrations.

## Limitations and review hold

- Tested browser engine: Chromium; no Safari/Firefox runtime claim.
- Existing circular tokens can clip portions of multiword player names at phone size. Light/dark computed geometry is identical; that inherited layout behavior was not redesigned in this feature.
- Docker CLI is installed, but its daemon is unavailable. COPY coverage passes static tests; no container build was claimed.
- The privacy page remains a pre-publication draft. Planned Vercel hosting, TransIP registration, STRATO mailbox and unresolved legal/mail-retention facts are unchanged.
- Feature PR only: independent parent review remains required. No merge or deployment performed.
