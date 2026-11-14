#!/usr/bin/env python3
"""Build a self-contained HTML dashboard of ALC's non-Schengen flights for one day.
Usage: dashboard.py [YYYY-MM-DD]   (default: latest data/*.json) -> dashboards/YYYY-MM-DD.html"""
import json, os, sys, glob, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect import LABELS, ROOT

# Schengen members as of 2025 (BG and RO fully since 2025-01-01, HR since 2023).
SCHENGEN = set("AT BE BG CH CZ DE DK EE ES FI FR GR HR HU IS IT LI LT LU LV MT NL NO PL PT RO SE SI SK".split())
COUNTRY_NAMES = {"GB": "United Kingdom", "IE": "Ireland", "DZ": "Algeria", "MA": "Morocco", "AM": "Armenia",
  "IL": "Israel", "TR": "Turkey", "CY": "Cyprus", "RS": "Serbia", "UA": "Ukraine", "GE": "Georgia", "AL": "Albania",
  "JE": "Jersey", "GG": "Guernsey", "IM": "Isle of Man", "GI": "Gibraltar", "TN": "Tunisia", "EG": "Egypt",
  "SN": "Senegal", "US": "United States", "MD": "Moldova", "BA": "Bosnia and Herzegovina", "ME": "Montenegro",
  "MK": "North Macedonia", "XK": "Kosovo", "AZ": "Azerbaijan"}
# IATA -> ISO country. Airports missing here are listed as "unclassified" on the dashboard; add them.
AIRPORTS = {
  # United Kingdom / Crown dependencies
  **dict.fromkeys("ABZ BFS BHD BHX BOH BRS CWL DSA EDI EMA EXT GLA HUY INV LBA LCY LGW LHR LPL LTN MAN MME NCL NQY NWI PIK SEN SOU STN".split(), "GB"),
  "JER": "JE", "GCI": "GG", "IOM": "IM", "GIB": "GI",
  **dict.fromkeys("DUB ORK SNN NOC KIR".split(), "IE"),
  **dict.fromkeys("ALG ORN TLM CZL BJA".split(), "DZ"),
  **dict.fromkeys("RAK TTU CMN TNG FEZ NDR OUD AGA RBA".split(), "MA"),
  "EVN": "AM", "TLV": "IL", "IST": "TR", "SAW": "TR", "LCA": "CY", "PFO": "CY", "BEG": "RS", "TBS": "GE",
  "KUT": "GE", "TIA": "AL", "TUN": "TN", "KIV": "MD", "GYD": "AZ", "JFK": "US", "EWR": "US",
  # Schengen
  **dict.fromkeys("MAD BCN IBZ PMI SVQ TFN TFS LPA AGP BIO SCQ VGO OVD MAH ACE FUE VLC SDR XRY GRX LEI VIT".split(), "ES"),
  **dict.fromkeys("AMS EIN RTM".split(), "NL"), **dict.fromkeys("BRU CRL ANR OST".split(), "BE"),
  **dict.fromkeys("ARN GOT VXO NYO MMX".split(), "SE"), **dict.fromkeys("OSL TRF BGO SVG TRD TOS HAU AES".split(), "NO"),
  **dict.fromkeys("BER BRE CGN FRA NRN DUS HAM MUC STR HHN FMM PAD FKB SCN HAJ NUE".split(), "DE"),
  **dict.fromkeys("BGY MXP CTA FCO BLQ NAP VCE PSA TSF".split(), "IT"),
  **dict.fromkeys("ORY CDG MRS TLS BVA NTE LYS NCE BOD LIL".split(), "FR"),
  **dict.fromkeys("LIS OPO FAO".split(), "PT"), **dict.fromkeys("GVA ZRH BSL".split(), "CH"),
  **dict.fromkeys("KTW WAW WMI KRK GDN POZ WRO BZG RZE".split(), "PL"), **dict.fromkeys("OTP CLJ IAS TSR".split(), "RO"),
  "BTS": "SK", "BUD": "HU", "CPH": "DK", "BLL": "DK", "HEL": "FI", "SZG": "AT", "VIE": "AT", "PRG": "CZ", "PED": "CZ", "RMO": "MD",
  "LUX": "LU", "KEF": "IS", "RIX": "LV", "VNO": "LT", "KUN": "LT", "TLL": "EE", "MLA": "MT", "SOF": "BG",
  "ZAG": "HR", "LJU": "SI", "ATH": "GR",
}

def minutes(date_ddmmyyyy, hhmmss):
    d = datetime.datetime.strptime(f"{date_ddmmyyyy} {hhmmss[:5]}", "%d/%m/%Y %H:%M")
    return (d - datetime.datetime(2000, 1, 1)) // datetime.timedelta(minutes=1)

def build(path):
    db = json.load(open(path))
    day = datetime.date.fromisoformat(db["date"]).strftime("%d/%m/%Y")
    rows, unknown = [], {}
    for f in db["flights"].values():
        cc = AIRPORTS.get(f["other_airport"])
        if cc is None:
            unknown[f["other_airport"]] = f["other_city"]; continue
        if cc in SCHENGEN: continue
        delay = None
        if f["estimated"] and f["estimated_date"]:
            delay = minutes(f["estimated_date"], f["estimated"]) - minutes(day, f["scheduled"])
        rows.append({"type": f["type"], "flight": f["flight"], "airline": f["airline"], "airport": f["other_airport"],
          "city": (f["other_city"] or "").strip(), "country": cc, "country_name": COUNTRY_NAMES.get(cc, cc),
          "scheduled": f["scheduled"][:5], "estimated": (f["estimated"] or "")[:5],
          "next_day": bool(f["estimated_date"] and f["estimated_date"] != day), "delay": delay,
          "status": f["status_code"] or "", "label": LABELS.get(f["status_code"] or "", "unknown code"),
          "gate": f["gate"], "belt": f["belt"], "hall": f["raw"].get("salaPrimera"), "updated": f["collected_at"]})
    rows.sort(key=lambda r: (r["scheduled"], r["flight"]))
    return {"date": db["date"], "runs": [r["at"] for r in db["runs"]], "failed_runs": sum(1 for r in db["runs"] if r["err"]),
            "total_all": len(db["flights"]), "unknown": unknown, "flights": rows}

def main():
    paths = sorted(glob.glob(os.path.join(ROOT, "data", "*.json")))
    path = os.path.join(ROOT, "data", sys.argv[1] + ".json") if len(sys.argv) > 1 else paths[-1]
    data = build(path)
    out_dir = os.path.join(ROOT, "dashboards"); os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, data["date"] + ".html")
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    open(out, "w").write(open(os.path.join(ROOT, "scripts", "dashboard_template.html")).read().replace("__DATA__", blob))
    print(out, f'{len(data["flights"])} non-Schengen of {data["total_all"]}', "unclassified:", data["unknown"] or "none")

if __name__ == "__main__": main()
