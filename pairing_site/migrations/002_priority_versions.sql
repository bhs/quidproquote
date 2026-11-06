-- Donors' priorities that are reported by others, and priorities that can be edited without losing their earlier
-- wording.
--
-- outlet, whose_words: a priority taken from a news report names the outlet that published it and whose words
--   the text is (reporter, donor_person: a named person at the donor quoted, third_party). A priority in the
--   donor's own words leaves both empty, so whose_words <> '' is what marks a priority as reported.
-- page_checked: 1 when the words were found on the page at the link, 0 when the page could not be fetched and
--   the priority was saved without that check (shown as "not checked against page").
-- supersedes_key, replaced_at: an edit inserts a new row whose supersedes_key is the key of the row it replaces,
--   and stamps the old row's replaced_at. The old row is never changed otherwise; lists show only rows whose
--   replaced_at is empty, and the chain of supersedes_key values is the history of one priority.

ALTER TABLE donor_priorities ADD COLUMN outlet TEXT NOT NULL DEFAULT '';
ALTER TABLE donor_priorities ADD COLUMN whose_words TEXT NOT NULL DEFAULT ''
    CHECK (whose_words IN ('', 'reporter', 'donor_person', 'third_party'));
ALTER TABLE donor_priorities ADD COLUMN page_checked BOOLEAN NOT NULL DEFAULT 1 CHECK (page_checked IN (0, 1));
ALTER TABLE donor_priorities ADD COLUMN supersedes_key TEXT;
ALTER TABLE donor_priorities ADD COLUMN replaced_at TIMESTAMP;
CREATE INDEX donor_priorities_supersedes_idx ON donor_priorities (supersedes_key);
