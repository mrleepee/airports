# ALC flight collector
`scripts/collect.py` pulls Aena's flight feed for Alicante (ALC) arrivals and departures (the JSON endpoint behind https://www.aena.es/en/flight-info.html), keeps today's (Europe/Madrid) flights, and merges them into `data/YYYY-MM-DD.json` (key: type|number|airline|scheduled|other airport; latest observation wins, `first_seen` kept). `--report` writes `reports/YYYY-MM-DD.md`.

Aena sometimes lists the same flight twice in one response (seen 2026-11-08: 215 departures, one copy with status `SCH`, one with blank status). Within a run the copy carrying a status is kept as the record; every other raw copy is stored in `duplicate_raw`.

Limitations: Aena's feed only lists flights from roughly the last hour onward, so flights earlier than the first run of a day are missed. First run on 2026-11-01 was at 18:01 CET, so that day's data is incomplete before ~16:35. Raw status codes are stored; labels in reports are inferred.
