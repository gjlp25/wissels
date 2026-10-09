# Dutch copy review

This editorial pass covers all shipped app and manual text. The Humanizer workflow and pattern catalog were applied to the complete text before selecting edits: mark, draft, check factual meaning, then write the final version. Short labels that already work remain unchanged.

## Inventory coverage

| Surface | Review scope |
| --- | --- |
| `index.html`, static HTML | Page title, navigation, section headings, buttons, placeholders, category titles, instructions and backup guidance: 25 text nodes and 6 text attributes. |
| `index.html`, inline script | All 271 string literals and template segments were inventoried, including selectors and markup that must stay unchanged. User-facing content includes empty states, migration team name, player deletion title, category/keeper guidance, table headings, legends, first substitutes, statistics, category conversion, deletion and restore confirmations, invalid-backup alert and the generated print/PDF document. |
| `schedule.js` | All seven category display labels; category identifiers, player counts, durations, keeper settings and scheduling logic are unchanged. |
| `uitleg.html` | The entire manual: title, navigation, introduction, warnings, seven numbered sections, seven captions, seven image descriptions and return links. The final page has 134 text nodes and 8 text attributes. |
| Manual screenshots | All seven regenerated from the actual app with the existing fictional fixture. Five changed: `01-team.png`, `03-wedstrijd.png`, `04-schema.png`, `05-opstelling.png`, `07-backup.png`. Player and totals captures remain byte-identical to main. |

Key button and table terms remain consistent across app, manual and screenshots, including Team aanmaken, Toevoegen, Nieuwe wedstrijd, Nieuw wisselvoorstel, Printen / PDF, Op veld, Eerste wissels, Gem., Keeper min, Back-up downloaden and Back-up terugzetten. README commands and deployment instructions are outside this app-copy pass and remain untouched. Maintenance documentation and test code stay English.

## Meaning and behavior preserved

- Category labels retain every supported game format and duration; no rules were changed or independently revalidated.
- Changing attendance, keeper, interval or converted match category still regenerates proposals and can overwrite manual edits. Manual instructions retain that warning.
- Field movement alone does not change playing time. Field-to-bench movement changes the schedule, and keeper cells are selected through keeper controls rather than table clicks.
- Team data stays in browser-local `localStorage`, isolated by device, browser and origin (protocol, domain and port). There is no account or automatic synchronization, and entered app records are not uploaded to the app server.
- Shared-browser access, unencrypted storage, clearing browser data and private-window storage loss remain explicit. Ordinary hosting access logs are distinguished from entered app data.
- JSON backups contain team/player/match data; PDF exports may contain names and match details. Safe storage, limited access and careful sharing remain required. PDF is not a restorable backup.
- Restore replaces all current teams and matches in this browser rather than merging them. The confirmation now states that scope directly, still shows backup counts, and cancellation leaves current data intact.

## Verification

- The full `node --test` run passes: 7 tests, 0 failures, including the existing scheduling suite. The clearer restore-scope test was observed failing against main before the copy edit. Accepted restore and cancellation exercise the real inline script in Node's VM.
- JavaScript AST comparison after masking string values confirms identical program structure in the inline app script and `schedule.js`. Every changed string was reviewed separately; no identifiers, numeric settings, storage contracts, event handlers or selectors changed. Both pages' CSS is byte-identical to main.
- Real Chromium interactions verify creation, presence/keeper selection, generation, paired cell editing, period selection, pointer drag, JSON download/restore, print output, keyboard navigation, all seven image links and return navigation.
- App and manual have no document overflow at 1100x1000, 375x812 and 812x375. Manual text also fits at doubled text size. Desktop/mobile panels and the regenerated product images were inspected; small manual images deliberately open at full size.
- All seven product captures are byte-identical across repeated runs with the seeded fictional fixture. No external requests or page errors occurred in the network-monitored acceptance run. The unconfigured favicon produces an existing local 404 in capture runs.
- Temporary local servers are stopped after acceptance. There are no new runtime dependencies, workflow changes, Docker deployment or merge. GitHub has no Actions workflows; local evidence is not a CI claim.
