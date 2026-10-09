# wissels

Wisselschema voor pupillenvoetbal volgens de KNVB-wedstrijdvormen 2026/'27: JO7 (4 tegen 4), JO8–JO10 (6 tegen 6) en JO11/MO11/JO12 (8 tegen 8). Kies per team de categorie; speeltijd, aantal spelers en keeperblokken volgen daaruit. Statische webapp (`index.html` + `schedule.js`) zonder backend: alle gegevens worden in de `localStorage` van de browser opgeslagen.

## Lokaal openen

Open `index.html` direct in de browser. Er is geen build-stap nodig.

## Deployen met Docker Compose

Vereist: Docker met de Compose-plugin.

```sh
git clone https://github.com/gjlp25/wissels.git
cd wissels
docker compose up -d --build
```

De app draait daarna op <http://localhost:8080> (nginx, herstart automatisch via `restart: unless-stopped`). Een andere poort kies je in `docker-compose.yml` (`"8080:80"` → `"<poort>:80"`).

Updaten na een wijziging:

```sh
git pull
docker compose up -d --build
```

Stoppen:

```sh
docker compose down
```

## Deployen met alleen Docker

```sh
docker build -t wissels .
docker run -d --name wissels -p 8080:80 --restart unless-stopped wissels
```

## Deployen zonder Docker

Omdat het een statische site is, kun je `index.html`, `schedule.js`, `uitleg.html` en de volledige map `assets/` ook op elke webserver of statische host zetten (nginx, Apache, GitHub Pages, Netlify, ...). Houd de mapstructuur intact.

## Let op: gegevens

Teams en wedstrijden staan in de browser van de gebruiker, niet op de server. Een ander apparaat, een andere browser of het wissen van browsergegevens betekent een lege app. Een nieuwe deploy raakt de opgeslagen gegevens niet, zolang het domein (en de poort) gelijk blijft.

Gebruik onderaan de app **Back-up downloaden** om alles als JSON-bestand op te slaan, en **Back-up terugzetten** om het (op een ander apparaat of adres) terug te zetten. Terugzetten vervangt de huidige gegevens in die browser.

## Tests

```sh
node --test
```

Runs the full generator, persistence, matchday, import and static-delivery suites. See `docs/matchday-improvements.md` for acceptance/compatibility decisions and `scripts/verify-matchday.py` for real-browser verification (external Playwright tooling required).
