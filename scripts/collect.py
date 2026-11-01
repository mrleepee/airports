#!/usr/bin/env python3
"""Collect ALC arrivals/departures from Aena, merge into data/YYYY-MM-DD.json.
Usage: collect.py [--report]   (--report also writes reports/YYYY-MM-DD.md)"""
import json, os, sys, urllib.request, datetime, zoneinfo
URL = "https://www.aena.es/sites/Satellite?pagename=AENA_ConsultarVuelos&airport=ALC&flightType={}"
TZ = zoneinfo.ZoneInfo("Europe/Madrid")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Aena status codes: raw code is always preserved; meanings below are inferred from
# Aena's Spanish codes and are only a convenience label.
LABELS = {"": "No status yet", "SCH": "Scheduled", "FLY": "In flight", "LAN": "Landed", "BOR": "Boarding (raw BOR)",
 "INI": "Check-in/boarding started (raw INI)", "IBK": "Baggage belt open (raw IBK)", "RET": "Delayed (raw RET)",
 "HOR": "Schedule changed (raw HOR)", "ULL": "Final call (raw ULL)", "EMB": "Boarding (raw EMB)",
 "CER": "Gate closed (raw CER)", "CAN": "Cancelled", "DIV": "Diverted", "DEP": "Departed"}
def fetch(t):
    r = urllib.request.Request(URL.format(t), headers={"User-Agent": "Mozilla/5.0"})
    return json.load(urllib.request.urlopen(r, timeout=90))
def main():
    now = datetime.datetime.now(TZ); today = now.strftime("%d/%m/%Y"); iso = now.strftime("%Y-%m-%d")
    path = os.path.join(ROOT, "data", iso + ".json")
    db = json.load(open(path)) if os.path.exists(path) else {"date": iso, "flights": {}, "runs": []}
    run = {"at": now.isoformat(timespec="seconds"), "ok": {}, "err": {}}
    for t, kind in (("L", "arrival"), ("S", "departure")):
        try:
            rows = fetch(t); n = 0
            for x in rows:
                if x["fecha"] != today: continue
                n += 1
                key = f'{kind}|{x["numVuelo"]}|{x["compania"]}|{x["horaProgramada"]}|{x["iataOtro"]}'
                rec = {"date": iso, "type": kind, "flight": f'{x["iataCompania"]}{x["numVuelo"]}',
                  "airline": x.get("nombreCompania"), "other_airport": x.get("iataOtro"), "other_city": x.get("ciudadIataOtro"),
                  "scheduled": x["horaProgramada"], "estimated_date": x.get("fechaEstimada"), "estimated": x.get("horaEstimada"),
                  "status_code": x.get("estado"), "terminal": x.get("terminal"), "aircraft": x.get("tipoAeronave"),
                  "gate": x.get("puertaPrimera"), "belt": x.get("cintaPrimera"), "raw": {k: v for k, v in x.items() if not k.startswith("urlLogo")},
                  "source": URL.format(t), "collected_at": run["at"]}
                old = db["flights"].get(key)
                rec["first_seen"] = old["first_seen"] if old else run["at"]
                db["flights"][key] = rec
            run["ok"][kind] = n
        except Exception as e:
            run["err"][kind] = repr(e)
    db["runs"].append(run)
    json.dump(db, open(path, "w"), indent=1, ensure_ascii=False, sort_keys=True)
    print(json.dumps(run))
    if "--report" in sys.argv: report(db, iso)
def report(db, iso):
    F = list(db["flights"].values())
    def tab(kind):
        rows = sorted((f for f in F if f["type"] == kind), key=lambda f: f["scheduled"])
        o = [f"| Flight | Airline | {'Origin' if kind=='arrival' else 'Destination'} | Scheduled | Estimated/Actual | Status |", "|---|---|---|---|---|---|"]
        for f in rows:
            o.append(f'| {f["flight"]} | {f["airline"]} | {f["other_city"]} ({f["other_airport"]}) | {f["scheduled"][:5]} | {(f["estimated"] or "")[:5]} | {f["status_code"] or "-"} ({LABELS.get(f["status_code"],"unknown code")}) |')
        return rows, "\n".join(o)
    A, at = tab("arrival"); D, dt = tab("departure")
    delayed = [f for f in F if f["estimated"] and f["estimated"][:5] > f["scheduled"][:5] and
               (int(f["estimated"][:2])*60+int(f["estimated"][3:5]) - int(f["scheduled"][:2])*60-int(f["scheduled"][3:5])) >= 15]
    canc = [f for f in F if f["status_code"] in ("CAN",)]
    abn = [f for f in F if f["status_code"] in ("CAN", "DIV", "RET", "HOR")]
    last = db["runs"][-1]["at"]; fails = [r for r in db["runs"] if r["err"]]
    md = f"""# ALC daily report {iso}
## Daily Summary
- Date: {iso}
- Arrivals collected: {len(A)}
- Departures collected: {len(D)}
- Cancellations: {len(canc)}
- Delayed (estimate >= 15 min after schedule): {len(delayed)}
- Collection runs: {len(db['runs'])} (first {db['runs'][0]['at']}, last {last}); failed runs: {len(fails)}
## Arrivals
{at}
## Departures
{dt}
## Exceptions
""" + ("\n".join(f'- {f["type"]} {f["flight"]} sched {f["scheduled"][:5]} est {(f["estimated"] or "")[:5]} status {f["status_code"]}' for f in {id(f): f for f in delayed+abn}.values()) or "- none") + """
## Data completeness
Not confirmed complete unless stated by the reporter; see README for limitations.
"""
    open(os.path.join(ROOT, "reports", iso + ".md"), "w").write(md)
main()
