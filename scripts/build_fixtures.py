"""Builds reference/ and fixtures/ from the surveyed snapshot under discovery/official-funding-map/.

    python3 scripts/build_fixtures.py

The five pairings shown by 'Pairings end to end' are the site's test fixtures and its demo seed: their
transcripts, the money snapshot (retrieved 2026-10-30), the donors' statements and the reviews (quote bounds,
speaker credit, readings) that a person made for them. Nothing here is analysis; it reshapes files already in
the repository into the JSON the Node site reads. Standard library only.
"""

import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "discovery", "official-funding-map")
sys.path.insert(0, os.path.join(ROOT, "discovery", "funder-first-pairings"))

import ff_lib  # noqa: E402
import fmap_lib as fl  # noqa: E402

EXTRA_COMMITTEES = {
    "Daniel Lurie": [{
        "filer_nid": "212391140",
        "filer_name": "Our Future, Our SF Opposing Lurie & Farrell for Mayor 2024",
        "filer_type": "Primarily Formed Candidate", "status": "TERMINATED", "match": "weak",
    }],
}
USED_FAMILIES = ["sf-chamber", "sf-poa", "govern-for-california", "seiu-1021"]
MEASURES = {
    "CHAMBER-H": (["Muni"], "H"), "POA-I-TIMING": (["budget", "deficit"], "I"), "POA-I-WONG": (["budget", "deficit"], "I"),
    "POA-I-C": (["inclusionary"], "I C"), "GFC-J": (["transfer tax"], "J"),
    "SEIU-D": (["charter reform"], "D"), "SEIU-E": (["charter reform"], "E"), "SEIU-F": (["charter reform"], "F"),
    "SEIU-STANDS": ([], ""),
}


def load(*parts):
    with open(os.path.join(SRC, *parts), encoding="utf-8") as f:
        return json.load(f)


def dump(obj, *parts):
    path = os.path.join(ROOT, *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=False, ensure_ascii=False)
        f.write("\n")


def roster():
    seed = load("data", "committees_seed.json")
    out = []
    for o in seed["officials"]:
        exact, garbled = ff_lib.VARIANTS[o["name"]]
        committees = [{k: c[k] for k in ("filer_nid", "filer_name", "filer_type", "status")}
                      for c in o["committees"] + EXTRA_COMMITTEES.get(o["name"], [])]
        out.append({"name": o["name"], "office": o["office"], "district": o["district"], "surname": o["surname"],
                    "given": o["name"].split()[0], "exact": exact, "garbled": garbled, "committees": committees})
    return out


def snapshot(families):
    s = load("data", "money_snapshot.json")
    committees = []
    for c in s["committees"]:
        committees.append({"official": c["official"], "office": c["office"], "district": c["district"],
                           "surname": c["surname"], "given": c["given"], "filerNid": c["filer_nid"],
                           "filerName": c["filer_name"], "filerType": c["filer_type"], "status": c["status"],
                           "relation": c["relation"]})
    keep = ("filer_nid", "form_type", "filing_id_number", "filing_date", "filing_version", "calculated_date",
            "calculated_amount", "committee_id", "fn", "ln", "entity_code")
    rows = {}
    for key in USED_FAMILIES:
        rows[key] = [{k: r[k] for k in keep if k in r} for r in s["family_rows"][key]
                     if fl.family_of(families, fl.donor_name(r), r.get("committee_id"))[0] == key]
    ids = sorted({r.get("committee_id") for rs in rows.values() for r in rs if r.get("committee_id")})
    lookup = {i: s["filers_lookup"][i] for i in ids if i in s["filers_lookup"]}
    ikeep = ("filer_nid", "filer_name", "filing_id_number", "candidate_last_name", "support_oppose_code",
             "office_description", "district_number", "amt", "d0", "d1")
    independent = [{k: r[k] for k in ikeep if k in r} for r in s["independent"]]
    return {"retrieved": s["retrieved"], "dataLoadedAt": s["data_loaded_at"], "datasetUrl": s["dataset"],
            "committees": committees, "familyRows": rows, "filersLookup": lookup, "independent": independent}


def priorities():
    wanted = {pid for p in load("picks.json")["pairings"] for pid in p["priority_ids"]}
    out = []
    for s in load("data", "priorities.json")["statements"]:
        if s["id"] in wanted:
            phrases, measures = MEASURES[s["id"]]
            out.append({"id": s["id"], "family": s["family"], "section": s["section"], "text": s["text"],
                        "url": s["url"], "kind": s["kind"], "pageDate": s["page_date"], "retrieved": s["retrieved"],
                        "phrases": phrases, "measures": measures.split()})
    return out


def reviews():
    out = []
    for p in load("picks.json")["pairings"]:
        q = p["quote"]
        out.append({
            "id": p["id"], "slug": p["slug"], "official": p["official"], "family": p["family"],
            "subject": p["subject"], "meetingId": str(p["meeting_id"]),
            "quote": {"from": q["start"], "to": q["end"], "beginAt": q.get("begin_at", ""), "endAt": q.get("end_at", "")},
            "speaker": {"cueStamps": p["speaker"]["cue_stamps"], "support": p["speaker"]["text_support"],
                        "doubt": p["speaker"]["doubt"], "doubtReason": p["speaker"]["doubt_reason"],
                        "outside": p["speaker"]["outside"]},
            "priorityIds": p["priority_ids"], "highlight": p["highlight"], "overlap": p["overlap"],
            "stance": p["stance"], "moneyNote": p["money_note"]})
    return out


def main():
    families = load("data", "families.json")["families"]
    dump({"families": families}, "reference", "families.json")
    dump({"officials": roster()}, "reference", "roster.json")
    dump(snapshot(families), "fixtures", "money.json")
    dump(priorities(), "fixtures", "priorities.json")
    dump(reviews(), "fixtures", "reviews.json")
    meetings = [m for m in load("data", "meetings.json") if m["id"] in (52849, 52853)]
    dump([{"id": str(m["id"]), "body": m["body"], "date": m["date"], "url": m["url"], "retrieved": m["retrieved"],
           "rows": m["rows"]} for m in meetings], "fixtures", "meetings.json")
    for m in meetings:
        shutil.copy(os.path.join(SRC, "data", "transcripts", "%d.tsv" % m["id"]),
                    os.path.join(ROOT, "fixtures", "transcripts", "%d.tsv" % m["id"]))
    print("reference and fixtures written")


if __name__ == "__main__":
    main()
