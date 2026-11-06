-- A donor priority may be taken from a news report instead of the organisation's own site. `kind` already says
-- what the source is: 'news report' marks a reported priority (the earlier values name a page on the
-- organisation's own site). A reported priority also names the outlet and whose words the quoted text is:
-- 'reporter' (the reporter's description of the donor's position), 'donor-quoted' (the donor's own words, quoted)
-- or 'third-party' (someone else's words, quoted). Both stay empty for a page on the organisation's own site.
-- The page date stays text and the retrieval date stays the server's: neither changes here.
ALTER TABLE donor_priorities ADD COLUMN outlet TEXT NOT NULL DEFAULT '';
ALTER TABLE donor_priorities ADD COLUMN whose_words TEXT NOT NULL DEFAULT ''
    CHECK (whose_words IN ('', 'reporter', 'donor-quoted', 'third-party'));
