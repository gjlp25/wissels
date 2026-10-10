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

Robert confirmed that `robert@wicaro.nl` is a STRATO mailbox, `pupillentrainer.nl` is registered with TransIP, and he intends to host the app on Vercel ("Nee ik ga hem op vercel draaien"). Vercel is the intended website host; TransIP is the registrar. This does not establish a live Vercel deployment or a connected custom domain. Robert remains the confirmed maker/contact, not an independently verified formal controller.

Vercel's Privacy Notice identifies hosted-site traffic data such as end-user IP addresses and system configuration information.[1] This is separate from application records in browser localStorage. The notice describes Vercel's own practices and excludes processing as a customer's processor under its DPA.[1] The DPA describes processing arrangements under the customer agreement; reading it does not verify Robert's applicable contract or account configuration.[2] No exact log period, processing region or automatic plan-specific DPA coverage is asserted.

Before publishing a complete live privacy declaration:

1. Verify the actual live address, controller identity and deployed configuration, including any additional proxy, cookies or analytics. Match the notice to the applicable hosting agreement and technical-data practices; do not ask Robert to identify Vercel again or guess the vendor's internal retention.
2. Robert still needs to establish feedback-mail access and actual deletion practice; document the applicable basis and provider arrangements separately. A simple **recommendation, not an adopted policy**, is to delete identifying feedback after resolution, with a maximum of three months after resolution, and keep useful bug notes only after anonymization. Any genuinely necessary exception needs its own reason and review date. The public page's existing case-resolution criterion remains explicitly proposed, without claiming a new retention policy.

The page remains visibly labelled as a draft. Keep this PR unmerged and undeployed pending the requested review and factual completion. This is a scoped factual update, not a full legal compliance review.

## Sources

[1] https://vercel.com/legal/privacy-notice
[2] https://vercel.com/legal/dpa

Retrieved directly over HTTPS on 10 October 2026. The Privacy Notice's hosted-site traffic and applicability sections support the distinction above; the DPA is a reference for contractual verification, not evidence of the project's actual agreement.

Authoritative AP guidance retrieved on 10 October 2026 (initial old URLs could not be extracted; current search results supplied these paths):

- [Right to information](https://www.autoriteitpersoonsgegevens.nl/themas/basis-avg/privacyrechten-avg/recht-op-informatie), including controller/contact, purposes/basis, recipients, transfers, retention and rights.
- [Cookies](https://www.autoriteitpersoonsgegevens.nl/themas/internet-slimme-apparaten/cookies). No consent UI was added solely for appearance; no new tracking was introduced.
- [Tip or complaint](https://autoriteitpersoonsgegevens.nl/een-tip-of-klacht-indienen-bij-de-ap).

## Verification

Vercel-intent follow-up: `node --test` rerun with 85 passing tests. The focused real Chromium probe passed seven groups: rendered Vercel intent (not a verified live deployment/domain connection), STRATO/TransIP facts, sourced technical-traffic explanation and explicit remaining mail-policy gaps; privacy layout at 320/375/844/1280px and enlarged text; and complete fictional records through app/privacy/manual/return navigation. It recorded zero informational-page storage writes, page errors or external requests; no email was sent. Evidence: `/opt/data/cache/scratch/wissels-footer-vercel-report.json`. All three footers, release version, application/manual files, schedule.js, footer.css, privacy styles and Dockerfile remain byte-identical to prior head `4287d8c406f882d7c78c25679d0866f84991cee6`. Broader suites and screenshots below are initial implementation evidence, not rerun for this prose-only update.

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
