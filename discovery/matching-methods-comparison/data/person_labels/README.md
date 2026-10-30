# Person labels

Drop one JSON file per person here, named after the labeler, in this shape:

    {"labeler": "name or initials",
     "labels": {"<pair id>": "real" | "loose" | "none", ...},
     "notes": {"<pair id>": "optional one line"}}

Pair ids are those in `../../labelling-sheet.json` (written by `compare.py`): the quote's passage id,
a vertical bar and the priority id. `compare.py` uses these files as the labels when any exist
(the lower middle level where labelers differ) and reports where the labelers disagree.
Do not look at any method's or judge's output before labelling.
