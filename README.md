# wissels

Wisselschema voor JO9-wedstrijden (6 tegen 6, 4x10 minuten). Statische webapp (`index.html` + `schedule.js`) zonder backend: alle gegevens worden in de `localStorage` van de browser opgeslagen.

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

Omdat het een statische site is, kun je `index.html` en `schedule.js` ook op elke webserver of statische host zetten (nginx, Apache, GitHub Pages, Netlify, ...). Beide bestanden moeten in dezelfde map staan.

## Let op: gegevens

Teams en wedstrijden staan in de browser van de gebruiker, niet op de server. Een ander apparaat, een andere browser of het wissen van browsergegevens betekent een lege app. Een nieuwe deploy raakt de opgeslagen gegevens niet, zolang het domein (en de poort) gelijk blijft.

## Tests

```sh
node schedule.test.js
```

Print `ok` als alles slaagt.
