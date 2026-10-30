"""Builds the funding map and the pairings from data/ (no network).

    python build_map.py        # reads data/*.json, writes funding-map.md, funding-map.json, pairings.md, pairings.json

Money is kept in separate buckets and never added across them: gifts (Schedule A) per committee, 24-hour
reports not yet on a periodic report, and outside spending (form 496) naming the official.
Exits 1 when a pairing's quote is not word for word in the transcript or a statement is missing.
"""

import collections
import json
import os
import sys

import fmap_lib as fl

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
ORG = ("COM", "OTH", "SCC", "PTY")
CAUSAL = ("because of the money", "in return", "bought", "paid for", "influence", "caused", "quid pro quo",
          "in exchange for", "payback", "pay-to-play", "pay to play")
NO_CAUSATION = ("Two things shown side by side for a reader to check. Nothing here says why anyone said "
                "or gave anything, and the order of the dates is not an explanation.")


def jload(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def load_all():
    snap, fams = jload("money_snapshot.json"), jload("families.json")["families"]
    # a family's rows are those that family_of gives to that family (precedence and exclusions applied)
    for key, rows in snap["family_rows"].items():
        snap["family_rows"][key] = [r for r in rows if fl.family_of(fams, fl.donor_name(r), r.get("committee_id"))[0] == key]
    for c in snap["committees"]:
        c["relation"], c["relation_words"] = fl.relation_of(c)
    return {"snap": snap, "fams": fams,
            "prio": {s["id"]: s for s in jload("priorities.json")["statements"]},
            "picks": json.load(open(os.path.join(HERE, "picks.json"), encoding="utf-8")),
            "meetings": {m["id"]: m for m in jload("meetings.json")},
            "sample": jload("donor_sample.json")}


def key_a(filer, date, amt):
    return (filer, (date or "")[:10], round(float(amt or 0), 2))


def committee_stats(snap):
    """Per committee: Schedule A rows and total, unitemized total, 24-hour-only rows and total."""
    st = {c["filer_nid"]: {"a_n": 0, "a_sum": 0.0, "d0": "", "d1": "", "last_filing": "", "unitemized": 0.0,
                           "h24_only_n": 0, "h24_only_sum": 0.0, "h24_repeat_n": 0} for c in snap["committees"]}
    for r in snap["a_summary"]:
        s = st[r["filer_nid"]]
        s.update(a_n=int(r["n"]), a_sum=float(r["amt"]), d0=fl.day(r["d0"]), d1=fl.day(r["d1"]),
                 last_filing=fl.day(r["last_filing"]))
    for r in snap["unitemized"]:
        st[r["filer_nid"]]["unitemized"] = float(r["amt"])
    a_keys = {key_a(r["filer_nid"], r["calculated_date"], r["calculated_amount"]) for r in snap["a_for_match"]}
    for r in snap["f497"]:
        s = st[r["filer_nid"]]
        if key_a(r["filer_nid"], r["calculated_date"], r["calculated_amount"]) in a_keys:
            s["h24_repeat_n"] += 1
        else:
            s["h24_only_n"] += 1
            s["h24_only_sum"] += float(r["calculated_amount"])
    return st


def f497_only_rows(snap):
    a_keys = {key_a(r["filer_nid"], r["calculated_date"], r["calculated_amount"]) for r in snap["a_for_match"]}
    return [r for r in snap["f497"]
            if key_a(r["filer_nid"], r["calculated_date"], r["calculated_amount"]) not in a_keys]


def by_official(snap):
    out = collections.OrderedDict()
    for c in snap["committees"]:
        out.setdefault(c["official"], []).append(c)
    return out


def recognise(fams, snap, name, cid):
    """Family key and how (id or name), the registered record the FPPC id resolves to, and the sponsor stated."""
    key, how = fl.family_of(fams, name, cid)
    rec = snap["filers_lookup"].get(cid or "", [])
    return {"family": key, "how": how, "record": rec[0]["filer_name"] if rec else "",
            "sponsor": fl.sponsor_of(name) or ""}


def aggregate_donors(data):
    """{official: {group: {donor key: row}}}, group being 'controlled' (own and measure committees) or
    'third-party' (committees formed to support or oppose). Amounts are Schedule A, per donor, never added
    across the two groups."""
    snap, fams = data["snap"], data["fams"]
    cm = {c["filer_nid"]: c for c in snap["committees"]}
    out = collections.defaultdict(lambda: collections.defaultdict(dict))
    for r in snap["donors_org"] + snap["donors_ind"]:
        c = cm[r["filer_nid"]]
        grp = "controlled" if fl.own_and_measure(c["relation"]) else "third-party"
        name = fl.donor_name(r)
        rec = recognise(fams, snap, name, r.get("committee_id"))
        k = rec["family"] or (fl.norm_name(name), r.get("committee_id") or "")
        d = out[c["official"]][grp].setdefault(k, {
            "name": name, "names": set(), "entity": r["entity_code"], "family": rec["family"], "how": rec["how"],
            "record": rec["record"], "sponsor": rec["sponsor"], "committee_id": r.get("committee_id") or "",
            "amount": 0.0, "n": 0, "by_committee": collections.defaultdict(float)})
        d["names"].add(name)
        d["amount"] += float(r["amt"])
        d["n"] += int(r["n"])
        d["by_committee"][c["filer_name"]] += float(r["amt"])
    return out


def entity_table(snap):
    """{relation: {'ind': $, 'org': $, 'by_code': {code: $}}} over Schedule A of all tied committees."""
    cm = {c["filer_nid"]: c for c in snap["committees"]}
    t = collections.defaultdict(lambda: {"ind": 0.0, "org": 0.0, "by_code": collections.defaultdict(float)})
    for r in snap["by_entity"]:
        rel = cm[r["filer_nid"]]["relation"]
        a = float(r["amt"])
        t[rel]["by_code"][r["entity_code"]] += a
        t[rel]["ind" if r["entity_code"] == "IND" else "org"] += a
    return t


def independent_for(data):
    """Form 496 rows naming an official, as [{official, payer, payer_nid, family, stance, amount, filings,...}].
    A bare-surname row is kept only when its district is blank or the official's (or the office is Mayor)."""
    snap, fams = data["snap"], data["fams"]
    roster = {}
    for c in snap["committees"]:
        roster[c["official"]] = c
    agg = {}
    for r in snap["independent"]:
        for off, c in roster.items():
            if not fl.names_official(r["candidate_last_name"], c["surname"], c["given"]):
                continue
            dist = (r.get("district_number") or "").strip()
            if dist and c["district"] and dist != c["district"]:
                continue
            if c["office"] == "Mayor" and "SUPERVISOR" in (r.get("office_description") or "").upper():
                continue
            if c["office"] != "Mayor" and "MAYOR" in (r.get("office_description") or "").upper():
                continue
            k = (off, r["filer_nid"], r["support_oppose_code"])
            fam, how = fl.family_of(fams, r["filer_name"])
            a = agg.setdefault(k, {"official": off, "payer": r["filer_name"], "payer_nid": r["filer_nid"],
                                   "family": fam, "stance": r["support_oppose_code"], "amount": 0.0,
                                   "filings": set(), "d0": "9999", "d1": ""})
            a["amount"] += float(r["amt"])
            a["filings"].add(r["filing_id_number"])
            a["d0"] = min(a["d0"], fl.day(r["d0"]))
            a["d1"] = max(a["d1"], fl.day(r["d1"]))
    rows = []
    for a in agg.values():
        a["filings"] = len(a["filings"])
        rows.append(a)
    return sorted(rows, key=lambda x: -x["amount"])


def family_routes(data, indep):
    """{family: {route: $}}: Schedule A by the relation of the receiving committee, and form 496 spending
    by committees the family's names take, naming any of the twelve officials. Routes are never added."""
    snap = data["snap"]
    cm = {c["filer_nid"]: c for c in snap["committees"]}
    t = collections.defaultdict(lambda: collections.defaultdict(float))
    for fam, rows in snap["family_rows"].items():
        for r in rows:
            if r["form_type"] == "A":
                t[fam][cm[r["filer_nid"]]["relation"]] += float(r["calculated_amount"])
    for r in indep:
        if r["family"]:
            t[r["family"]]["outside spending (form 496)"] += r["amount"]
    return t


def individuals_check(data, agg):
    """Individuals among the listed donors that the donor-priorities survey also assessed (by last name and
    the start of the first name), with the survey's class."""
    out = []
    people = []
    for p in data["sample"]["individuals"]:
        nm = p["donor"].split(" (")[0]
        for part in nm.replace(" and ", "|").split("|"):
            toks = part.split()
            if len(toks) >= 2:
                people.append((toks[0].upper(), toks[-1].upper(), p))
    for off, groups in agg.items():
        for grp, donors in groups.items():
            for d in donors.values():
                if d["entity"] != "IND" and not d["family"]:
                    pass
                nm = fl.norm_name(d["name"]).split()
                if len(nm) < 2:
                    continue
                for first, last, p in people:
                    if nm[-1] == last and nm[0][:4] == first[:4]:
                        out.append({"official": off, "group": grp, "name": d["name"], "amount": d["amount"],
                                    "class": p["class"], "source": p.get("own_source"), "survey_name": p["donor"],
                                    "by_committee": dict(d["by_committee"])})
    return out


def pairing_money(data, official, family, indep):
    """The family's money beside an official, by committee: Schedule A rows (the headline, per committee),
    24-hour rows that repeat a Schedule A row (listed, not counted) and 24-hour rows with no Schedule A row
    yet (listed apart, own total), and form 496 spending by the family's committees naming the official."""
    snap = data["snap"]
    mine = {c["filer_nid"]: c for c in snap["committees"] if c["official"] == official}
    rows = [r for r in snap["family_rows"][family] if r["filer_nid"] in mine]
    a_rows = [r for r in rows if r["form_type"] == "A"]
    a_keys = {key_a(r["filer_nid"], r["calculated_date"], r["calculated_amount"]) for r in a_rows}
    per = collections.OrderedDict()
    for nid, c in mine.items():
        mine_rows = [r for r in rows if r["filer_nid"] == nid]
        if not mine_rows:
            continue
        a = [r for r in mine_rows if r["form_type"] == "A"]
        h = [r for r in mine_rows if r["form_type"] == "F497P1"]
        rep = [r for r in h if key_a(nid, r["calculated_date"], r["calculated_amount"]) in a_keys]
        only = [r for r in h if r not in rep]
        per[nid] = {"committee": c, "a": a, "a_sum": sum(float(r["calculated_amount"]) for r in a),
                    "repeat": rep, "only": only, "only_sum": sum(float(r["calculated_amount"]) for r in only)}
    outside = [x for x in indep if x["official"] == official and x["family"] == family]
    return {"per": per, "outside": outside}


def vnum(r):
    v = r.get("filing_version")
    try:
        return str(int(float(v)))
    except (TypeError, ValueError):
        return str(v or "")


def build_pairings(data, indep):
    picks = data["picks"]["pairings"]
    snap = data["snap"]
    out = []
    for pk in picks:
        meeting = data["meetings"][pk["meeting_id"]]
        rows = fl.load_rows(DATA, pk["meeting_id"])
        q = fl.extract_quote(rows, pk["quote"]["start"], pk["quote"]["end"], pk["quote"].get("begin_at"),
                             pk["quote"].get("end_at"))
        if not fl.is_verbatim(rows, q["text"]):
            raise ValueError("pairing %s: quote is not verbatim" % pk["id"])
        c0 = next(c for c in snap["committees"] if c["official"] == pk["official"])
        stm = []
        for sid in pk["priority_ids"]:
            if sid not in data["prio"]:
                raise ValueError("pairing %s: statement %s missing" % (pk["id"], sid))
            stm.append(data["prio"][sid])
        fam = next(f for f in data["fams"] if f["key"] == pk["family"])
        money = pairing_money(data, pk["official"], pk["family"], indep)
        if not money["per"]:
            raise ValueError("pairing %s: no money found" % pk["id"])
        out.append({"pk": pk, "meeting": meeting, "quote": q, "cues": fl.cue_rows(rows, pk["speaker"]["cue_stamps"]),
                    "official": c0, "statements": stm, "family": fam, "money": money})
    return out


def money_md(p, snap):
    pk, m = p["pk"], p["money"]
    L = []
    names = sorted({fl.donor_name(r) for c in m["per"].values() for r in c["a"] + c["repeat"] + c["only"]})
    ids = sorted({r.get("committee_id") or "none" for c in m["per"].values() for r in c["a"] + c["repeat"] + c["only"]})
    L.append("Money read from the Ethics Commission's Transactions dataset on DataSF (%s), data loaded through %s, "
             "retrieved %s. Contributor names as filed: %s. FPPC ids carried by those rows: %s."
             % (fl.DATASET_PAGE, snap["data_loaded_at"], snap["retrieved"], "; ".join(names), ", ".join(ids)))
    resolved = [snap["filers_lookup"][i][0]["filer_name"] for i in ids if i in snap["filers_lookup"]]
    if resolved:
        L.append("How the committee is recognised as the organisation's: the id resolves in the Filers dataset to "
                 "'%s'." % "'; '".join(resolved))
    else:
        L.append("How the giver is recognised as the organisation's: by the name as filed alone (the FPPC ids "
                 "above do not resolve in the Filers dataset, which holds only committees registered with the "
                 "San Francisco Ethics Commission).")
    L.append("")
    L.append(pk["money_note"])
    L.append("")
    for nid, c in m["per"].items():
        cm = c["committee"]
        L.append("**%s** (filer %s; %s; status %s)" % (cm["filer_name"], nid, cm["relation_words"], cm["status"]))
        L.append("")
        L.append("| Kind | Contribution date | Filing id (version) | Filing date | Amount | Giver as filed |")
        L.append("|---|---|---|---|---|---|")
        for r in c["a"]:
            L.append("| Schedule A | %s | %s (v%s) | %s | %s | %s |" % (
                fl.day(r["calculated_date"]), r["filing_id_number"], vnum(r), fl.day(r["filing_date"]),
                fl.dollars(r["calculated_amount"]), fl.donor_name(r)))
        for r in c["only"]:
            L.append("| 24-hour report, no Schedule A row yet | %s | %s (v%s) | %s | %s | %s |" % (
                fl.day(r["calculated_date"]), r["filing_id_number"], vnum(r), fl.day(r["filing_date"]),
                fl.dollars(r["calculated_amount"]), fl.donor_name(r)))
        for r in c["repeat"]:
            L.append("| 24-hour report repeating a Schedule A row (not counted) | %s | %s (v%s) | %s | %s | %s |" % (
                fl.day(r["calculated_date"]), r["filing_id_number"], vnum(r), fl.day(r["filing_date"]),
                fl.dollars(r["calculated_amount"]), fl.donor_name(r)))
        L.append("")
        tail = "Schedule A total for this committee: **%s** in %d rows." % (fl.dollars(c["a_sum"]), len(c["a"]))
        if c["only"]:
            tail += " Reported on 24-hour reports only, listed apart and not in that total: %s." % fl.dollars(c["only_sum"])
        L.append(tail)
        L.append("")
    L.append("Not added across committees: a total over committees would join money received by different "
             "committees. The per-committee Schedule A totals above are the figures to quote.")
    L.append("")
    if m["outside"]:
        L.append("Outside spending apart (form 496 reports naming the official, filed by committees the family's "
                 "names take; spending by those committees, not a gift to the official's committees):")
        for o in m["outside"]:
            L.append("- %s: %s, %s, %d filings, %s to %s." % (o["payer"], "supporting" if o["stance"] == "S" else "opposing",
                     fl.dollars(o["amount"]), o["filings"], o["d0"], o["d1"]))
    else:
        L.append("Outside spending apart: no form 496 report naming this official was filed by a committee the "
                 "family's names take.")
    return L


def render_pairing(p, snap, n):
    pk, mt, q, off = p["pk"], p["meeting"], p["quote"], p["official"]
    who = "%s (%s%s)" % (off["official"], off["office"], ", District %s" % off["district"] if off["district"] else "")
    L = ["## Pairing %d: %s and %s on %s" % (n, off["official"], p["family"]["name"], pk["subject"]), ""]
    L += ["### %d.1 The official's words, as the city's caption transcript publishes them" % n, "", "> " + q["text"], ""]
    L.append("- Meeting: %s, %s. Transcript time: %s to %s (caption stamps from the start of the recording)." % (
        mt["body"], mt["date"], q["first_stamp"], q["last_stamp"]))
    L.append("- Transcript: <%s> (Legistar caption transcript, retrieved %s). Wording is the transcript's; it was not "
             "checked against the recording." % (mt["url"], mt["retrieved"]))
    L.append("- Speaker named: **%s**, %s." % (who.split(" (")[0], who.split(" (", 1)[1].rstrip(")")))
    L += ["", "### %d.2 How the transcript supports that credit" % n, ""]
    for s, t in p["cues"]:
        L.append("- Caption row `%s`: %s" % (s, t))
    L.append("- What the transcript shows: " + pk["speaker"]["text_support"])
    L.append("- Doubt in the credit: **%s**. %s" % (pk["speaker"]["doubt"], pk["speaker"]["doubt_reason"]))
    for o in pk["speaker"]["outside"]:
        L.append("- Outside the transcript (read 2026-10-30): <%s>: %s" % (o["url"], o["says"]))
    L += ["", "### %d.3 The donor's priority in its own words" % n, ""]
    for s in p["statements"]:
        L.append("> " + s["text"])
        L.append("")
        L.append("- %s. Section: %s. Page type: %s%s. Source: <%s>. Retrieved %s." % (
            p["family"]["name"], s["section"], s["kind"], ", page dated %s" % s["page_date"] if s["page_date"] else "",
            s["url"], s["retrieved"]))
        L.append("")
    L += ["### %d.4 Why these two sit side by side" % n, "", "- Overlap (my reading): " + pk["overlap"],
          "- Positions (my reading): " + pk["stance"], ""]
    L += ["### %d.5 The money, by committee and filing" % n, ""] + money_md(p, snap)
    L += ["", "### %d.6 What this does not say" % n, "", NO_CAUSATION,
          "The family is read from names as filed (%s); a reader should confirm each is the organisation." % p["family"]["link_note"].rstrip(".") if p["family"]["link_note"] else "The family is read from names as filed; a reader should confirm each is the organisation.",
          ""]
    return L


def render_pairings_md(pairs, snap):
    L = ["# Pairings from the money: five San Francisco officials, a donor's own words and the money through committees tied to the official", "",
         "Written by `python build_map.py` from `data/` (transcripts, donor statements, money snapshot retrieved %s). "
         "Each pairing starts from money a donor family gave through a committee tied to the official; it then "
         "shows the official's exact caption words on a subject the donor's own page speaks to. %s" % (snap["retrieved"], NO_CAUSATION), ""]
    L.append("| # | Official | Words (meeting, stamp) | Donor | Schedule A to committees tied to the official |")
    L.append("|---|---|---|---|---|")
    for i, p in enumerate(pairs, 1):
        tot = ", ".join("%s %s" % (fl.dollars(c["a_sum"]), c["committee"]["filer_name"]) for c in p["money"]["per"].values())
        L.append("| %d | %s | %s %s, %s | %s | %s |" % (i, p["official"]["official"], p["meeting"]["body"], p["meeting"]["date"],
                 p["quote"]["first_stamp"], p["family"]["name"], tot))
    L.append("")
    for i, p in enumerate(pairs, 1):
        L += render_pairing(p, snap, i)
    return "\n".join(L) + "\n"


def recognition_stats(data):
    snap = data["snap"]
    st = collections.Counter()
    ex = collections.defaultdict(set)
    for r in snap["donors_org"]:
        if r["entity_code"] not in ("COM", "SCC"):
            continue
        st["committee giver rows"] += 1
        cid = r.get("committee_id")
        if cid:
            st["with an FPPC id"] += 1
        if cid in snap["filers_lookup"]:
            st["id resolves in the Filers dataset"] += 1
        if fl.sponsor_of(fl.donor_name(r)):
            st["name states a sponsor"] += 1
        fam, how = fl.family_of(data["fams"], fl.donor_name(r), cid)
        if fam:
            st["taken by a donor family"] += 1
            st["  by id" if how == "id" else "  by name"] += 1
            ex[fam].add(fl.donor_name(r))
    return st, ex


def render_map_md(data, agg, indep, routes, ind_check, st, ex):
    snap, fams = data["snap"], data["fams"]
    stats = committee_stats(snap)
    L = ["# Official funding map: committees tied to the Mayor and the eleven supervisors, who gave through them, and which givers publish a priority", "",
         "Written by `python build_map.py` from `data/money_snapshot.json` (Ethics Commission Transactions and Filers datasets on DataSF, %s; data loaded through %s) and `data/priorities.json`. Three kinds of money are kept apart and never added: **gifts** (Schedule A, per committee), **24-hour reports not yet on a periodic report** (listed with their own totals) and **outside spending** (form 496, by the committee that spent)." % (snap["retrieved"], snap["data_loaded_at"]), ""]
    L += ["## 1. Committees tied to each official", "",
          "Relation is read from the data's `filer_type` and the words of the committee's name; the data has no field for who controls a committee, so a ballot-measure committee is tied to an official by carrying the official's name, and that is a name tie. Own and measure committees are the official's; supporting and opposing committees are primarily formed committees that are not the official's own candidate committee (the data does not say who controls them) and their money is shown apart.", ""]
    for off, cs in by_official(snap).items():
        c0 = cs[0]
        L += ["### %s (%s%s)" % (off, c0["office"], ", District %s" % c0["district"] if c0["district"] else ""), "",
              "| Committee | Filer | Relation | Status | Schedule A rows | Schedule A total | 24-hour only | Last filing |", "|---|---|---|---|---|---|---|---|"]
        for c in sorted(cs, key=lambda c: (c["relation"], c["filer_name"])):
            s = stats[c["filer_nid"]]
            L.append("| %s | %s | %s | %s | %d | %s | %s | %s |" % (c["filer_name"], c["filer_nid"], c["relation_words"], c["status"].lower(),
                     s["a_n"], fl.dollars(s["a_sum"]), fl.dollars(s["h24_only_sum"]) if s["h24_only_n"] else "-", s["last_filing"] or "-"))
        L.append("")
    L += ["## 2. Who gave through those committees", "",
          "Organisations and committees by name (any amount), individuals only from %s within one committee. Grouped by donor family where one takes the name (see section 3), else by name as filed. 'Recognised' says how: by the FPPC id the row carries, or by name." % fl.dollars(snap["ind_list_min"]), ""]
    for off in by_official(snap):
        for grp, title in (("controlled", "gifts to the official's own and measure committees"), ("third-party", "gifts to primarily formed committees supporting or opposing the official")):
            ds = list(agg[off].get(grp, {}).values())
            if not ds:
                continue
            ds.sort(key=lambda d: -d["amount"])
            L += ["**%s: %s**" % (off, title), "", "| Giver (as filed) | Kind | Amount | Recognised as | Committees |", "|---|---|---|---|---|"]
            for d in ds[:8]:
                rec = "-"
                if d["family"]:
                    rec = "%s (%s)" % (next(f["name"] for f in fams if f["key"] == d["family"]), d["how"])
                elif d["sponsor"]:
                    rec = "names sponsor: %s" % d["sponsor"].title()
                L.append("| %s | %s | %s | %s | %s |" % ("; ".join(sorted(d["names"]))[:90], d["entity"], fl.dollars(d["amount"]), rec,
                         "; ".join("%s %s" % (fl.dollars(v), k[:40]) for k, v in sorted(d["by_committee"].items(), key=lambda x: -x[1])[:2])))
            L.append("")
    L += ["## 3. How a gift from an organisation's own committee is recognised as the organisation's", "",
          "Of %d committee and small-contributor-committee giver rows, grouped by committee and donor name:" % st["committee giver rows"], ""]
    for k in ("with an FPPC id", "id resolves in the Filers dataset", "name states a sponsor", "taken by a donor family", "  by id", "  by name"):
        L.append("- %s: %d" % (k.strip(), st[k]))
    L += ["", "| Family | Names the rows carry |", "|---|---|"]
    for f in fams:
        if ex.get(f["key"]):
            L.append("| %s | %s |" % (f["name"], "; ".join(sorted(ex[f["key"]]))[:300]))
    L += ["", "## 4. Donor families, whether they publish a priority, and where their money reached", "",
          "| Family | Kind | Publishes a priority in its own words (retrieved) | Gifts by receiving committee (Schedule A) | Outside spending (form 496) naming an official |", "|---|---|---|---|---|"]
    prio_by_fam = collections.defaultdict(list)
    for s in data["prio"].values():
        prio_by_fam[s["family"]].append(s)
    for f in fams:
        ps = prio_by_fam.get(f["key"], [])
        link = "; ".join(sorted({"<%s> (%s)" % (p["url"], p["retrieved"]) for p in ps})) or "none found"
        r = routes.get(f["key"], {})
        gifts = ", ".join("%s %s" % (k, fl.dollars(v)) for k, v in sorted(r.items()) if not k.startswith("outside")) or "none"
        out = fl.dollars(r.get("outside spending (form 496)", 0)) if r.get("outside spending (form 496)") else "none"
        L.append("| %s | %s | %s | %s | %s |" % (f["name"], f["kind"], link, gifts, out))
    L += ["", "Families with no money in these committees (none found) are still listed so a reader sees the search. Individuals:", ""]
    if ind_check:
        L += ["| Official | Giver | Amount | Survey class of own statement | Own source |", "|---|---|---|---|---|"]
        for r in sorted(ind_check, key=lambda r: -r["amount"]):
            L.append("| %s | %s | %s (%s) | %s | %s |" % (r["official"], r["name"], fl.dollars(r["amount"]), r["group"], r["class"], r["source"]))
    else:
        L.append("No listed individual matched the donor-priorities survey's individuals.")
    L += ["", "## 5. Outside spending naming an official, apart from gifts", "",
          "Form 496 reports, by the committee that filed them; spending by the committee, not a gift to the official's committees. A committee that is itself tied to the official (for example 'Believe in SF, Lurie for Mayor 2024') appears in section 1 as a committee and here as a spender.", ""]
    for off in by_official(snap):
        rows = [r for r in indep if r["official"] == off][:6]
        if not rows:
            continue
        L += ["**%s**" % off, "", "| Spender | Stance | Amount | Filings | Dates |", "|---|---|---|---|---|"]
        for r in rows:
            L.append("| %s | %s | %s | %d | %s to %s |" % (r["payer"][:80], "supports" if r["stance"] == "S" else "opposes", fl.dollars(r["amount"]), r["filings"], r["d0"], r["d1"]))
        L.append("")
    return L


REL_ORDER = ["own", "own-other", "measure", "supporting", "opposing"]
REL_NAMES = {"own": "own committee, Mayor or Supervisor", "own-other": "own committee, another office",
             "measure": "ballot-measure committee carrying the official's name",
             "supporting": "primarily formed committee supporting the official", "opposing": "primarily formed committee opposing the official"}


def render_limits_md(data, ent, indep, agg):
    L = ["## 6. The city's limits on who may give, and where organisations' money reached", "",
         "Rules as the Ethics Commission publishes them (read 2026-10-30): contributions to a candidate committee for City office are limited to $500 per source per election (<https://sfethics.org/guidance/campaigns/contributors/contributor-third-party-restrictions>); corporations, limited liability companies and limited liability partnerships may not contribute to candidate committees, though they may fund a separate segregated fund that does; non-candidate committees, including ballot-measure committees, are generally not limited, and candidate-controlled ballot-measure committees are not currently limited (<https://sfethics.org/ethics/2026/04/april-10-2026-agenda-item-5-report-discussion-on-proposed-campaign-finance-reforms-to-reinforce-contribution-limits-and-ensure-accountability-for-violations-of-city-law.html>); independent spending is not limited. A proposal to apply the limit to candidate-controlled committees was approved by the Commission in August 2026 and needs the Board of Supervisors, taking effect no earlier than 1 January 2027 (<https://growsf.org/news/2026-08-14-ethics-commission-campaign-finance-loopholes/>).", "",
         "What the filings show, Schedule A by the relation of the receiving committee (all committees tied to the twelve officials, any year):", "",
         "| Receiving committee | Individuals | Organisations and committees | Organisation share | Committee giver code COM |", "|---|---|---|---|---|"]
    for rel in REL_ORDER:
        e = ent.get(rel)
        if not e:
            continue
        tot = e["ind"] + e["org"]
        L.append("| %s | %s | %s | %.1f%% | %s |" % (REL_NAMES[rel], fl.dollars(e["ind"]), fl.dollars(e["org"]),
                 100 * e["org"] / tot if tot else 0, fl.dollars(e["by_code"].get("COM", 0))))
    L += ["", "Outside spending (form 496) naming the twelve officials, by whether the spender's name is taken by a donor family:", ""]
    fam_total = sum(r["amount"] for r in indep if r["family"])
    all_total = sum(r["amount"] for r in indep)
    L.append("- Form 496 spending naming an official, all spenders: %s over %d spender-official-stance groups; of which by committees a donor family's names take: %s. Not added to any gift." % (fl.dollars(all_total), len(indep), fl.dollars(fam_total)))
    selfg = []
    for off, groups in agg.items():
        for d in groups.get("controlled", {}).values():
            if d["entity"] == "IND" and fl.norm_name(d["name"]) == fl.norm_name(off):
                selfg.append("%s %s" % (off, fl.dollars(d["amount"])))
    L.append("- Gifts by an official in their own name to their own and measure committees are inside the 'Individuals' column above: %s." % ("; ".join(selfg) or "none found"))
    sponsored = sum(r["amount"] for r in indep if fl.sponsor_of(r["payer"]))
    L.append("- Of the spending, committees whose names state a sponsor: %s (a sponsor such as 'Labor Organizations' names no single organisation)." % fl.dollars(sponsored))
    return L


def main(argv=None):
    data = load_all()
    snap = data["snap"]
    agg = aggregate_donors(data)
    indep = independent_for(data)
    routes = family_routes(data, indep)
    ind_check = individuals_check(data, agg)
    st, ex = recognition_stats(data)
    ent = entity_table(snap)
    try:
        pairs = build_pairings(data, indep)
    except (ValueError, StopIteration) as exc:
        print("PAIRING FAILED: %s" % exc, file=sys.stderr)
        return 1
    md = render_map_md(data, agg, indep, routes, ind_check, st, ex) + [""] + render_limits_md(data, ent, indep, agg)
    pmd = render_pairings_md(pairs, snap)
    full = ("\n".join(md) + "\n") + pmd
    low = full.lower()
    bad = [w for w in CAUSAL if w in low and w != "influence"]
    if bad:
        print("CAUSAL WORDS: %s" % bad, file=sys.stderr)
        return 1
    with open(os.path.join(HERE, "funding-map.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    with open(os.path.join(HERE, "pairings.md"), "w", encoding="utf-8") as f:
        f.write(pmd)
    summary = {
        "retrieved": snap["retrieved"], "data_loaded_at": snap["data_loaded_at"],
        "committees": [{k: c[k] for k in ("official", "filer_nid", "filer_name", "filer_type", "status", "relation")} |
                       {k: v for k, v in committee_stats(snap)[c["filer_nid"]].items()} for c in snap["committees"]],
        "by_relation": {r: {"individuals": e["ind"], "organisations": e["org"]} for r, e in ent.items()},
        "family_routes": {k: dict(v) for k, v in routes.items()},
        "independent": [dict(r) for r in indep[:60]],
        "pairings": [{"n": i, "official": p["official"]["official"], "family": p["family"]["key"],
                      "meeting": p["meeting"]["date"], "stamp": p["quote"]["first_stamp"],
                      "schedule_a": {c["committee"]["filer_name"]: c["a_sum"] for c in p["money"]["per"].values()}}
                     for i, p in enumerate(pairs, 1)],
    }
    with open(os.path.join(HERE, "funding-map.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, default=list)
    print(full)
    return 0


if __name__ == "__main__":
    sys.exit(main())
