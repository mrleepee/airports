# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-script collector that snapshots Alicante (ALC) arrivals and departures from Aena's public flight feed into one JSON file per day. No dependencies beyond the Python 3.9+ standard library (`zoneinfo`), no build, no tests, no linter config.

## Commands

```bash
python3 scripts/collect.py            # fetch both feeds, merge into data/<today>.json
python3 scripts/collect.py --report   # also write reports/<today>.md
python3 scripts/dashboard.py          # non-Schengen HTML dashboard for the latest day -> dashboards/<date>.html
python3 scripts/dashboard.py 2026-11-01
```

Each run prints its run record (`{"at", "ok", "err"}`) as JSON. `--report` writes into `reports/`, which is not in the repo and is not created by the script: create it first or the run fails after the data has already been saved.

Data updates are committed one per run (e.g. `Update ALC data 18:20`).

## How the collector works (`scripts/collect.py`)

- **Source**: `https://www.aena.es/sites/Satellite?pagename=AENA_ConsultarVuelos&airport=ALC&flightType={L|S}` (L = arrivals, S = departures), the JSON endpoint behind aena.es flight-info. It needs a browser-like `User-Agent`. Field names are Spanish (`numVuelo`, `horaProgramada`, `estado`, `iataOtro`, `cintaPrimera`, …), and missing values often come back as the string `"null"` instead of JSON null.
- **Day boundary**: "today" is Europe/Madrid. Rows whose `fecha` (DD/MM/YYYY) isn't today are dropped, so a run just after midnight starts a new file.
- **Merge key**: `type|numVuelo|compania|horaProgramada|iataOtro`. Each run overwrites the record for a key (latest observation wins) and keeps the original `first_seen`. Flights that drop out of the feed are never removed. If you change the key format, existing data files won't match up any more.
- **Per-day file shape**: `{"date", "flights": {key: record}, "runs": [run, ...]}`. Each record has normalized fields plus `raw` (the full Aena row minus `urlLogo*`), `source`, and `collected_at`. A fetch failure for one direction goes into `run.err` and does not stop the other direction or the save. Output is written with `sort_keys=True, indent=1, ensure_ascii=False` to keep git diffs stable.
- **Status codes**: always stored as raw `estado`. The `LABELS` map is a guess at Aena's Spanish codes and is used only for report display; don't treat the labels as authoritative.
- **Report**: "delayed" means estimated ≥ 15 min after scheduled, computed from HH:MM only. It ignores `estimated_date`, so delays that cross midnight are missed. "Exceptions" are delayed flights plus `CAN`/`DIV`/`RET`/`HOR` statuses.

## Non-Schengen dashboard (`scripts/dashboard.py`)

Imports `LABELS`/`ROOT` from `collect.py`, which is why `collect.py` guards `main()` with `__name__`. Classification goes airport → country through the hand-maintained `AIRPORTS` IATA map, checked against `SCHENGEN` (BG/RO count as Schengen since 2025; CH/NO/IS/LI are Schengen; UK/IE are not). Airports missing from `AIRPORTS` are not guessed: they're excluded and listed on the page and in stdout as "unclassified", so add new destinations to the map when that appears. The rendered page is `scripts/dashboard_template.html` with the filtered rows injected at `__DATA__`; all charts, filters and the table are client-side vanilla JS and the file has no external assets. Delay is computed with `estimated_date`, so it handles midnight. The status shown is the last one observed: flights drop out of the feed, so departed flights often stay at `BOR`.

## Data limitations (from README)

The feed only lists flights from about an hour ago onward, so flights earlier than a day's first run are never captured. 2026-11-01's first run was at 18:01 CET, so that day is incomplete before ~16:35. Don't call a day complete unless runs covered it.
