-- The first schema of the pairing site, in SQLite: transcripts, donors' priorities, the source data for money,
-- pairings (published, waiting and rejected), the pairs the AI filter dropped, the audit log and the worker's
-- progress rows.
--
-- Column types name how db.py reads a value back: DATE and TIMESTAMP hold ISO 8601 text (timestamps in UTC),
-- BOOLEAN holds 0 or 1, JSON_TEXT holds JSON text (it has TEXT affinity, so SQLite never turns it into a number).

CREATE TABLE meetings (
    id            INTEGER PRIMARY KEY,
    body          TEXT NOT NULL,
    meeting_date  DATE NOT NULL,
    url           TEXT NOT NULL,
    recording_url TEXT NOT NULL,
    retrieved     DATE NOT NULL,
    row_count     INTEGER NOT NULL,
    captions      TEXT NOT NULL
);

CREATE TABLE donor_priorities (
    id        INTEGER PRIMARY KEY,
    key       TEXT NOT NULL UNIQUE,
    family    TEXT NOT NULL,
    donor     TEXT NOT NULL,
    url       TEXT NOT NULL,
    section   TEXT NOT NULL DEFAULT '',
    text      TEXT NOT NULL,
    page_date TEXT NOT NULL DEFAULT '',
    retrieved DATE NOT NULL,
    kind      TEXT NOT NULL,
    added_by  TEXT NOT NULL,
    added_at  TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now'))
);

CREATE TABLE source_data (
    name      TEXT PRIMARY KEY,
    retrieved DATE NOT NULL,
    payload   JSON_TEXT NOT NULL CHECK (json_valid(payload))
);

CREATE TABLE pairings (
    id                     INTEGER PRIMARY KEY,
    slug                   TEXT NOT NULL UNIQUE,
    candidate_key          TEXT UNIQUE,
    status                 TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
    source                 TEXT NOT NULL,
    official               TEXT NOT NULL,
    donor_key              TEXT NOT NULL,
    donor_name             TEXT NOT NULL,
    meeting_id             INTEGER NOT NULL,
    meeting_date           DATE NOT NULL,
    first_stamp            TEXT NOT NULL,
    quote_text             TEXT NOT NULL,
    card                   JSON_TEXT NOT NULL CHECK (json_valid(card)),
    ai                     JSON_TEXT CHECK (json_valid(ai)),
    recording_url          TEXT NOT NULL,
    recording_checked      BOOLEAN NOT NULL DEFAULT 0 CHECK (recording_checked IN (0, 1)),
    recording_checked_at   TIMESTAMP,
    published_at           DATE,
    decided_at             TIMESTAMP,
    decision_note          TEXT NOT NULL DEFAULT '',
    created_at             TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now'))
);
CREATE INDEX pairings_status_idx ON pairings (status, published_at DESC);

CREATE TABLE dropped_pairs (
    id             INTEGER PRIMARY KEY,
    candidate_key  TEXT NOT NULL UNIQUE,
    official       TEXT NOT NULL,
    donor_key      TEXT NOT NULL,
    donor_name     TEXT NOT NULL,
    meeting_id     INTEGER NOT NULL,
    meeting_body   TEXT NOT NULL,
    meeting_date   DATE NOT NULL,
    first_stamp    TEXT NOT NULL,
    last_stamp     TEXT NOT NULL,
    quote_text     TEXT NOT NULL,
    priority_text  TEXT NOT NULL,
    priority_url   TEXT NOT NULL,
    reason_kind    TEXT NOT NULL,
    reason         TEXT NOT NULL,
    stage          TEXT NOT NULL,
    model          TEXT NOT NULL DEFAULT '',
    created_at     TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now'))
);

CREATE TABLE audit_log (
    id         INTEGER PRIMARY KEY,
    at         TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')),
    actor      TEXT NOT NULL,
    action     TEXT NOT NULL,
    pairing_id INTEGER,
    detail     TEXT NOT NULL DEFAULT ''
);

CREATE TABLE progress (
    id          INTEGER PRIMARY KEY,
    run_id      TEXT NOT NULL,
    step        TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('running', 'ok', 'error', 'skipped')),
    detail      TEXT NOT NULL DEFAULT '',
    counts      JSON_TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(counts)),
    started_at  TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')),
    finished_at TIMESTAMP
);
CREATE INDEX progress_run_idx ON progress (run_id, id);

CREATE TABLE worker_state (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    next_run_at TIMESTAMP,
    last_run_id TEXT,
    last_error  TEXT NOT NULL DEFAULT '',
    updated_at  TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now'))
);
INSERT INTO worker_state (id) VALUES (1);
