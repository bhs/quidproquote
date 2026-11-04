-- The pairing site's first schema: the roster and its committees, donors and their stated priorities, the money
-- fetched for them, the meetings' caption lines, the candidates the finder proposes and what a person decided,
-- and the log of fetch runs.

CREATE TABLE officials (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    office TEXT NOT NULL,
    district TEXT NOT NULL DEFAULT '',
    surname TEXT NOT NULL,
    given TEXT NOT NULL,
    exact_spellings TEXT NOT NULL,      -- JSON list: how the captions spell the surname when they get it right
    garbled_spellings TEXT NOT NULL     -- JSON list: spellings earlier transcripts showed for it
);

CREATE TABLE committees (
    filer_nid TEXT PRIMARY KEY,
    official_id INTEGER NOT NULL REFERENCES officials(id),
    filer_name TEXT NOT NULL,
    filer_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT '',
    fppc_id TEXT NOT NULL DEFAULT '',
    relation TEXT NOT NULL,             -- own, own-other, measure, supporting, opposing, other
    relation_words TEXT NOT NULL
);

CREATE TABLE donors (
    id INTEGER PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    patterns TEXT NOT NULL,             -- JSON: lists of words that must all be in a giver's name as filed
    exclude TEXT NOT NULL DEFAULT '[]', -- JSON: words that take a giver out
    committee_ids TEXT NOT NULL DEFAULT '[]', -- JSON: FPPC ids of the donor's own committees
    link_note TEXT NOT NULL DEFAULT ''
);

CREATE TABLE priorities (
    id INTEGER PRIMARY KEY,
    donor_id INTEGER NOT NULL REFERENCES donors(id),
    label TEXT NOT NULL DEFAULT '',
    section TEXT NOT NULL DEFAULT '',   -- the heading the words sit under on the donor's page
    words TEXT NOT NULL,                -- the donor's exact words
    source_type TEXT NOT NULL,
    url TEXT NOT NULL,
    page_date TEXT NOT NULL DEFAULT '',
    retrieved TEXT NOT NULL,
    measures TEXT NOT NULL DEFAULT '[]', -- JSON: measure names to look for (Prop H, ...)
    phrases TEXT NOT NULL DEFAULT '[]',  -- JSON: distinctive phrases to look for; a trailing * matches any ending
    created_at TEXT NOT NULL
);

CREATE TABLE contributions (
    id INTEGER PRIMARY KEY,
    donor_id INTEGER NOT NULL REFERENCES donors(id),
    filer_nid TEXT NOT NULL REFERENCES committees(filer_nid),
    form_type TEXT NOT NULL,            -- A (Schedule A) or F497P1 (24-hour report)
    filing_id_number TEXT NOT NULL,
    filing_version TEXT NOT NULL DEFAULT '',
    filing_date TEXT NOT NULL DEFAULT '',
    contribution_date TEXT NOT NULL,
    amount REAL NOT NULL,
    committee_id TEXT NOT NULL DEFAULT '',
    giver_name TEXT NOT NULL,
    entity_code TEXT NOT NULL DEFAULT ''
);
CREATE INDEX contributions_pair ON contributions(donor_id, filer_nid);

CREATE TABLE independent_spending (
    id INTEGER PRIMARY KEY,
    donor_id INTEGER NOT NULL REFERENCES donors(id),
    official_id INTEGER NOT NULL REFERENCES officials(id),
    payer_nid TEXT NOT NULL,
    payer TEXT NOT NULL,
    stance TEXT NOT NULL,               -- supporting or opposing
    amount REAL NOT NULL,
    filings TEXT NOT NULL,              -- JSON list of filing ids
    first_date TEXT NOT NULL,
    last_date TEXT NOT NULL
);

CREATE TABLE filer_records (
    fppc_id TEXT PRIMARY KEY,
    filer_name TEXT NOT NULL
);

CREATE TABLE meetings (
    id INTEGER PRIMARY KEY,             -- the Legistar transcript id
    body TEXT NOT NULL,
    date TEXT NOT NULL,
    url TEXT NOT NULL,
    retrieved TEXT NOT NULL,
    line_count INTEGER NOT NULL
);

CREATE TABLE lines (
    meeting_id INTEGER NOT NULL REFERENCES meetings(id),
    idx INTEGER NOT NULL,
    stamp TEXT NOT NULL,
    text TEXT NOT NULL,
    PRIMARY KEY (meeting_id, idx)
);

CREATE TABLE candidates (
    id INTEGER PRIMARY KEY,
    donor_id INTEGER NOT NULL REFERENCES donors(id),
    official_id INTEGER NOT NULL REFERENCES officials(id),
    meeting_id INTEGER NOT NULL REFERENCES meetings(id),
    priority_ids TEXT NOT NULL,         -- JSON: the priorities whose measure or phrase the remark names
    hits TEXT NOT NULL,                 -- JSON: the words of the remark that matched
    first_idx INTEGER NOT NULL,         -- caption rows holding the remark
    last_idx INTEGER NOT NULL,
    start_off INTEGER NOT NULL,         -- character offsets of the remark and of the turn in the joined captions
    end_off INTEGER NOT NULL,
    region_start INTEGER NOT NULL,
    region_end INTEGER NOT NULL,
    text TEXT NOT NULL,
    first_stamp TEXT NOT NULL,
    last_stamp TEXT NOT NULL,
    doubt TEXT NOT NULL,                -- low, medium or high
    doubt_why TEXT NOT NULL,            -- JSON list
    cue_text TEXT NOT NULL,
    cue_stamp TEXT NOT NULL,
    cue_lines TEXT NOT NULL,            -- JSON: [[stamp, text], ...] the caption rows holding the cue
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, approved or rejected
    created_at TEXT NOT NULL,
    reviewed_at TEXT,
    slug TEXT UNIQUE,                   -- set when approved: the card's own URL
    quote_text TEXT,
    quote_first_stamp TEXT,
    quote_last_stamp TEXT,
    doubt_note TEXT NOT NULL DEFAULT '',
    in_common TEXT NOT NULL DEFAULT '',
    differs TEXT NOT NULL DEFAULT '',
    reject_note TEXT NOT NULL DEFAULT '',
    UNIQUE (donor_id, official_id, meeting_id, first_stamp)
);
CREATE INDEX candidates_status ON candidates(status);

CREATE TABLE card_statements (
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    priority_id INTEGER NOT NULL REFERENCES priorities(id),
    PRIMARY KEY (candidate_id, priority_id)
);

CREATE TABLE fetch_runs (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,                 -- scheduled, manual or seed
    started_at TEXT NOT NULL,
    finished_at TEXT,
    ok INTEGER,
    summary TEXT NOT NULL DEFAULT '',
    error TEXT NOT NULL DEFAULT ''
);

CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
