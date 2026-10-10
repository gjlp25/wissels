# Footer and privacy release

## Scope

Release `2026.10.1` is the first explicitly labelled October 2026 release, adding privacy information and feedback navigation. The version is static in all three public footers, with a release description in its title attribute. Update all three together; `footer.test.js` enforces parity. No build tool or runtime script is needed.

The compact footer links to Robert Postma's supplied LinkedIn path, `uitleg.html`, `privacy.html` and `mailto:robert@wicaro.nl`. All pages share `footer.css`. The existing manual return links remain, and print hides the footer. No external embedding, preconnect, tracking, consent banner, form or backend was added.

## Source audit

Audited against main `1fa5fad8285ec89da65d0185e2cf6ea75d344a90`:

- Production HTML loads local `schedule.js` and local branding/manual assets. No fetch/XHR/beacon, app cookies, analytics or remote resources are present. The unused `design/` prototypes load Google Fonts but are not included by Docker and are not public production dependencies.
- `index.html` uses only the `wissels-jo9` localStorage key for application records: teams (IDs, names, categories, players), selected team, matches (IDs, dates, opponents, status, attendance, intervals, keepers, slots, actual period keepers, positions, manual state and last undo), and last requested backup time/played-match count. Import preserves compatible additional fields, so a JSON backup may include more than the known schema.
- JSON download serializes the full database locally. Restore validates then replaces current records after confirmation. PDF uses browser printing and contains player/match information; there is no upload or remote renderer.
- Local records are not encrypted by the app, do not sync, and are isolated by browser profile/device/origin. Same-browser access exposes them. Browser site-data removal is the existing way to clear all records; no destructive reset control was added. Exports need separate deletion.
- Both the inline application script and `schedule.js` are byte-for-byte identical to the baseline. SHA-256: inline script `fa98a4c8fadbdb552fa2a06c68ed966cfeb3b6cfc2a2185459a54372741b88b1`; `schedule.js` `42e7a1b5c4f531421479b8c343e02d9276fba394f86de854ddd49f8e9eda7316`.
- Docker uses `nginx:alpine`, explicit HTML/JS COPY and assets COPY. This release adds an explicit COPY for privacy HTML and footer CSS. Compose is a possible deployment route, not evidence of actual live hosting. Base port is 8080; committed override uses 9091.

## Publication facts still needed

Read-only GitHub discovery returned no homepage, deployments, Actions workflows, rulesets or open PRs. Pages lookup returned 404 and main protection lookup returned “Branch not protected”. These results do not establish who operates a separate live deployment. No platform configuration was changed.

Robert confirmed that the mailbox `robert@wicaro.nl` is provided by STRATO and the domain `pupillentrainer.nl` is registered with TransIP. These are owner-supplied facts; domain registration does not establish website hosting. Runtime HTTPS/DNS discovery failed name resolution and the external web fetch timed out, so neither attempt established the live host or that the domain is absent. No provider-specific processing locations, transfers or retention claims were added.

Before publishing a complete live privacy declaration, Robert must confirm:

1. The actual live address, hosting operator/controller, hosting/proxy services, actual logs/cookies/analytics, purpose and lawful basis, access/recipients, retention/deletion criteria and processing locations/transfers.
2. The feedback-mail recipients/access, applicable lawful basis, actual retention/deletion practice and relevant processing locations/transfers. The mailbox provider is now confirmed as STRATO. The page labels a case-resolution retention criterion as a proposal, not an established practice. No fixed period or processing region is invented.

The page visibly labels these gaps and distinguishes verified application behavior from incomplete live-hosting/mail information. Keep this PR unmerged and undeployed for independent review and resolution of publication facts. It does not claim blanket GDPR compliance.

Authoritative AP guidance retrieved on 10 October 2026 (initial old URLs could not be extracted; current search results supplied these paths):

- [Right to information](https://www.autoriteitpersoonsgegevens.nl/themas/basis-avg/privacyrechten-avg/recht-op-informatie), including controller/contact, purposes/basis, recipients, transfers, retention and rights.
- [Cookies](https://www.autoriteitpersoonsgegevens.nl/themas/internet-slimme-apparaten/cookies). No consent UI was added solely for appearance; no new tracking was introduced.
- [Tip or complaint](https://autoriteitpersoonsgegevens.nl/een-tip-of-klacht-indienen-bij-de-ap).

## Verification

Provider-facts follow-up: `node --test` rerun with 85 passing tests. A focused Chromium probe verified rendered STRATO/TransIP facts, explicit hosting/basis/retention gaps, privacy layout at 320/375/844/1280px and enlarged text, zero informational-page storage writes, complete fictional records through app/privacy/manual/return navigation, zero page errors and zero external requests. No email was sent. Application/manual scripts, styles and release versions remain unchanged from approved head `68da715a3c5b915099b55d364d8ac96bbaa11234`. Existing screenshot and broader regression evidence below is from the initial footer implementation; no redundant full recapture was performed for this prose-only follow-up.

- `node --test`: 85 tests passed, zero failed. Added focused footer/privacy/package contracts; updated old blanket external-URL assertions to forbid external resources while allowing ordinary approved links.
- `scripts/verify-footer-privacy.py`: 16 acceptance groups across all three pages at 320x740, 375x812, 844x390 and 1280x900. Real app/privacy/manual/return navigation preserves complete fictional stored JSON; informational pages make zero localStorage writes. Exact mailto and LinkedIn targets, sequential footer Tab order, focus outline, wrapping, no document overflow, enlarged text and print hiding pass. No pre-click external requests; deliberate LinkedIn navigation is intercepted and blocked. No email sent.
- `scripts/verify-matchday.py`: 12 acceptance groups passed, including complete records, reload, mode, pointer undo, actual keeper correction, statistics, backup/download/restore and phone navigation. No page errors or external requests.
- `scripts/verify-matchday-blockers.py`: 7 cases passed, including inherited IDs, quota failures, pending input, storage read failures, stale downloads, legacy keeper tails and pointer undo.
- Eight desktop/mobile footer/privacy screenshots were inspected locally. All use the real static app with fictional records; no private browser session or production data.
- Dockerfile/static delivery assertions pass. A real Docker build could not run because no Docker daemon is available; this is not claimed as a container-build pass.

Reproduce browser checks using external Playwright Python and an existing Chromium executable:

```sh
/path/to/playwright/python scripts/verify-footer-privacy.py --output /path/to/evidence/footer --chromium /path/to/chrome
/path/to/playwright/python scripts/verify-matchday.py --output /path/to/evidence/matchday --chromium /path/to/chrome
/path/to/playwright/python scripts/verify-matchday-blockers.py --output /path/to/evidence/blockers --chromium /path/to/chrome
```

No merge or deployment is authorized by this handoff.
