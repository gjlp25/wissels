# Onderzoek: voorbereide wedstrijden bewaren

Onderzocht op `main` (`1affda307686e9201c94f445b89d74e050d2bcb4`) in lokale Chromium-sessies met fictieve gegevens. Roberts gebruikte URL en browser zijn niet bekend; dit is geen diagnose van zijn draaiende versie.

## Wat al werkte

Vijf wedstrijden met verschillende datums en tegenstanders bleven afzonderlijk bewaard, inclusief aanwezigheid, keepers, interval, handmatig aangepaste schema's en versleepte posities. Wisselen en herladen veranderden de opgeslagen records niet. Een wijziging in één wedstrijd liet de andere vier ongemoeid. Ook 25 wedstrijden bleven na herladen bewaard.

De app had en heeft geen vast maximum aantal wedstrijden. Browseropslag is wel eindig. De bestaande lijst past bij 25 wedstrijden binnen een scherm van 375 pixels breed; knoppen lopen door op volgende regels.

Na herladen is geen wedstrijd geselecteerd. De opgeslagen wedstrijden staan nog in de lijst. Wedstrijden met dezelfde datum zonder tegenstander hebben dezelfde zichtbare knoptekst. Dat kan verwarrend zijn, maar de normale test toonde daarbij geen verlies van records. Deze PR verandert die weergave niet.

## Aangetoonde fouten en gerichte oplossingen

1. **Tegenstander nog in invoer:** typen en onmiddellijk herladen, zonder het veld te verlaten, verloor de nieuwe tekst. De app bewaarde dit veld pas bij `change`. Datum en tegenstander worden nu ook bij `input` opgeslagen, zonder de invoer opnieuw te tekenen. Het datumveld committeerde in de onderzochte Chromium al tijdens invullen; de extra handler bewaakt beide invoervelden.
2. **Gelijke klokticks:** 100 aanroepen van de echte aanmaak-handler met een vaste `Date.now()` leverden 100 records met één gedeeld ID op. Selecteren/bewerken zoekt het eerste record met dat ID, waardoor het verkeerde record wordt aangepast. Nieuwe IDs krijgen alleen bij een botsing een vrije suffix. Bestaande IDs worden niet gewijzigd.
3. **Verouderd tweede tabblad:** open twee tabbladen, bereid een wedstrijd voor in het eerste, maak vervolgens een wedstrijd in het tweede. Het tweede schreef zijn oude volledige database terug en verwijderde de voorbereiding uit de opslag. Vóór opslaan controleert de app nu of de opgeslagen snapshot nog overeenkomt. Bij een conflict blijft de nieuwste opslag intact, verschijnt een waarschuwing en herlaadt het tabblad. De geweigerde laatste wijziging moet opnieuw worden gedaan.

De tabbladcontrole is een bescherming tegen een reeds verouderde snapshot, geen synchronisatie- of transactiesysteem. Exact gelijktijdige schrijfacties tussen de controle en `setItem` zijn niet atomair vergrendeld. Gebruik één actief bewerkingstabblad. Er is geen backend toegevoegd, geen migratie of verwijdering van records, en de sleutel `wissels-jo9` en het JSON-formaat blijven hetzelfde. Eventuele al aanwezige dubbele IDs worden niet automatisch gerepareerd.

## Verificatie

- Iedere fout had een falende Node-regressietest vóór de bijbehorende oplossing.
- `node --test` voert de volledige bestaande en nieuwe tests uit.
- `matches.test.js` controleert 100 afzonderlijk benoemde voorbereidingen bij dezelfde kloktick, herladen, één record wijzigen zonder de andere 99 te wijzigen, invoer zonder blur en verouderde tabbladopslag.
- `scripts/verify-match-persistence.py` gebruikt de echte app met geïsoleerde browseropslag, vijf volledige voorbereidingen, 25 normale aanmaakacties, 100 aanmaakacties bij gelijke klokticks, invoer/herladen en twee tabbladen. Het controleert opgeslagen JSON naast de zichtbare invoer en maakt screenshots. De tijdelijke lokale server sluit aan het eind.

Benodigd voor de optionele browsercontrole: Python met `playwright` en een bestaande Chromium-installatie. Voorbeeld vanuit de repository:

```sh
python scripts/verify-match-persistence.py \
  --chromium /pad/naar/chromium \
  --output /pad/buiten/de/repository/bewijs
```

Met `--root /pad/naar/ongewijzigde/main --baseline` bevestigt dezelfde controle de fouten op de oude versie. Er is geen CI-workflow toegevoegd, geen merge uitgevoerd en niets gedeployd. Statistieken en eerlijkheidsberekeningen vallen buiten deze wijziging.
