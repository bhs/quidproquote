# Card design space: how a pairing card shows the words, the priority and the money

**Kind of hop: an exploration** of how the product could work (the card a reader meets), written as a design space. It recommends, ranks and chooses nothing; the redesign that follows chooses. The same content as data is in `design-space.json`; the mockups are in `mockups/` (open `mockups/index.html`); the summary is `findings.md`.

## Contents

- [What every card carries (held fixed)](#what-every-card-carries-held-fixed)
- [What was mocked up, and on what](#what-was-mocked-up-and-on-what)
- [See the words, priority and money together](#see-the-words-priority-and-money-together)
  - [How the card is laid out](#how-the-card-is-laid-out) (choose one)
    - [Three zones side by side](#three-zones-side-by-side)
    - [Words first](#words-first)
    - [Matched pair with a money ledger](#matched-pair-with-a-money-ledger)
    - [Glance row that opens](#glance-row-that-opens)
  - [What a phone does with the zones](#what-a-phone-does-with-the-zones) (choose one)
    - [Stack in zone order](#stack-in-zone-order)
    - [Words first on a phone](#words-first-on-a-phone)
    - [Fold zones behind headings](#fold-zones-behind-headings)
- [Show doubt and caveats without implying cause](#show-doubt-and-caveats-without-implying-cause)
  - [Where the reading strip sits](#where-the-reading-strip-sits) (choose one)
    - [Under the three zones](#under-the-three-zones)
    - [Between the words and the money](#between-the-words-and-the-money)
    - [As a label at the top](#as-a-label-at-the-top)
  - [How speaker-credit doubt is shown](#how-speaker-credit-doubt-is-shown) (choose one)
    - [Badge with the level only](#badge-with-the-level-only)
    - [Badge with the reason on the card](#badge-with-the-reason-on-the-card)
    - [Badge that opens its reason](#badge-that-opens-its-reason)
  - [How shared words are marked](#how-shared-words-are-marked) (any of these)
    - [Highlight in both texts](#highlight-in-both-texts)
    - [Shared-word chips](#shared-word-chips)
    - [A plain line when nothing is shared](#a-plain-line-when-nothing-is-shared)
- [Show money without inviting a sum](#show-money-without-inviting-a-sum)
  - [How committee lines are laid out](#how-committee-lines-are-laid-out) (choose one)
    - [One block per committee](#one-block-per-committee)
    - [A ledger table](#a-ledger-table)
    - [One compact line per committee in lists](#one-compact-line-per-committee-in-lists)
  - [How outside spending is kept apart](#how-outside-spending-is-kept-apart) (choose one)
    - [A separate dashed box below the gifts](#a-separate-dashed-box-below-the-gifts)
    - [A flag in the list and a box on the card](#a-flag-in-the-list-and-a-box-on-the-card)
    - [Left off the card and linked](#left-off-the-card-and-linked)
  - [How a many-to-one donor is shown](#how-a-many-to-one-donor-is-shown) (choose one)
    - [One bubble with a tie note](#one-bubble-with-a-tie-note)
    - [Giver names as a count that opens](#giver-names-as-a-count-that-opens)
    - [Giver names listed as filed](#giver-names-listed-as-filed)
- [Serve scanning, reading and checking](#serve-scanning-reading-and-checking)
  - [What the list shows of each card](#what-the-list-shows-of-each-card) (choose one)
    - [The whole card](#the-whole-card)
    - [A row that opens](#a-row-that-opens)
    - [The words cut with the card a click away](#the-words-cut-with-the-card-a-click-away)
  - [What the card's own page adds](#what-the-cards-own-page-adds) (any of these)
    - [Row-level filing table](#row-level-filing-table)
    - [Recording and transcript links](#recording-and-transcript-links)
    - [A copyable link and a printable view](#a-copyable-link-and-a-printable-view)
  - [Where sources sit](#where-sources-sit) (choose one)
    - [One sources row at the bottom](#one-sources-row-at-the-bottom)
    - [A source link beside each element](#a-source-link-beside-each-element)
    - [Both](#both)
- [Layouts side by side](#layouts-side-by-side)
- [Open questions](#open-questions)

## What every card carries (held fixed)

These are not options. Every mockup layout is built from the same fragments (`card_design_lib.py`), and `build_mockups.py` refuses to write a page when a card in any layout, list or single, breaks one of them.

- The official's words exactly as the transcript has them, in quotation marks, with meeting, date and time stamp. A list row may cut the words, marking the cut outside the quotation marks.
- The donor's priority in the donor's own words, with the organisation, page date and a source link; the note on how the donor is tied to the givers (by Filers id or by name only).
- One line per receiving committee with its own Schedule A total, kind, rows and dates, and the giver names as filed. No total across committees appears anywhere; the build fails if the sum of a card's committee totals appears in its text.
- Outside spending, when present, in its own container labelled as a different record, with no sum of it with anything.
- Highlights only on words literally in both the quote and the donor's words; the build fails on a term not in both.
- A 'reading, not a finding' strip with 'No cause is claimed.' and the speaker-credit doubt badge, and a sources row with the transcript, the donor page, the filing ids and the money retrieval date.

## What was mocked up, and on what

- **Content:** the five cards of the Official funding map (`data/pairing-cards.json`, a copy of `../official-funding-map/pairing-cards.json`) and a sixth, the worked pairing of Bilal Mahmood and GrowSF from `../worked-pairing-examples/` (`data/outside-spending-example.json`), whose only money is outside spending. Card 6 is a stress case that the built cards do not cover (no card of the five has outside spending, and none has more than two committees); Project Memory says a pairing with no money found is not shown as a card, and card 6 has outside spending but no gift, so whether such a pairing is a card is the maintainer's to say.
- **Layouts:** options A to D under "How the card is laid out". The other dimensions are described, and mocked only where a layout already carries them (marked "mocked in" under each option).
- **Screens:** `mockups/index.html` shows each layout in frames 390 pixels wide (phone) and 1,320 pixels wide shown at half size (computer), as the list of six cards and as one card on its own page (card 4: two committees, 15 giver names, high speaker doubt). The pages are responsive, so opening `option-<a-d>-list.html` or `option-<a-d>-card.html#c4` at any window width shows the same.
- **Reading order:** `mockups/reading-order.json` counts, for each layout and card in the list view, the characters of visible text before the first dollar amount, the words and the donor's priority. It is a stand-in for how far a phone reader scrolls, not a measurement of a screen.
- **Not done:** the pages were not opened in a browser or on a phone in this work, and no reader tested them (see Open questions).

## See the words, priority and money together

A reader can say, without scrolling or reading a paragraph, what the official said, what the donor says it wants and what was given, and which words the two share.

### How the card is laid out

The overall arrangement of the three things a card must show, plus the official's name, on a computer-sized screen. Each is mocked up in `mockups/` (open `mockups/index.html`). Exclusive: a product takes one.

*The layout decides which of the three a reader meets first and whether the shared words are seen across two texts or inside one; it is worth seeing built more than one way because it is judged by readers, not by the data.*

Options: [Three zones side by side](#three-zones-side-by-side), [Words first](#words-first), [Matched pair with a money ledger](#matched-pair-with-a-money-ledger), [Glance row that opens](#glance-row-that-opens).

#### Three zones side by side

Money then the donor's priority on the left, the official in the middle, the official's exact words on the right; stacked in that order on a phone (mockup option A).

```
+---------------------+-------+------------------+
| MONEY IN            | Name  | "EXACT WORDS ...  |
|  $ per committee    | Role  |  with <shared>   |
| (priority bubble)   |       |  words marked"   |
+---------------------+-------+------------------+
| reading strip  [DOUBT: LOW]                     |
| sources                                         |
```

- **Makes easy:** Matches the layout the maintainer described. On a computer all three are in view at once, so money, priority and words share one glance. The left zone holds the donor's side whole, so the amount and the priority it comes with are read together.
- **Costs:** On a phone the words land last: in the mockup the first dollar amount comes after about 90 characters of text and the words after about 1,400 (card 4; counts in `mockups/reading-order.json`). The official's name sits in a narrow middle column that on a phone becomes a lone line between the donor and the words. The left zone gets long when a card has several committees.
- **Suits:** A reader who wants to take in the whole pairing on a computer, and the maintainer's own description.

#### Words first

The official's name and exact words are the headline; the donor's priority and the money sit under them, side by side on a computer, stacked on a phone (mockup option B).

```
Name, role
"EXACT WORDS ... <shared> ... ..."   meeting, date, stamp
+------------------+  +------------------+
| donor priority   |  | MONEY IN         |
| (bubble)         |  |  $ per committee |
+------------------+  +------------------+
reading strip / sources
```

- **Makes easy:** The words, the thing a reporter checks first, come first on every screen (about 90 characters in on a phone). The shared words are read in the words and then met again in the priority just below.
- **Costs:** Money is pushed down: the first dollar amount appears after about 1,040 characters on card 4 and 1,940 on card 3 on a phone. A scanner looking for money in a list has to scroll past every card's words. The headline words are long on some cards (card 3 is 1,211 characters).
- **Suits:** A reader who comes for what officials said, such as a reporter following a vote; weaker for a reader who comes for who gave.

#### Matched pair with a money ledger

The words and the donor's priority face each other in two columns with the shared words listed between them; the money is a ledger in its own box beneath (mockup option C).

```
[ Name x Donor ]
| WHAT WAS SAID        | WHAT THE DONOR SAYS |
| "... <shared> ..."   | "... <shared> ..."  |
          Words in both: [shared] [shared]
+- MONEY IN: separate record ----------------+
| $10,500 | committee | kind | rows, dates | ... |
+--------------------------------------------+
reading strip / sources
```

- **Makes easy:** Puts the two texts that share words next to each other, so the highlight is seen across them rather than recalled. The ledger gives money its own box and its own heading ('a separate record from the words'), which fits the rule that nothing implies the money explains the words.
- **Costs:** Two long texts side by side are the widest block on a computer and, with a priority statement of several paragraphs (card 5 has four), lopsided. The money is last: about 1,230 characters in on card 4 on a phone. A ledger needs a stacked fallback on a phone (the mockup turns each row into a block).
- **Suits:** A reader or checker comparing the two sets of words; a reporter reading closely.

#### Glance row that opens

In a list each card is a short row: names, shared words, the first words cut at a word boundary with the cut marked, one line per committee, the doubt badge and a flag when outside spending exists; the whole card opens in place or on its own page (mockup option D).

```
Name (role) x Donor                      [DOUBT: LOW]
Words in both: [shared] [shared]
"EXACT WORDS cut here ..." (cut for the list)
| $10,500 committee A (this committee only)
| $7,500  committee B (this committee only)
[Outside spending, kept apart: open the card]
   Open the whole card   (v)
```

- **Makes easy:** A list of cards is a list of about 500 to 600 characters each instead of 2,500 to 3,700, so many can be scanned. Money and words are both in the row. The card page shows the full card.
- **Costs:** The priority, the money detail and the reading strip are hidden until opened, so the list alone shows a pairing without the strip that says it is a reading. A cut quote in quotation marks is only safe when the cut is marked outside them and the shared words are shown separately (they are, as chips), because the cut can drop the highlighted words. Outside-only cards show no amount in the row.
- **Suits:** A reader scanning many cards; paired with any of A to C as the card's own page.

### What a phone does with the zones

Where the zones go when the screen is about 390 pixels wide, which this project's readers use. Not mocked as separate files; options A to D show the first (A, C), the second (B) and the third (D's open card). Exclusive: a product takes one.

*Most of the layouts above are really three phone orderings; choosing the order is choosing what a thumb meets first.*

Options: [Stack in zone order](#stack-in-zone-order), [Words first on a phone](#words-first-on-a-phone), [Fold zones behind headings](#fold-zones-behind-headings).

#### Stack in zone order

On a phone the zones stack as on a computer: money, donor priority, official, words.

```
[ money lines     ]
[ priority bubble ]
[ official        ]
[ words           ]
[ strip, sources  ]
```

- **Makes easy:** Same order everywhere, so a reader who knows the computer card knows the phone card. The amount is at the top.
- **Costs:** The words, the sentence the whole card is about, come after the donor's long statement (about 1,400 characters in on card 4).
- **Suits:** A money-first reader.

#### Words first on a phone

On a phone the words and the official come first, then the priority, then the money.

```
[ official, words ]
[ priority bubble ]
[ money lines     ]
[ strip, sources  ]
```

- **Makes easy:** The quote is in view on opening. The shared words are met in the words, then in the priority.
- **Costs:** The computer layout (money left) differs from the phone, so a screenshot or description of the card does not match on both. Money is far down on the longest cards.
- **Suits:** A reader following what officials say.

#### Fold zones behind headings

On a phone each zone is a heading that opens (money, donor's priority, words), with the shared words and the doubt badge always visible above them.

```
Name x Donor      [DOUBT: LOW]
Shared: [shared]
> Words
> Donor's priority
> Money in (2 committees)
```

- **Makes easy:** Everything about the card fits one screen; the reader chooses what to open.
- **Costs:** A folded card hides the reading strip and the no-sum note until opened; a reader who opens only the money sees it without the words it is shown beside. Needs a rule for which zone opens first.
- **Suits:** A scanner on a phone; a reader who knows what they want.

## Show doubt and caveats without implying cause

A reader sees the speaker-credit doubt, which words are shared and that the card is a reading, and cannot take the card as saying the money caused the words.

### Where the reading strip sits

Where the 'reading, not a finding' strip (the in-common and differs sentences and 'No cause is claimed.') is placed. The mockups put it under the zones (A to C) and inside the opened card (D). Exclusive: a product takes one.

*The strip is the card's only statement of what the pairing is; where it sits decides whether a reader meets it before or after the money.*

Options: [Under the three zones](#under-the-three-zones), [Between the words and the money](#between-the-words-and-the-money), [As a label at the top](#as-a-label-at-the-top).

#### Under the three zones

The strip is a full-width dashed band between the zones and the sources row, labelled 'Reading, not a finding.'

```
[ zones ]
- - - - - - - - - - - - - - -
[DOUBT: LOW] Reading, not a finding. In common ... Differs ... No cause is claimed.
- - - - - - - - - - - - - - -
sources
```

- **Makes easy:** It reads as the conclusion: the reader has the three things and then the plain statement of how they relate. One place on every card.
- **Costs:** A scanner who stops after the zones, or on a phone after the money, never reaches it (it comes after all three zones). In a glance row it is hidden until opened.
- **Suits:** A reader who reads top to bottom.

#### Between the words and the money

The strip sits between the words-and-priority block and the money block, so the two are never read side by side without it.

```
[ words | priority ]
[ Reading, not a finding. [DOUBT] ... No cause is claimed. ]
[ money ]
```

- **Makes easy:** The one arrangement that puts the strip physically between what was said and what was given, where a causal reading would form.
- **Costs:** Not mocked. It separates the money from the donor's priority it sits with in the maintainer's left zone, and puts a text band mid-card.
- **Suits:** A design whose first rule is to keep a reader from linking money and words.

#### As a label at the top

The card opens with a one-line label, the doubt badge and 'Reading, not a finding. No cause is claimed.'; the in-common and differs sentences stay under the zones.

```
[DOUBT: LOW]  Reading, not a finding. No cause is claimed.
Name x Donor
[ zones ]
In common ... Differs ...
```

- **Makes easy:** The caveat is the first thing on every card, including a card shared on its own or cut down for a list.
- **Costs:** Repeated on every card of a list, the label turns to wallpaper; the fuller sentences still come last.
- **Suits:** A list of many cards where the badge must show at a glance.

### How speaker-credit doubt is shown

How the low, medium or high doubt about who is speaking is presented. The mockups use a badge plus the reason in the strip; every built card carries a reason. Exclusive: a product takes one.

*The doubt is about whether the words are the official's at all; on card 4 (high) the caption names the speaker only phonetically.*

Options: [Badge with the level only](#badge-with-the-level-only), [Badge with the reason on the card](#badge-with-the-reason-on-the-card), [Badge that opens its reason](#badge-that-opens-its-reason).

#### Badge with the level only

A coloured badge reads 'SPEAKER-CREDIT DOUBT: HIGH' and nothing more.

```
[SPEAKER-CREDIT DOUBT: HIGH]
```

- **Makes easy:** Smallest; readable in a list row and on a phone.
- **Costs:** A reader cannot tell what 'high' rests on, or whether to trust the card, without leaving it.
- **Suits:** A list row, with the reason a tap away.

#### Badge with the reason on the card

The badge and the reason sentences sit together in the reading strip (as mocked in A to D).

```
[SPEAKER-CREDIT DOUBT: HIGH] ... Speaker credit: No caption cue spells the speaker's surname. Two pages name Supervisor Mahmood as the introducer ...
```

- **Makes easy:** The reader sees how the credit was reached with the words in front of them.
- **Costs:** The reasons run to two or three sentences and lengthen the strip.
- **Suits:** A card's own page, or a card the reader means to rely on.

#### Badge that opens its reason

The badge is a control that opens the reason beside it; in a list only the badge shows.

```
[SPEAKER-CREDIT DOUBT: HIGH (i)]  -> reason opens below
```

- **Makes easy:** Short on a phone and in lists, with the reason one tap away.
- **Costs:** A hidden reason can go unread; it needs markup that works without a pointer.
- **Suits:** A phone list.

### How shared words are marked

How words literally in both the quote and the donor's priority are shown. They are never rewritten; only literal shared words (a measure name, a topic) are marked, and a card with none says so. Inclusive: a product may take several.

*Highlights are the card's strongest visual claim of a link, so how far they reach decides how much a reader thinks the two texts agree.*

Options: [Highlight in both texts](#highlight-in-both-texts), [Shared-word chips](#shared-word-chips), [A plain line when nothing is shared](#a-plain-line-when-nothing-is-shared).

#### Highlight in both texts

The shared words are wrapped in a highlight in the official's words and in the donor's bubble (mocked in A to D).

```
"... TRANSFER TAX CODE ..."  <->  "... Foreclosure Transfer Tax ..."
        [yellow]                        [yellow]
```

- **Makes easy:** The reader sees the same word in both places and can check it is literally there; a term that is not in both texts stops the build.
- **Costs:** On a card with one marked word the pairing can look more connected than it is. A highlight says 'same words', not 'same position': card 4 shares two terms yet the positions differ.
- **Suits:** All readers.

#### Shared-word chips

The shared words are also listed as chips between or above the texts (mocked in C and D).

```
Words in both: [real estate market] [transfer tax]
```

- **Makes easy:** Works in a list row where the full texts are not shown, and survives a cut quote.
- **Costs:** A second place to read the same words; a chip loses its sentence.
- **Suits:** A scanner.

#### A plain line when nothing is shared

A card with no literally shared words says 'none of substance, so nothing is highlighted' and shows no chips.

```
Highlighted: none of substance, so nothing is highlighted.
```

- **Makes easy:** A card with nothing marked is not taken for a card someone forgot to mark.
- **Costs:** Two of the five built cards (2 and 3) are in this case; the wording must not read as a failure.
- **Suits:** A reporter reading the card as a lead on a subject.

## Show money without inviting a sum

A reader sees what was given through each committee and any outside spending and is never offered, or led toward, a total across committees or outside spending.

### How committee lines are laid out

The form of one committee's line: its Schedule A total, kind, row count, date range and the giver names as filed. Exclusive: a product takes one.

*Three of the five built cards (3, 4 and 5) have two committees each, and the Mayor's two cards have one measure committee each; the funding map (`../official-funding-map/funding-map.md`, Daniel Lurie table) lists three ballot-measure committees carrying his name, of which the third, Daniel Lurie for Prop E, is terminated and has no card. What a second line looks like decides whether a total is invited.*

Options: [One block per committee](#one-block-per-committee), [A ledger table](#a-ledger-table), [One compact line per committee in lists](#one-compact-line-per-committee-in-lists).

#### One block per committee

Each committee is its own block with its total as the largest text, labelled 'Schedule A, this committee only', and a note after the last: none is added to another (mocked in A, B, D).

```
$10,500  Schedule A, this committee only
Bilal Mahmood for DCCC Member 2024 (filer ...)
own committee, for another office; 4 rows, 2024-01-29 to 2024-02-06

$7,500   Schedule A, this committee only
Bilal Mahmood for Supervisor 2024 ...
```

- **Makes easy:** Each amount is read with its committee's name, kind and dates, which differ and should be read. Separate blocks do not line up as a column of figures.
- **Costs:** Tall: a third committee adds a third block, and the label repeats on each.
- **Suits:** Cards with two or three committees.

#### A ledger table

A table with one row per committee and columns for total, committee, kind, rows and dates, and giver as filed (mocked in C).

```
TOTAL    | COMMITTEE     | KIND   | ROWS, DATES | GIVER
$10,500  | ... DCCC 2024 | own... | 4 rows ...  | GFC ...
$7,500   | ... Supervisor| own    | 15 rows ... | GFC ...
```

- **Makes easy:** Compact, and good for checking because the columns are the filing's fields.
- **Costs:** A column of dollar amounts is the shape of a sum and the eye adds it; the mockup labels each cell 'this committee only' and repeats the no-sum note, but the shape remains. On a phone the table must become blocks.
- **Suits:** A checker reading one card closely.

#### One compact line per committee in lists

In a list each committee is one line, amount first, with 'this committee only' and the committee name; kind, rows and dates are on the card (mocked in D).

```
$10,500 Bilal Mahmood for DCCC Member 2024 (this committee only)
$7,500  Bilal Mahmood for Supervisor 2024 (this committee only)
```

- **Makes easy:** A scanner sees every committee in a line each.
- **Costs:** The list drops the kind of committee (own, officeholder, measure), which says how close it is to the official; stacked lines are still a column of figures.
- **Suits:** A list of many cards.

### How outside spending is kept apart

How money a committee spent itself on reports naming the official (form 496) is shown when a card has it. None of the five built cards has any; the one worked pairing that does (Mahmood and GrowSF: three filer lines, no gift to his committees) is mocked as card 6. Exclusive: a product takes one.

*The earlier worked pairings found outside spending, not gifts, for the one donor with money, so a card must show it without its reading as a gift.*

Options: [A separate dashed box below the gifts](#a-separate-dashed-box-below-the-gifts), [A flag in the list and a box on the card](#a-flag-in-the-list-and-a-box-on-the-card), [Left off the card and linked](#left-off-the-card-and-linked).

#### A separate dashed box below the gifts

Outside spending is a box with a different border and colour, headed 'Outside spending, kept apart', saying it is not a gift to any committee above and not added to one; each report line stands alone (mocked in A to C).

```
+- - - - - - - - - - - - - - - - - - - - - - +
| OUTSIDE SPENDING, KEPT APART                |
| a different record from the gifts above ... |
| $14,939.79  Grow SF PAC; supports; ...      |
| $131,170.23 Grow SF PAC Opposing ...; ...   |
+- - - - - - - - - - - - - - - - - - - - - - +
```

- **Makes easy:** Seen on the card without a click, and the border says 'not the same kind'. A card with only outside spending says no gift was found, so the box is not mistaken for gifts.
- **Costs:** Two of card 6's lines belong to one committee (different offices) and the third is a committee whose name opposes someone else; read together they invite adding, so each line carries 'not added to each other'. The box is long on a phone.
- **Suits:** Cards where outside spending is the only money.

#### A flag in the list and a box on the card

In a list the row carries a flag, 'Outside spending, kept apart: open the card', and no amount; the box is on the card (mocked in D).

```
[Outside spending, kept apart: open the card]
```

- **Makes easy:** A list never shows an outside-spending amount beside a gift, and the reader learns it exists.
- **Costs:** A reader scanning sees no amount and may take the card for one with less money; an outside-only card shows no amount at all in its row.
- **Suits:** A list of many cards.

#### Left off the card and linked

The card shows gifts only, with a line saying outside spending also exists and linking to the funding map section that lists it.

```
Gifts: ...
Also: outside spending naming this official (see the map)
```

- **Makes easy:** Smallest card; nothing on it can be added to anything.
- **Costs:** A pairing whose only money is outside spending shows no money, although Project Memory says outside spending is labelled separately if present.
- **Suits:** A product that treats outside spending as a separate page.

### How a many-to-one donor is shown

How a donor given through several chapters or sub-committees (card 4 has 15 giver names as filed) appears in the money lines and the donor bubble, with the note on how the tie is recognised. Exclusive: a product takes one.

*A bubble that holds many names must say how each is tied, or a reader takes a name match for a fact.*

Options: [One bubble with a tie note](#one-bubble-with-a-tie-note), [Giver names as a count that opens](#giver-names-as-a-count-that-opens), [Giver names listed as filed](#giver-names-listed-as-filed).

#### One bubble with a tie note

One donor bubble, with an italic line saying how the tie is recognised, by Filers id or by name only (mocked in every option).

```
Govern For California: stated priority
Tie recognised by name only (15 giver names as filed); the FPPC ids do not resolve ...
```

- **Makes easy:** One donor, one bubble, and the basis for the tie in it.
- **Costs:** Nothing separates an id tie from a name tie visually, so a weak tie is seen only if the line is read.
- **Suits:** All readers.

#### Giver names as a count that opens

The money line shows '15 giver names as filed' and the count opens to the full list in place (mocked in A to D when a line has more than three names).

```
15 giver names as filed (opens to the list)
```

- **Makes easy:** Keeps the money line short.
- **Costs:** The names as filed are the evidence for the tie, and stay folded until opened.
- **Suits:** A list.

#### Giver names listed as filed

Every giver name is listed in the money line.

```
GFC COURAGE COMMITTEE - BAY AREA CHAPTER; ... (15 names)
```

- **Makes easy:** Everything needed to check the tie is in view.
- **Costs:** Fifteen names bury the amount; not mocked.
- **Suits:** A checker on a computer.

## Serve scanning, reading and checking

A reader scanning many cards, one reading a card closely and one checking its sources each get what they need without the others' clutter.

### What the list shows of each card

How much of a card a list of many cards carries before the reader opens one. Full cards are mocked in A to C, rows in D. Exclusive: a product takes one.

*The list is how most readers meet the cards, so what it omits is what most readers never see.*

Options: [The whole card](#the-whole-card), [A row that opens](#a-row-that-opens), [The words cut with the card a click away](#the-words-cut-with-the-card-a-click-away).

#### The whole card

Every card in the list is the whole card (mocked in A to C).

```
[ card, 2,500 to 3,700 characters ]
[ card, 2,500 to 3,700 characters ]
```

- **Makes easy:** Nothing is hidden; every card carries its strip, badge and sources wherever it is read or shared.
- **Costs:** A card is 2,500 to 3,700 characters of text in the mockups, so a phone shows about one card a screen or two; comparing cards means scrolling.
- **Suits:** A short list, or a reader who reads each card.

#### A row that opens

Each card is a row of names, shared words, cut words, one line per committee and the badge; it opens in place to the whole card (mocked in D).

```
Name x Donor [DOUBT]
shared words / cut words
$ line per committee
Open the whole card
```

- **Makes easy:** About 450 to 600 characters a card, so many fit a screen, and each row carries both an amount and words.
- **Costs:** A row is not a self-contained card: it lacks the donor's priority and the reading strip, so a row shared alone says less than the card. The cut words need a mark.
- **Suits:** A scanner.

#### The words cut with the card a click away

Each card shows only the official and the words (cut if long) and the doubt badge; money and priority are on the card's page.

```
Name, role  [DOUBT]
"EXACT WORDS cut ..."  (cut)
Money and priority: open the card
```

- **Makes easy:** Shortest list, and the words come first.
- **Costs:** A list without money is not the pairing the project is about; not mocked.
- **Suits:** A feed of what officials said.

### What the card's own page adds

What a card's own page carries that the list does not, for the reader reading it closely or checking it. Inclusive: a product may take several.

*The page is where a reporter verifies a pairing, so what it adds sets how long verification takes.*

Options: [Row-level filing table](#row-level-filing-table), [Recording and transcript links](#recording-and-transcript-links), [A copyable link and a printable view](#a-copyable-link-and-a-printable-view).

#### Row-level filing table

Under each committee line, a table of each Schedule A row with date, filing id and version, filing date, amount and giver as filed, with 24-hour repeats listed apart (the built site's card already does this).

```
Given | Filing (version) | Filed | Amount | Giver as filed
```

- **Makes easy:** A checker can match every row to the filing without leaving the page.
- **Costs:** Long; its column of amounts is the shape of a sum, so the committee's own total and 'not added to another' stay beside it.
- **Suits:** A checker.

#### Recording and transcript links

The words carry a link to the city transcript at its time stamp and, where there is one, to the meeting recording.

```
Board of Supervisors, 2026-07-14, 00:03:46 to 00:03:59   transcript | recording
```

- **Makes easy:** The reader checks the words and the speaker at the source.
- **Costs:** A link from a stamp to a recording has not been found for the transcripts read (see Open questions).
- **Suits:** A reporter verifying a quote.

#### A copyable link and a printable view

The page has its own address that can be copied, and prints as a single card without navigation.

```
/pairings/<slug>   [Copy link]   [Print]
```

- **Makes easy:** A reporter can cite the card or put it in a notebook.
- **Costs:** A shared card must carry its strip and badge with it, which the whole-card layouts do and the row does not.
- **Suits:** A reporter or watchdog.

### Where sources sit

Where the transcript, donor page and filing links, and the money retrieval date, are placed on a card. Exclusive: a product takes one.

*Sources are what makes a card checkable, and a source far from the claim it supports is slower to check.*

Options: [One sources row at the bottom](#one-sources-row-at-the-bottom), [A source link beside each element](#a-source-link-beside-each-element), [Both](#both).

#### One sources row at the bottom

A single row at the bottom links the transcript, the donor page and the filing ids and gives the money retrieval date (as the maintainer described, mocked in A to D).

```
Sources: transcript | donor page | filing ids (dataset) | money retrieved 2026-10-30
```

- **Makes easy:** One place on every card; a card in any layout ends the same way.
- **Costs:** The reader must carry a link back up to the claim; the row is reached last, so a phone scanner may not see it.
- **Suits:** A reader who checks last.

#### A source link beside each element

Each part carries its own link: the words a transcript link, the priority a source link, the money its dataset link (the mockups include the first two in the words and the priority and keep the row).

```
"words"  transcript
"priority"  source page
Money in  filings
```

- **Makes easy:** A claim and its source are together; a card that is cut or shared in pieces keeps its links.
- **Costs:** More links on a card, so more to read past; filing ids per committee are long.
- **Suits:** A reader checking claim by claim.

#### Both

Links beside each element and a sources row that collects them with the retrieval date.

```
element links + sources row
```

- **Makes easy:** Serves a checker working claim by claim and one looking for the list of sources.
- **Costs:** The same link twice; the card is longer.
- **Suits:** A reporter or watchdog.

## Layouts side by side

Characters of visible text before each item in one list card on a phone (card 4: two committees; card 3: two committees and a 1,211-character quote; card 6: outside spending only). "Hidden" means the list view does not show it; "none" means the card has no such amount in the list view.

| Layout | Card 4: amount / words / priority | Card 3: amount / words | Card 6: amount / words | Text per list card |
|---|---|---|---|---|
| A. Three zones | 92 / 1,405 / 707 | 110 / 1,360 | 487 / 2,001 | 2,570 to 3,740 |
| B. Words first | 1,044 / 94 / 407 | 1,939 / 110 | 1,526 / 123 | 2,510 to 3,680 |
| C. Matched pair, ledger | 1,234 / 117 / 459 | 2,125 / 133 | 1,632 / 146 | 2,530 to 3,710 |
| D. Glance row that opens | 457 / 145 / hidden | 452 / 158 | none / 155 | 490 to 610 |

| Layout | Easy for a reader | Hard for a reader | Phone | Computer |
|---|---|---|---|---|
| A. Three zones | Seeing money and the donor's priority together; the maintainer's description | Meeting the words on a phone (they are last); a long money zone with several committees | Money first, words last, three stacked blocks | All three in one glance |
| B. Words first | Meeting the words first; checking the quote | Finding the money while scanning a list | Words first, then priority, then money | Words wide on top, priority and money beneath |
| C. Matched pair, ledger | Seeing the shared words in both texts; a separate, labelled money box | A very long priority beside a short quote; the money is last; the ledger's column of amounts | Pair stacks, ledger becomes blocks | Two texts side by side, ledger full width |
| D. Glance row that opens | Scanning many cards; seeing every committee line and a badge in a row | Reading the priority or the strip without opening; a row shared alone | Short rows, one tap to the card | Short rows, an open card in place |

The dimensions are independent of the layout: any of the three strip positions, doubt treatments, committee-line forms and source placements could go with any of A to D, except that the ledger form belongs with C.

## Open questions

**Not found, and where looked.** No reader test of any card was found in the repository (`discovery/` holds the pairing findings and the earlier card build, none a test with readers); no rendering of the mockups in a browser was available in this work, so how each looks on a real phone is unverified. The sources for the built cards are in `../official-funding-map/` and `../worked-pairing-examples/`.

**To ask a maintainer or test with readers.**

- Which of the layouts a reporter or watchdog finds fastest to read: this needs two or three local reporters timed on a few real cards (the same test the second objective's missing key result waits on). No such test has been run.
- Is a pairing whose only money is outside spending (card 6) a card? Project Memory's rule is "Pairings that have no money found are not shown as cards" and "Outside spending is kept apart and labelled separately if present"; read together they leave this case open (my reading).
- Does the list show the whole card or a row? This depends on whether a card shared alone, or read in a list, must always carry the strip and the doubt badge; rows in option D drop the strip and carry the badge.
- Which of the objectives' unwritten key results (return visitors, stories written, correction mail) a card page can support: a copyable link and a printable view (under "What the card's own page adds") are what a reporter's return visit or citation would need; no source says which measure the maintainer will use.

**Claims not verified.**

- Whether a time stamp on a city transcript can be turned into a link to the point in the meeting recording: the earlier worked pairings found no source that resolves it (see `../worked-pairing-examples/findings.md`); the built site's card already has a meeting-recording link, whose resolution this work did not check (unverified).
- The mockups' phone behaviour (stacking, ledger turned to blocks, the opened row) was written from the CSS and not seen on a screen (unverified).
- The reading-order counts treat text order in the page as order on a phone and ignore line wraps and the heights of boxes (unverified as a measure of scrolling).
- Card 6's three filer lines are copied from the worked pairings' table of form 496 reports (stance, filing ids and dates as filed there); the figures were not re-queried here, and the data on file has no filing dates for the individual rows beyond the first and last filed.
