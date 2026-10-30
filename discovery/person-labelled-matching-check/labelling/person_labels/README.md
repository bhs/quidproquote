# Person labels

One JSON file per person, named after the labeler. The easiest way to make one is `../label.html`
(open it in a browser, label, download the file it offers); it records every label's time. The shape:

    {"format": 1, "labeler": "name or initials", "blind": true,
     "labels":   {"<pair id>": "real" | "loose" | "none"},
     "sides":    {"<pair id>": "same" | "opposite" | "unclear"},
     "speakers": {"<pair id>": "official" | "other" | "unclear"},
     "ms":       {"<pair id>": milliseconds from the pair appearing to Next},
     "ms_hidden": {"<pair id>": milliseconds the page was in a background tab},
     "notes":    {"<pair id>": "optional one line"}}

`blind: true` is the labeler's statement that they are a person (not an automated reader) and did not look at any
method's or judge's output, `../../results.md`, `../../matches-that-stand-out.md`, `../sheet-key.json` or
anyone else's labels before labelling. `run.py` ignores a file without it and lists it in `results.md`.

`sides` and `speakers` are asked only where the overlap is real or loose. Two or more labelers are welcome and are
what measure where people differ; `run.py` reads their lower middle level as the label.
