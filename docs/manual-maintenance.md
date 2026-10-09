# Manual maintenance and acceptance

`uitleg.html` is a standalone Dutch manual, linked above the app's first card. The app and manual share the approved green primary (`#006948`), pale lavender surface, system font, bordered white cards and local PupillenTrainer logo. There are no scripts in the manual, external fonts, external images or new runtime dependencies. Deploy the three HTML/JS files and the complete `assets/` directory together; the Dockerfile copies these explicitly.

## Local checks

From the checkout root:

```sh
node schedule.test.js
node --test manual.test.js
python3 -m http.server 8080 --bind 127.0.0.1
```

Open `http://localhost:8080/`, follow **Uitleg**, and return using **Terug naar Wisselschema**. Use a separate browser profile for example data. HTTP versus HTTPS, host and port define distinct browser storage origins; testing on this local origin does not load data from the production origin.

With a working Docker daemon:

```sh
docker compose up -d --build
# Open http://localhost:9091/ and test the manual and every image link.
# The committed docker-compose.override.yml overrides the published port to 9091.
docker compose down
```

Do not run the local HTTP server and Compose on the same port simultaneously. No production deployment is needed to test this branch.

## Screenshot contract

The seven committed PNGs are targeted captures of the actual app, populated through browser interactions in an isolated context with **only fictional data**: Voorbeeldteam JO9, Speler A through H, Voorbeeldclub, example match date 2026-10-17. Speler H is marked absent; different keepers are chosen for the four blocks. The schema image follows a real cell edit and paired repair; the field image follows selecting period 5 and a real pointer drag. Number badges, outlines and leaders are added to the captures, without replacing app content. The date input's displayed format is browser/locale-dependent.

For updates, use fixed desktop viewport 1100×1000 and Dutch browser locale. Seed the isolated browser context's `Math.random` (LCG, seed 42, multiplier 1664525, increment 1013904223, unsigned 32-bit state) so regenerated proposals are repeatable without changing production code. Two successive captures were verified byte-identical. Capture each target card, crop the match card before the schedule, and keep callouts outside text. Inspect every resulting image after regeneration. Do not use production browser storage, names or matches. Images open directly with a native link; browser Back returns to the manual. Each has Dutch alt text and a caption, while complete instructions remain text alongside the image so small-screen users need not read scaled screenshot text.

## Repeatable capture and visual verification

Use an external Python tooling environment with Playwright and Pillow, plus an existing full Chromium executable. These are maintenance dependencies only; do not add them to the runtime image. From the checkout root:

```sh
PYTHON=/path/to/tooling/bin/python
CHROMIUM=/path/to/chromium/chrome
EVIDENCE=/path/outside/the/checkout
BASELINE=/path/to/read-only/baseline-checkout
"$PYTHON" scripts/prepare-logo.py --chromium "$CHROMIUM" --evidence "$EVIDENCE/branding"
"$PYTHON" scripts/capture-manual.py --chromium "$CHROMIUM" --output "$EVIDENCE/capture-one"
"$PYTHON" scripts/capture-manual.py --chromium "$CHROMIUM" --output "$EVIDENCE/capture-two"
"$PYTHON" scripts/verify-design.py --chromium "$CHROMIUM" --baseline "$BASELINE" --output "$EVIDENCE/design"
node --test
```

Compare the two capture-results JSON files and all seven hashes before replacing `assets/manual/*.png`. Inspect every changed image, including full-resolution panels of tall pages. The capture script reuses the original fictional fixture and real cell edit/pointer drag. All three tools bind an ephemeral loopback port, intercept external requests, use isolated browser contexts and verify their temporary port is closed afterward.

`verify-design.py` inventories all static Dutch text and non-styling attributes against the baseline; its only approved addition is the decorative header logo. It verifies the production JavaScript byte-for-byte, hidden states, 320/375px phone and landscape layouts, local table scrolling/sticky names, enlarged text, field geometry, two bench rows, real pointer crossing, keeper protection, JSON download/restore, print output and all manual anchors/image links/keyboard navigation. Also run the existing `verify-match-persistence.py` and `verify-bench-rotation.py` with the same `--chromium` and evidence paths.

The authoritative logo remains `logo/logo.svg`. It contains two embedded PNGs, not a lightweight vector. `prepare-logo.py` rejects scripts, event handlers and external resources, then renders the full logo at 640×588 with transparency. The header uses `assets/branding/logo.webp`, lossless including transparent RGB (`exact=True`); decoded RGBA bytes must match the source render. The full shield and wordmark remain unchanged, without a matte, crop, distortion or recoloring. The existing Docker `assets/` copy includes it without changing Docker configuration.

## Acceptance checklist

- Run both Node suites; the manual tests cover top navigation, seven numbered sections, privacy warnings, local PNGs, image links and Docker COPY instructions.
- At desktop and 375px phone width, inspect all readable panels through the footer; check for no horizontal document overflow. Also check landscape width and enlarged text.
- Use actual Tab/Enter navigation to reach Uitleg, section anchors, image links and both back links; verify focus is visible.
- Open each image, return, and follow the back link to the app. Returning to the app preserves localStorage but does not promise to reopen the previously selected match.
- Monitor browser requests and page errors: all manual resources must stay on the local origin, with no external services or entered-data requests.
- Exercise app creation, presence, keeper selection, generation, a paired cell edit, a pointer drag, JSON download and restore on fictional data. Restore must replace current data only after the existing confirmation. Verify PDF output from the existing print document.
- Run `node --test` for the full suite, including restore cancellation and replacement coverage in `copy.test.js`.
- For copy-only updates, preserve scheduling logic, category numbers, selectors, storage keys and backup contracts. Compare JavaScript structure independently of user-facing string values; review every changed string separately. Regenerate screenshots when visible app text changes, and repeat captures to check determinism.

This repository has no configured GitHub Actions workflows at implementation time. Local tests are evidence, not a claim of CI success. Docker COPY coverage is a static contract; a real container build still requires an available daemon.
