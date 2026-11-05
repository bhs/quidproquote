-- The first schema of the pairing site: transcripts, donors' priorities, the source data for money,
-- pairings (published, waiting and rejected), the pairs the AI filter dropped, the audit log and the worker's
-- progress rows.

CREATE TABLE meetings (
    id            integer PRIMARY KEY,
    body          text NOT NULL,
    meeting_date  date NOT NULL,
    url           text NOT NULL,
    recording_url text NOT NULL,
    retrieved     date NOT NULL,
    row_count     integer NOT NULL,
    captions      text NOT NULL
);

CREATE TABLE donor_priorities (
    id        serial PRIMARY KEY,
    key       text NOT NULL UNIQUE,
    family    text NOT NULL,
    donor     text NOT NULL,
    url       text NOT NULL,
    section   text NOT NULL DEFAULT '',
    text      text NOT NULL,
    page_date text NOT NULL DEFAULT '',
    retrieved date NOT NULL,
    kind      text NOT NULL,
    added_by  text NOT NULL,
    added_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE source_data (
    name      text PRIMARY KEY,
    retrieved date NOT NULL,
    payload   jsonb NOT NULL
);

CREATE TABLE pairings (
    id                     serial PRIMARY KEY,
    slug                   text NOT NULL UNIQUE,
    candidate_key          text UNIQUE,
    status                 text NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
    source                 text NOT NULL,
    official               text NOT NULL,
    donor_key              text NOT NULL,
    donor_name             text NOT NULL,
    meeting_id             integer NOT NULL,
    meeting_date           date NOT NULL,
    first_stamp            text NOT NULL,
    quote_text             text NOT NULL,
    card                   jsonb NOT NULL,
    ai                     jsonb,
    recording_url          text NOT NULL,
    recording_checked      boolean NOT NULL DEFAULT false,
    recording_checked_at   timestamptz,
    published_at           date,
    decided_at             timestamptz,
    decision_note          text NOT NULL DEFAULT '',
    created_at             timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX pairings_status_idx ON pairings (status, published_at DESC);

CREATE TABLE dropped_pairs (
    id             serial PRIMARY KEY,
    candidate_key  text NOT NULL UNIQUE,
    official       text NOT NULL,
    donor_key      text NOT NULL,
    donor_name     text NOT NULL,
    meeting_id     integer NOT NULL,
    meeting_body   text NOT NULL,
    meeting_date   date NOT NULL,
    first_stamp    text NOT NULL,
    last_stamp     text NOT NULL,
    quote_text     text NOT NULL,
    priority_text  text NOT NULL,
    priority_url   text NOT NULL,
    reason_kind    text NOT NULL,
    reason         text NOT NULL,
    stage          text NOT NULL,
    model          text NOT NULL DEFAULT '',
    created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (
    id         serial PRIMARY KEY,
    at         timestamptz NOT NULL DEFAULT now(),
    actor      text NOT NULL,
    action     text NOT NULL,
    pairing_id integer,
    detail     text NOT NULL DEFAULT ''
);

CREATE TABLE progress (
    id          serial PRIMARY KEY,
    run_id      text NOT NULL,
    step        text NOT NULL,
    status      text NOT NULL CHECK (status IN ('running', 'ok', 'error', 'skipped')),
    detail      text NOT NULL DEFAULT '',
    counts      jsonb NOT NULL DEFAULT '{}'::jsonb,
    started_at  timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz
);
CREATE INDEX progress_run_idx ON progress (run_id, id);

CREATE TABLE worker_state (
    id          integer PRIMARY KEY CHECK (id = 1),
    next_run_at timestamptz,
    last_run_id text,
    last_error  text NOT NULL DEFAULT '',
    updated_at  timestamptz NOT NULL DEFAULT now()
);
INSERT INTO worker_state (id) VALUES (1);
