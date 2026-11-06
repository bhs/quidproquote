-- Priorities reported by a news outlet, and the edit history of every priority.
--
-- donor_priorities.outlet names the outlet of a news report (its kind is then 'news report'); it is empty for a
-- donor's own page. version counts the wordings a priority has had: 1 until it is edited, and updated_at says when
-- the current wording was written. An edit never overwrites the earlier wording: the whole old row is written as
-- JSON to audit_log.snapshot, with audit_log.priority_id naming the priority, and the 'Earlier wording' page reads
-- those snapshots.

ALTER TABLE donor_priorities ADD COLUMN outlet TEXT NOT NULL DEFAULT '';
ALTER TABLE donor_priorities ADD COLUMN version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE donor_priorities ADD COLUMN updated_at TIMESTAMP;

ALTER TABLE audit_log ADD COLUMN priority_id INTEGER;
ALTER TABLE audit_log ADD COLUMN snapshot JSON_TEXT CHECK (snapshot IS NULL OR json_valid(snapshot));
CREATE INDEX audit_log_priority_idx ON audit_log (priority_id, id);
