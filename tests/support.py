"""Shared fixtures: a temporary database holding a small, synthetic pairing (no network, no real names beyond the
roster's officials)."""

import os
import tempfile

from pairing_site import config, db, fetcher, money, review

DORSEY_OWN = "203924838"  # Matt Dorsey for Supervisor 2022 (own committee, in the roster)

MEETING = [
    ("00:00:01", ">> WELCOME TO THE REGULAR MEETING OF THE BOARD."),
    ("00:00:05", "SUPERVISOR WALTON WALTON PRESENT SUPERVISOR WONG WONG PRESENT"),
    ("00:00:09", ">> SUPERVISOR DORSEY THANK YOU PRESIDENT. COLLEAGUES, TODAY I SPEAK ABOUT"),
    ("00:00:12", "THE PARCEL TAX FOR MUNI OPERATIONS AND WHY IT MATTERS."),
    ("00:00:15", "MUNI RIDERS DEPEND ON IT EVERY DAY. THE WEATHER IS FINE."),
    ("00:00:18", "THANK YOU FOR YOUR TIME TODAY COLLEAGUES. >> SUPERVISOR WONG THANK YOU."),
    ("00:00:21", "I WILL SPEAK ABOUT THE PARCEL TAX TOO, AND ABOUT MUNI."),
    ("00:00:24", "THAT IS ALL FOR NOW."),
]


def make_env():
    """Environment variables for a temporary database file."""
    d = tempfile.mkdtemp(prefix="pairing-test-")
    return {"ADMIN_PASSWORD": "secret-pw", "FETCH_CONTACT_EMAIL": "maintainer@example.org",
            "DATABASE_PATH": os.path.join(d, "site.db")}


def make_db(env=None, with_priority=True):
    """A migrated database with one donor funded in Matt Dorsey's own committee, one transcript and (by default)
    one priority, entered through the form code. Returns (conn, ids)."""
    env = env or make_env()
    settings = config.load(env)
    conn = db.init(settings["database_path"])
    donor_id = review.save_donor(conn, {"name": "Acme Transit Union", "kind": "union",
                                        "patterns": "ACME TRANSIT UNION\nACME TRANSIT"})
    donor = conn.execute("SELECT * FROM donors WHERE id=?", (donor_id,)).fetchone()
    rows = [
        {"filer_nid": DORSEY_OWN, "form_type": "A", "filing_id_number": "1001", "filing_version": "1.0",
         "filing_date": "2026-02-01T00:00:00.000", "calculated_date": "2026-01-15T00:00:00.000",
         "calculated_amount": "500.0", "committee_id": "", "entity_code": "OTH", "fn": "", "ln": "Acme Transit Union"},
        {"filer_nid": DORSEY_OWN, "form_type": "A", "filing_id_number": "1002", "filing_version": "1.0",
         "filing_date": "2026-03-01T00:00:00.000", "calculated_date": "2026-02-20T00:00:00.000",
         "calculated_amount": "250.0", "committee_id": "", "entity_code": "OTH", "fn": "", "ln": "Acme Transit Union"},
        {"filer_nid": DORSEY_OWN, "form_type": "F497P1", "filing_id_number": "1003", "filing_version": "1.0",
         "filing_date": "2026-02-21T00:00:00.000", "calculated_date": "2026-02-20T00:00:00.000",
         "calculated_amount": "250.0", "committee_id": "", "entity_code": "OTH", "fn": "", "ln": "Acme Transit Union"},
        {"filer_nid": DORSEY_OWN, "form_type": "F497P1", "filing_id_number": "1004", "filing_version": "1.0",
         "filing_date": "2026-04-02T00:00:00.000", "calculated_date": "2026-04-01T00:00:00.000",
         "calculated_amount": "100.0", "committee_id": "", "entity_code": "OTH", "fn": "", "ln": "Acme Transit Union"},
        {"filer_nid": DORSEY_OWN, "form_type": "A", "filing_id_number": "1005", "filing_version": "1.0",
         "filing_date": "2026-03-01T00:00:00.000", "calculated_date": "2026-02-21T00:00:00.000",
         "calculated_amount": "999.0", "committee_id": "", "entity_code": "OTH", "fn": "", "ln": "Somebody Else Entirely"},
    ]
    money.replace_contributions(conn, donor, rows)
    fetcher.store_meeting(conn, 900001, "Board of Supervisors", "2026-07-14", MEETING, retrieved="2026-10-01")
    ids = {"donor": donor_id, "meeting": 900001}
    if with_priority:
        ids["priority"] = review.save_priority(conn, priority_form(donor_id))
    return conn, ids


def priority_form(donor_id, **over):
    form = {"donor_id": donor_id, "label": "TRANSIT", "section": "Proposition H - Parcel Tax to Fund Public Muni Operations",
            "words": "Acme Transit Union supports the parcel tax to fund Muni operations. Riders depend on Muni every day.",
            "source_type": "voter guide on the organisation's own site", "url": "https://example.org/voter-guide",
            "retrieved": "2026-10-01", "page_date": "2026-09-20", "measures": "", "phrases": "parcel tax\nMuni"}
    form.update(over)
    return form
