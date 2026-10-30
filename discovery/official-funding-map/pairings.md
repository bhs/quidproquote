# Pairings from the money: five San Francisco officials, a donor's own words and the money through committees tied to the official

Written by `python build_map.py` from `data/` (transcripts, donor statements, money snapshot retrieved 2026-10-30). Each pairing starts from money a donor family gave through a committee tied to the official; it then shows the official's exact caption words on a subject the donor's own page speaks to. Two things shown side by side for a reader to check. Nothing here says why anyone said or gave anything, and the order of the dates is not an explanation.

| # | Official | Words (meeting, stamp) | Donor | Schedule A to committees tied to the official |
|---|---|---|---|---|
| 1 | Daniel Lurie | Board of Supervisors 2026-07-14, 00:03:46 | San Francisco Chamber of Commerce | $499,000 Mayor Lurie's Yes on H Committee |
| 2 | Daniel Lurie | Board of Supervisors 2026-07-14, 00:04:36 | San Francisco Police Officers Association | $10,000 Mayor Lurie's Yes on D, E & F Committee |
| 3 | Matt Dorsey | Board of Supervisors 2026-07-14, 01:47:19 | San Francisco Police Officers Association | $500 Matt Dorsey for Supervisor 2022, $7,500 Matt Dorsey for DCCC Member 2024 Officeholder Committee |
| 4 | Bilal Mahmood | Budget and Finance Committee 2026-07-15, 02:52:31 | Govern For California | $10,500 Bilal Mahmood for DCCC Member 2024, $7,500 Bilal Mahmood for Supervisor 2024 |
| 5 | Shamann Walton | Board of Supervisors 2026-07-14, 02:39:58 | SEIU Local 1021 | $500 Shamann Walton for School Board 2014, $500 Committee to Elect Shamann Walton for SF Board of Education 2012 |

## Pairing 1: Daniel Lurie and San Francisco Chamber of Commerce on Muni and the Prop H parcel tax

### 1.1 The official's words, as the city's caption transcript publishes them

> MUNI WEEKEND RIDERSHIP SURPASSED PRE-PANDEMIC LEVELS FOR THE FIRST TIME AS OF SFO RECORDED ITS BUSIEST MEMORIAL DAY WEEKEND EVER AND HALF A MILLION MORE TOURISTS ARE PROJECTED TO COME TO OUR CITY THIS YEAR THAN IN 2025.

- Meeting: Board of Supervisors, 2026-07-14. Transcript time: 00:03:46 to 00:03:59 (caption stamps from the start of the recording).
- Transcript: <https://sfgov.legistar.com/Transcript.aspx?ID1=52849> (Legistar caption transcript, retrieved 2026-10-29). Wording is the transcript's; it was not checked against the recording.
- Speaker named: **Daniel Lurie**, Mayor.

### 1.2 How the transcript supports that credit

- Caption row `00:02:15`: >> YES. THE SPECIAL ORDER AT 2 P.M. IS
- Caption row `00:02:16`: THE APPEARANCE BY THE HONORABLE MAYOR DANIEL LURIE TO DISCUSS
- Caption row `00:02:28`: >> WELCOME, MR. MAYOR. DO YOU HAVE ANY OPENING
- Caption row `00:02:31`: REMARKS? I DO.
- Caption row `00:06:11`: >> THANK YOU, MAYOR LURIE. MADAM CLERK, PLEASE CALL THE
- What the transcript shows: The clerk reads the special order as 'THE APPEARANCE BY THE HONORABLE MAYOR DANIEL LURIE' (00:02:16); the presiding officer says 'WELCOME, MR. MAYOR. DO YOU HAVE ANY OPENING REMARKS?' and the answer is 'I DO.' (00:02:28 to 00:02:31); the remarks begin 'GOOD AFTERNOON. BOARD PRESIDENT ... AND MEMBERS OF THE BOARD OF SUPERVISORS' and the presiding officer closes them with 'THANK YOU, MAYOR LURIE.' (00:06:11). The quoted rows sit inside that unbroken turn, between 00:02:34 and 00:06:06.
- Doubt in the credit: **low**. The transcript itself names the speaker as the Mayor before and after the turn; only the captions' rendering of the Board President's name ('MANAGEMENT') is garbled. The roster has one Mayor.

### 1.3 The donor's priority in its own words

> Prop H would introduce a parcel tax from 2027-2042 to assist in funding San Francisco Municipal Transportation Agency operations. The anticipated revenue generated from this tax would be about $177 million. The Chamber supports Prop H as public transit is a critical driver of the San Francisco economy, helping workers, residents, and businesses stay connected.

- San Francisco Chamber of Commerce. Section: Proposition H - Parcel Tax to Fund Public Muni Operations. Page type: voter guide on the organisation's own site, page dated 2026-10-08. Source: <https://sfchamber.com/november-2026-voter-guide/>. Retrieved 2026-10-30.

### 1.4 Why these two sit side by side

- Overlap (my reading): Same subject: Muni. The Mayor's words report Muni weekend ridership; the Chamber's statement is its position on the Muni parcel tax (Prop H).
- Positions (my reading): Different kinds of statement: the Mayor's sentence reports ridership and does not mention Prop H; the Chamber's statement supports Prop H. No agreement or disagreement is claimed. (My reading.)

### 1.5 The money, by committee and filing

Money read from the Ethics Commission's Transactions dataset on DataSF (https://data.sf.gov/d/pitq-e56w), data loaded through 2026-10-30, retrieved 2026-10-30. Contributor names as filed: San Francisco Forward sponsored by San Francisco Chamber of Commerce. FPPC ids carried by those rows: 891575.
How the committee is recognised as the organisation's: the id resolves in the Filers dataset to 'SF FORWARD SPONSORED BY THE SAN FRANCISCO CHAMBER OF COMMERCE'.

The committee that received the money is 'Mayor Lurie's Yes on H Committee', a ballot-measure committee carrying the Mayor's name; its purpose in the Ethics Commission's portal is 'organized to support Measure H: Parcel Tax to Fund Public Muni Operations'.

**Mayor Lurie's Yes on H Committee** (filer 214099226; ballot-measure committee carrying the official's name; status ACTIVE)

| Kind | Contribution date | Filing id (version) | Filing date | Amount | Giver as filed |
|---|---|---|---|---|---|
| Schedule A | 2026-03-09 | 216870148 (v3) | 2026-06-09 | $10,000 | San Francisco Forward sponsored by San Francisco Chamber of Commerce |
| Schedule A | 2026-05-26 | 216863528 (v1) | 2026-06-05 | $50,000 | San Francisco Forward sponsored by San Francisco Chamber of Commerce |
| Schedule A | 2026-09-15 | 217514736 (v1) | 2026-09-24 | $225,000 | San Francisco Forward sponsored by San Francisco Chamber of Commerce |
| Schedule A | 2026-09-23 | 217719664 (v1) | 2026-10-22 | $214,000 | San Francisco Forward sponsored by San Francisco Chamber of Commerce |
| 24-hour report repeating a Schedule A row (not counted) | 2026-09-15 | 217439436 (v1) | 2026-09-16 | $225,000 | San Francisco Forward sponsored by San Francisco Chamber of Commerce |
| 24-hour report repeating a Schedule A row (not counted) | 2026-09-23 | 217504132 (v1) | 2026-09-24 | $214,000 | San Francisco Forward sponsored by San Francisco Chamber of Commerce |

Schedule A total for this committee: **$499,000** in 4 rows.

Not added across committees: a total over committees would join money received by different committees. The per-committee Schedule A totals above are the figures to quote.

Outside spending apart: no form 496 report naming this official was filed by a committee the family's names take.

### 1.6 What this does not say

Two things shown side by side for a reader to check. Nothing here says why anyone said or gave anything, and the order of the dates is not an explanation.
The family is read from names as filed. 'San Francisco Forward sponsored by San Francisco Chamber of Commerce' is a committee that names the Chamber as sponsor; the bare name 'SF Forward' carries no sponsor in the filing name. A reader should confirm each is the organisation.

## Pairing 2: Daniel Lurie and San Francisco Police Officers Association on The city budget and the general fund

### 2.1 The official's words, as the city's caption transcript publishes them

> I'M CONFIDENT THAT THE UPCOMING BUDGET WILL BUILD ON THE PROGRESS WE'VE ALREADY MADE. AMID FEDERAL CUTS WE ARE STRENGTHENING OUR SOCIAL SAFETY NET SO SAN FRANCISCANS KNOW THEY CAN COUNT ON THIS CITY. THE BUDGET MAINTAINS HEALTH CARE AND FOOD ASSISTANCE INVESTS IN PREVENTING INDIVIDUALS AND FAMILIES FROM FALLING INTO HOMELESSNESS AND PROTECTS CORE SERVICES THAT KEEPS OUR STREETS SAFE AND CLEAN. AND WE ARE ALSO ON TRACK TO CLOSE A $642 MILLION DEFICIT.

- Meeting: Board of Supervisors, 2026-07-14. Transcript time: 00:04:36 to 00:05:01 (caption stamps from the start of the recording).
- Transcript: <https://sfgov.legistar.com/Transcript.aspx?ID1=52849> (Legistar caption transcript, retrieved 2026-10-29). Wording is the transcript's; it was not checked against the recording.
- Speaker named: **Daniel Lurie**, Mayor.

### 2.2 How the transcript supports that credit

- Caption row `00:02:15`: >> YES. THE SPECIAL ORDER AT 2 P.M. IS
- Caption row `00:02:16`: THE APPEARANCE BY THE HONORABLE MAYOR DANIEL LURIE TO DISCUSS
- Caption row `00:02:28`: >> WELCOME, MR. MAYOR. DO YOU HAVE ANY OPENING
- Caption row `00:02:31`: REMARKS? I DO.
- Caption row `00:06:11`: >> THANK YOU, MAYOR LURIE. MADAM CLERK, PLEASE CALL THE
- What the transcript shows: As for pairing 1: the clerk announces 'THE APPEARANCE BY THE HONORABLE MAYOR DANIEL LURIE' (00:02:16), the presiding officer asks 'DO YOU HAVE ANY OPENING REMARKS?' and the answer is 'I DO.' (00:02:28 to 00:02:31), and 'THANK YOU, MAYOR LURIE.' closes the turn (00:06:11). The quoted rows (00:04:36 to 00:05:01) are inside it.
- Doubt in the credit: **low**. The transcript names the speaker as the Mayor on both sides of the turn.

### 2.3 The donor's priority in its own words

> The timing of the special-interest led Proposition I could not be worse. San Francisco is in the middle of its most aggressive first-responder hiring push in years.

- San Francisco Police Officers Association. Section: Mayor Lurie Joined by Firefighters and Police Officers in Strong Opposition to Proposition I. Page type: article by the association's president, on its own site, page dated 2026-09-01. Source: <https://sfpoa.org/mayor-lurie-joined-by-firefighters-and-police-officers-in-strong-opposition-to-proposition-i/>. Retrieved 2026-10-30.

> "We are finally turning the corner on staffing after years of losing officers, and this is exactly the wrong moment to drain the fund that's paying for that comeback," said Louis Wong, President of the San Francisco Police Officers Association.

- San Francisco Police Officers Association. Section: Quoted words of SFPOA President Louis Wong. Page type: article by the association's president, on its own site, page dated 2026-09-01. Source: <https://sfpoa.org/mayor-lurie-joined-by-firefighters-and-police-officers-in-strong-opposition-to-proposition-i/>. Retrieved 2026-10-30.

### 2.4 Why these two sit side by side

- Overlap (my reading): Same subject: the city's budget and what it pays for. The Mayor describes the coming budget, core services and the deficit; the association's page is about the general fund that pays for police officers and firefighters.
- Positions (my reading): No position of the Mayor on a measure is in the quote, and the association's statement is about Proposition I, which the quote does not name. The association's page also reports the Mayor opposing Proposition I (a different occasion, August 2026). (My reading.)

### 2.5 The money, by committee and filing

Money read from the Ethics Commission's Transactions dataset on DataSF (https://data.sf.gov/d/pitq-e56w), data loaded through 2026-10-30, retrieved 2026-10-30. Contributor names as filed: San Francisco Police Officers Association Issues PAC. FPPC ids carried by those rows: 1317554.
How the committee is recognised as the organisation's: the id resolves in the Filers dataset to 'San Francisco Police Officers Association Issues PAC'.

The committee that received the money is 'Mayor Lurie's Yes on D, E & F Committee', a ballot-measure committee carrying the Mayor's name; its purpose in the Ethics Commission's portal is 'organized to support Measures D, E, and F'.

**Mayor Lurie's Yes on D, E & F Committee** (filer 216006060; ballot-measure committee carrying the official's name; status ACTIVE)

| Kind | Contribution date | Filing id (version) | Filing date | Amount | Giver as filed |
|---|---|---|---|---|---|
| Schedule A | 2026-08-27 | 217516412 (v1) | 2026-09-24 | $10,000 | San Francisco Police Officers Association Issues PAC |
| 24-hour report repeating a Schedule A row (not counted) | 2026-08-27 | 217307118 (v1) | 2026-08-28 | $10,000 | San Francisco Police Officers Association Issues PAC |

Schedule A total for this committee: **$10,000** in 1 rows.

Not added across committees: a total over committees would join money received by different committees. The per-committee Schedule A totals above are the figures to quote.

Outside spending apart: no form 496 report naming this official was filed by a committee the family's names take.

### 2.6 What this does not say

Two things shown side by side for a reader to check. Nothing here says why anyone said or gave anything, and the order of the dates is not an explanation.
The family is read from names as filed. The association's PAC and its Issues PAC are the association's own committees. A reader should confirm each is the organisation.

## Pairing 3: Matt Dorsey and San Francisco Police Officers Association on The inclusionary housing fee vote and the Prop C package

### 3.1 The official's words, as the city's caption transcript publishes them

> COLLEAGUES, I WILL RESPECTFULLY BE VOTING NO ON THE PROPOSED AMENDMENT WHILE WE ULTIMATELY HAVE THE FINAL POLICY DECISION OVER OUR INCLUSIONARY RATES. WE GENERALLY ENTRUST THE BULK OF THE POLICYMAKING WORK ON OUR INCLUSIONARY RATES TO A GROUP OF EXPERTS FROM THE DEVELOPMENT AND AFFORDABLE HOUSING COMMUNITY. THEY LOOK AT THE DATA AND PROVIDE US WITH RECOMMENDATIONS. AS LAND USE CHAIR MELGAR JUST EXPLAINED. AND THIS TIME AROUND THE NUMBERS SHOWED THAT OUR RATES ARE TOO HIGH AND IN FACT THE REPORT SHOWED THAT THE EVEN ZERO IS INFEASIBLE. WHILE I FRANKLY HAVE RESERVATIONS EVEN ABOUT 5%, I RESPECT THE PROCESS THAT LED TO THAT RECOMMENDATION AND I UNDERSTAND THE DESIRE AND THE IMPORTANCE OF HAVING A NUMBER THAT'S GREATER THAN ZERO. BUT I DO BELIEVE WE NEED TO TRUST THE MATH. I DON'T BELIEVE WE SHOULD SINGLE OUT NEIGHBORHOODS AND FREEZE THEM OUT FOR NEW HOUSING MARKET RATE OR AFFORDABLE. IT TAKES TIME TO SEE THE EFFECTS OF THESE CHANGES AND THAT'S WHY THE TAX PROCESS HAPPENS EVERY THREE YEARS. I BELIEVE WE NEED TO LET THIS POLICY PLAY OUT SO I WILL RESPECTFULLY NOT SUPPORT THE AMENDMENT ON THE PRINCIPLE THAT IT RISKS MOVING THE LEGISLATION FURTHER FROM ITS GOAL OF MAKING HOUSING PRODUCTION FEASIBLE.

- Meeting: Board of Supervisors, 2026-07-14. Transcript time: 01:47:19 to 01:48:25 (caption stamps from the start of the recording).
- Transcript: <https://sfgov.legistar.com/Transcript.aspx?ID1=52849> (Legistar caption transcript, retrieved 2026-10-29). Wording is the transcript's; it was not checked against the recording.
- Speaker named: **Matt Dorsey**, Supervisor, District 6.

### 3.2 How the transcript supports that credit

- Caption row `01:47:12`: MATH SUPPORTS IT. >> THANK YOU.
- Caption row `01:47:15`: SUPERVISOR DORSEY THANK YOU PRESIDENT MANDOLIN.
- Caption row `01:48:28`: >> SUPERVISOR CHEN. THANK YOU MR. PRESIDENT.
- What the transcript shows: The row at 01:47:15 opens the turn with the member's name, spelled correctly: 'SUPERVISOR DORSEY THANK YOU PRESIDENT MANDOLIN.' (the Board President's name is garbled). The next turn opens at 01:48:28 with 'SUPERVISOR CHEN. THANK YOU MR. PRESIDENT.' The speaker refers to the land use chair in the third person ('AS LAND USE CHAIR MELGAR JUST EXPLAINED'), so is not Melgar.
- Doubt in the credit: **low**. Name spelled correctly in the cue that opens the turn, and the next speaker is named.

### 3.3 The donor's priority in its own words

> San Francisco Firefighters Local 798, SFPOA, and Mayor Lurie urge San Franciscans to vote NO on Proposition I and YES on Proposition C this November - and to protect the budget that keeps this city safe.

- San Francisco Police Officers Association. Section: Closing paragraph. Page type: article by the association's president, on its own site, page dated 2026-09-01. Source: <https://sfpoa.org/mayor-lurie-joined-by-firefighters-and-police-officers-in-strong-opposition-to-proposition-i/>. Retrieved 2026-10-30.

### 3.4 Why these two sit side by side

- Overlap (my reading): Same package: the Board's 14 July vote to cut the inclusionary housing fee, which the speaker before Dorsey ties to the Housing Trust Fund expansion ('SIT ON TOP OF THE HOUSING TRUST FUND THAT HAS BEEN EXPANDED SO THAT WE HAVE BOTH', 01:46:56 to 01:47:00); the association's page urges a Yes vote on Prop C, the Housing Trust Fund measure. The quote itself does not name Prop C.
- Positions (my reading): Not comparable on the text: the quote explains a vote on an amendment to the fee ordinance; the association's statement is a vote recommendation on a ballot measure. (My reading.)

### 3.5 The money, by committee and filing

Money read from the Ethics Commission's Transactions dataset on DataSF (https://data.sf.gov/d/pitq-e56w), data loaded through 2026-10-30, retrieved 2026-10-30. Contributor names as filed: SAN FRANCISCO POLICE OFFICERS ASSOCIATION PAC. FPPC ids carried by those rows: 1315969.
How the committee is recognised as the organisation's: the id resolves in the Filers dataset to 'San Francisco Police Officers Association PAC'.

The committees that received the money are the Supervisor's own: his 2022 supervisor committee and his 2024 officeholder committee (named 'Matt Dorsey for DCCC Member 2024 Officeholder Committee').

**Matt Dorsey for Supervisor 2022** (filer 203924838; own committee for Supervisor; status TERMINATED)

| Kind | Contribution date | Filing id (version) | Filing date | Amount | Giver as filed |
|---|---|---|---|---|---|
| Schedule A | 2024-04-01 | 211830580 (v1) | 2024-07-31 | $500 | SAN FRANCISCO POLICE OFFICERS ASSOCIATION PAC |

Schedule A total for this committee: **$500** in 1 rows.

**Matt Dorsey for DCCC Member 2024 Officeholder Committee** (filer 208697921; own committee for another office (Democratic County Central Committee); status ACTIVE)

| Kind | Contribution date | Filing id (version) | Filing date | Amount | Giver as filed |
|---|---|---|---|---|---|
| Schedule A | 2024-01-30 | 210655135 (v1) | 2024-02-22 | $2,500 | SAN FRANCISCO POLICE OFFICERS ASSOCIATION PAC |
| Schedule A | 2025-05-27 | 214607150 (v1) | 2025-07-31 | $2,500 | SAN FRANCISCO POLICE OFFICERS ASSOCIATION PAC |
| Schedule A | 2026-04-23 | 217134003 (v1) | 2026-07-31 | $2,500 | SAN FRANCISCO POLICE OFFICERS ASSOCIATION PAC |
| 24-hour report repeating a Schedule A row (not counted) | 2024-01-30 | 209998325 (v1) | 2024-01-31 | $2,500 | SAN FRANCISCO POLICE OFFICERS ASSOCIATION PAC |

Schedule A total for this committee: **$7,500** in 3 rows.

Not added across committees: a total over committees would join money received by different committees. The per-committee Schedule A totals above are the figures to quote.

Outside spending apart: no form 496 report naming this official was filed by a committee the family's names take.

### 3.6 What this does not say

Two things shown side by side for a reader to check. Nothing here says why anyone said or gave anything, and the order of the dates is not an explanation.
The family is read from names as filed. The association's PAC and its Issues PAC are the association's own committees. A reader should confirm each is the organisation.

## Pairing 4: Bilal Mahmood and Govern For California on Prop J, the foreclosure exemption in the transfer tax

### 4.1 The official's words, as the city's caption transcript publishes them

> THIS MEASURE GIVES SAN FRANCISCO VOTERS THE OPPORTUNITY TO DECIDE WHETHER A TRANSFER TAX CODE SHOULD REFLECT THE WAY TODAY'S REAL ESTATE MARKET OPERATES RATHER THAN THE MARKET THAT EXISTED DECADES AGO.

- Meeting: Budget and Finance Committee, 2026-07-15. Transcript time: 02:52:31 to 02:52:42 (caption stamps from the start of the recording).
- Transcript: <https://sfgov.legistar.com/Transcript.aspx?ID1=52853> (Legistar caption transcript, retrieved 2026-10-29). Wording is the transcript's; it was not checked against the recording.
- Speaker named: **Bilal Mahmood**, Supervisor, District 5.

### 4.2 How the transcript supports that credit

- Caption row `02:52:22`: >> MADAM CHAIR, THANK YOU AND TODAY WE HAVE SUPERVISOR
- Caption row `02:52:27`: BALA MAMU HERE. >> WELCOME TO THE CHAMBER.
- Caption row `02:52:30`: >> THANK YOU CHAIR CHIN AND THANK YOU COLLEAGUES AS
- Caption row `02:53:17`: CONVERSATION. I WANT TO THANK MY CO SPONSORS
- Caption row `02:53:21`: SUPERVISOR DORSEY MELGAR, CHEN WANG AND WALTON FOR STANDING
- What the transcript shows: The chair is told at 02:52:22 'TODAY WE HAVE SUPERVISOR' and the next row reads 'BALA MAMU HERE'; the captions render the name phonetically. The speaker then thanks 'MY CO SPONSORS SUPERVISOR DORSEY MELGAR, CHEN WANG AND WALTON' (02:53:17 to 02:53:24), naming others and not himself. The text alone does not spell the surname; the credit rests on the sponsor record outside the transcript.
- Doubt in the credit: **high**. No caption cue spells the speaker's surname. Two pages read on 2026-10-30 name Supervisor Mahmood as the measure's introducer, which the sponsor list in the speaker's thanks fits.
- Outside the transcript (read 2026-10-30): <https://www.sfpublicpress.org/proposition-j-would-close-tax-loophole-on-large-foreclosed-properties/>: San Francisco Public Press says Mayor Lurie and Supervisor Bilal Mahmood introduced Proposition J.
- Outside the transcript (read 2026-10-30): <https://growsf.org/voter-guide/san-francisco-voter-guide-november-2026-election/measures/prop-j/>: GrowSF's page for Prop J lists the sponsors as Supervisor Mahmood, joined by Supervisors Dorsey, Melgar, Chen, Wong, Walton and Mandelman.

### 4.3 The donor's priority in its own words

> San Francisco's commercial real estate market is already under tremendous stress, and adding transfer taxes to foreclosures and distressed property workouts would make matters worse. The city should be encouraging capital to return to its struggling real estate market, not making it more expensive to invest.

- Govern For California. Section: Proposition J, Foreclosure Transfer Tax: NO. Page type: voter guide on the organisation's own site, page dated 2026-10-21. Source: <https://www.governforcalifornia.org/news/2026/10/21/sf-voter-guide>. Retrieved 2026-10-30.

### 4.4 Why these two sit side by side

- Overlap (my reading): Same measure: Prop J, the foreclosure exemption in the real property transfer tax.
- Positions (my reading): Different positions on the text: the quote presents the measure as bringing the transfer tax code up to date; the donor's page says NO on Prop J. (My reading of the quote; the donor's side is its own words.)

### 4.5 The money, by committee and filing

Money read from the Ethics Commission's Transactions dataset on DataSF (https://data.sf.gov/d/pitq-e56w), data loaded through 2026-10-30, retrieved 2026-10-30. Contributor names as filed: GFC COURAGE COMMITTEE - BAY AREA CHAPTER; GFC COURAGE COMMITTEE - CALIFORNIA BUSINESS COALITION; GFC COURAGE COMMITTEE - COMMON SENSE CHAPTER; GFC COURAGE COMMITTEE - EAST BAY CHAPTER; GFC COURAGE COMMITTEE - EXCELLENCE IN EDUCATION CHAPTER; GFC COURAGE COMMITTEE - FUTURE GENERATIONS CHAPER; GFC COURAGE COMMITTEE - GOLDEN GATE CHAPTER; GFC COURAGE COMMITTEE - MARIN CHAPTER; GFC COURAGE COMMITTEE - PALO ALTO CHAPTER; GFC COURAGE COMMITTEE - SAN FRANCISCO CHAPTER; GFC COURAGE COMMITTEE - SANTA BARBARA CHAPTER; GFC COURAGE COMMITTEE - SANTA CRUZ CHAPTER; GFC COURAGE COMMITTEE - SIERRA CHAPTER; GFC COURAGE COMMITTEE - SOUTHERN CALIFORNIA CHAPTER; GOVERN FOR CALIFORNIA COURAGE COMMITTEE. FPPC ids carried by those rows: 1392639, 1416422, 1416434, 1416436, 1416438, 1416440, 1416442, 1420855, 1423911, 1423919, 1424659, 1425929, 1435804, 1435894.
How the giver is recognised as the organisation's: by the name as filed alone (the FPPC ids above do not resolve in the Filers dataset, which holds only committees registered with the San Francisco Ethics Commission).

The committees that received the money are the Supervisor's own: his 2024 supervisor committee and his 2024 committee for the Democratic County Central Committee (another office).

**Bilal Mahmood for DCCC Member 2024** (filer 208655996; own committee for another office (Democratic County Central Committee); status TERMINATED)

| Kind | Contribution date | Filing id (version) | Filing date | Amount | Giver as filed |
|---|---|---|---|---|---|
| Schedule A | 2024-01-29 | 210655413 (v1) | 2024-02-22 | $1,000 | GFC COURAGE COMMITTEE - EAST BAY CHAPTER |
| Schedule A | 2024-01-29 | 210655413 (v1) | 2024-02-22 | $1,500 | GFC COURAGE COMMITTEE - BAY AREA CHAPTER |
| Schedule A | 2024-01-29 | 210655413 (v1) | 2024-02-22 | $5,000 | GFC COURAGE COMMITTEE - SAN FRANCISCO CHAPTER |
| Schedule A | 2024-02-06 | 210655413 (v1) | 2024-02-22 | $3,000 | GFC COURAGE COMMITTEE - SIERRA CHAPTER |
| 24-hour report repeating a Schedule A row (not counted) | 2024-01-29 | 209936092 (v1) | 2024-01-30 | $1,500 | GFC COURAGE COMMITTEE - BAY AREA CHAPTER |
| 24-hour report repeating a Schedule A row (not counted) | 2024-01-29 | 209936092 (v1) | 2024-01-30 | $1,000 | GFC COURAGE COMMITTEE - EAST BAY CHAPTER |
| 24-hour report repeating a Schedule A row (not counted) | 2024-01-29 | 209936092 (v1) | 2024-01-30 | $5,000 | GFC COURAGE COMMITTEE - SAN FRANCISCO CHAPTER |
| 24-hour report repeating a Schedule A row (not counted) | 2024-02-06 | 210411535 (v1) | 2024-02-07 | $3,000 | GFC COURAGE COMMITTEE - SIERRA CHAPTER |

Schedule A total for this committee: **$10,500** in 4 rows.

**Bilal Mahmood for Supervisor 2024** (filer 209865652; own committee for Supervisor; status ACTIVE)

| Kind | Contribution date | Filing id (version) | Filing date | Amount | Giver as filed |
|---|---|---|---|---|---|
| Schedule A | 2024-05-01 | 213049667 (v2) | 2025-01-31 | $500 | GFC COURAGE COMMITTEE - SAN FRANCISCO CHAPTER |
| Schedule A | 2024-05-01 | 213049667 (v2) | 2025-01-31 | $500 | GFC COURAGE COMMITTEE - SANTA CRUZ CHAPTER |
| Schedule A | 2024-05-01 | 213049667 (v2) | 2025-01-31 | $500 | GFC COURAGE COMMITTEE - SIERRA CHAPTER |
| Schedule A | 2024-05-01 | 213049667 (v2) | 2025-01-31 | $500 | GFC COURAGE COMMITTEE - PALO ALTO CHAPTER |
| Schedule A | 2024-05-01 | 213049667 (v2) | 2025-01-31 | $500 | GFC COURAGE COMMITTEE - BAY AREA CHAPTER |
| Schedule A | 2024-05-01 | 213049667 (v2) | 2025-01-31 | $500 | GFC COURAGE COMMITTEE - GOLDEN GATE CHAPTER |
| Schedule A | 2024-05-10 | 213049667 (v2) | 2025-01-31 | $500 | GFC COURAGE COMMITTEE - CALIFORNIA BUSINESS COALITION |
| Schedule A | 2024-05-16 | 213049667 (v2) | 2025-01-31 | $500 | GFC COURAGE COMMITTEE - COMMON SENSE CHAPTER |
| Schedule A | 2024-08-16 | 213049699 (v2) | 2025-01-31 | $500 | GFC COURAGE COMMITTEE - MARIN CHAPTER |
| Schedule A | 2024-08-19 | 213049699 (v2) | 2025-01-31 | $500 | GFC COURAGE COMMITTEE - FUTURE GENERATIONS CHAPER |
| Schedule A | 2024-08-20 | 213049699 (v2) | 2025-01-31 | $500 | GFC COURAGE COMMITTEE - SOUTHERN CALIFORNIA CHAPTER |
| Schedule A | 2024-08-26 | 213049699 (v2) | 2025-01-31 | $500 | GFC COURAGE COMMITTEE - EXCELLENCE IN EDUCATION CHAPTER |
| Schedule A | 2024-08-26 | 213049699 (v2) | 2025-01-31 | $500 | GFC COURAGE COMMITTEE - SANTA BARBARA CHAPTER |
| Schedule A | 2024-08-26 | 213049699 (v2) | 2025-01-31 | $500 | GFC COURAGE COMMITTEE - EAST BAY CHAPTER |
| Schedule A | 2024-09-26 | 212414131 (v1) | 2024-10-24 | $500 | GOVERN FOR CALIFORNIA COURAGE COMMITTEE |

Schedule A total for this committee: **$7,500** in 15 rows.

Not added across committees: a total over committees would join money received by different committees. The per-committee Schedule A totals above are the figures to quote.

Outside spending apart: no form 496 report naming this official was filed by a committee the family's names take.

### 4.6 What this does not say

Two things shown side by side for a reader to check. Nothing here says why anyone said or gave anything, and the order of the dates is not an explanation.
The family is read from names as filed. The 'GFC Courage Committee' chapters are tied to Govern For California by the organisation's own pages, by press and by third-party records of the state filings, not by a registration read here. (1) Its 'Who We Are' page lists its independent political action committee chapters (Statewide, SF Public Schools, Southern California, Housing For Californians, San Francisco, Peninsula South Bay, East Bay) and its footer names 'Govern For California, a registered 501(c)(4) non-profit organization' (<https://www.governforcalifornia.org/who-we-are>, read 2026-10-30); its San Francisco voter guide says it was put together by 'GFC's San Francisco Chapter' (<https://www.governforcalifornia.org/news/2026/10/21/sf-voter-guide>). (2) Mission Local reported in 2024 that Govern for California gave $500 each to supervisor candidates through eight chapters, and that a complaint to the Ethics Commission alleged the payments came from one legal entity, which is an allegation and not a finding (<https://missionlocal.org/2024/09/s-f-ethics-complaint-targets-govern-for-california-group-that-bundles-political-donations/>). (3) Transparency USA's record of the state Govern for California Network Committee (id 1383984) lists payments to the San Francisco, Sierra, California Business Coalition, Palo Alto, Marin, Excellence in Education, Bay Area, Southern California and Golden Gate chapter committees (<https://www.transparencyusa.org/ca/committee/govern-for-california-network-committee-1383984-rcp>). (4) CalMatters' Digital Democracy lists chapter committee names, including Santa Cruz, Santa Barbara, Future Generations and Common Sense, under the organisation Govern for California (<https://calmatters.digitaldemocracy.org/organizations/-15028>). The chapter committees are state committees: the Ethics Commission's list of active committees for the 2 June 2026 election shows them as state-level committees with Cal-Access ids that match the ids on the filed rows (for example 1416440, the San Francisco chapter; <https://campaign.sfethics.org/elections/2026-06-02/committees/CA1433436>), but their Cal-Access registrations (Form 410), which name the sponsor, were not read, so the tie for each chapter rests on (1) to (4) and the name. A reader should confirm each is the organisation.

## Pairing 5: Shamann Walton and SEIU Local 1021 on The Mayor's three charter measures (Props D, E and F)

### 5.1 The official's words, as the city's caption transcript publishes them

> COLLEAGUES I AM ALSO REQUESTING THE BUDGET AND LEGISLATIVE ANALYSTS TO INTERPRET CLEARLY ANALYZE THE ECONOMIC IMPACT OF THE CHARTER REFORM MEASURES PROPOSED BY MAYOR LURIE THAT ARE CURRENTLY UNDERGOING THE SIGNATURE VERIFICATION PROCESS AT THE DEPARTMENT OF ELECTIONS. SAN FRANCISCO VOTERS ARE BEING ASKED TO DECIDE ON THREE CHARTER REFORM MEASURES THIS NOVEMBER THAT WERE FUNDAMENTAL RESTRUCTURE HOW THE CITY OPERATES INCLUDING A SPENDING MAYORAL HIRING AND FIRING AUTHORITY AS WELL AS REORGANIZATION POWER. EXTENDING THE CITY ADMINISTRATOR'S TERM TO TEN YEARS WHILE GIVING THAT OFFICE SO AUTHORITY OVER PROCUREMENT. AND RAISING THE SIGNATURE THRESHOLD FOR CITIZEN INITIATIVES FROM 2% TO 8%. >> THESE ARE NOT SMALL TECHNICAL FIXES. THEY SHIFT REAL POWER AWAY FROM THE BOARD OF SUPERVISORS INDEPENDENT COMMISSIONS AND FROM THE RESIDENTS OF SAN FRANCISCO.

- Meeting: Board of Supervisors, 2026-07-14. Transcript time: 02:39:58 to 02:40:56 (caption stamps from the start of the recording).
- Transcript: <https://sfgov.legistar.com/Transcript.aspx?ID1=52849> (Legistar caption transcript, retrieved 2026-10-29). Wording is the transcript's; it was not checked against the recording.
- Speaker named: **Shamann Walton**, Supervisor, District 10.

### 5.2 How the transcript supports that credit

- Caption row `02:36:50`: YOU. SUPERVISOR WALTON THANK YOU,
- Caption row `02:36:56`: INTRODUCING A RESOLUTION AND ALSO A BILL A REQUEST.
- Caption row `02:37:05`: CONTINUING THE BABY'S SHADOW. >> DISTRICT TEN RESIDENTS
- Caption row `02:38:45`: EMPOWERMENT. AS MANY OF YOU KNOW, DISTRICT
- Caption row `02:38:49`: TEN WILL SOON FACE ADDITIONAL TRANSPORTATION CHALLENGES AS
- Caption row `02:39:46`: RESOLUTION. I ALSO WANT TO THANK MY
- Caption row `02:39:54`: WELL AS SUPERVISOR FIELDER FOR THE EARLY CO-SPONSORSHIP.
- Caption row `02:42:48`: THE REST I SUBMIT. >> THANK YOU.
- What the transcript shows: Walton is called at 02:36:50 ('SUPERVISOR WALTON THANK YOU, MADAM CLERK'), says 'I AM INTRODUCING A RESOLUTION AND ALSO A BILL A REQUEST', and the request here is the 'also'. The remarks say 'DISTRICT TEN RESIDENTS' and 'DISTRICT TEN WILL SOON FACE' (District 10 is Walton on the roster) and thank 'SUPERVISOR CHEN AS WELL AS SUPERVISOR FIELDER', so the speaker is neither of those. The chair moves on at 02:42:48 ('THE REST I SUBMIT ... SUPERVISOR WALTON').
- Doubt in the credit: **low**. No name cue directly before the passage (the cue is three minutes earlier, with '>>' marks between); the speaker's own 'District Ten' and the chair's closing agree with Walton.

### 5.3 The donor's priority in its own words

> Proposition D - Changes to Ballot Measure Process - Vote NO

- SEIU Local 1021. Section: San Francisco, local ballot measures. Page type: endorsement list on the organisation's own site, page dated 2026-09-28. Source: <https://www.seiu1021.org/post/election-endorsements-nov-3-2026>. Retrieved 2026-10-30.

> Proposition E - City Administrator's Authority and Changes to City Contracting - Vote NO

- SEIU Local 1021. Section: San Francisco, local ballot measures. Page type: endorsement list on the organisation's own site, page dated 2026-09-28. Source: <https://www.seiu1021.org/post/election-endorsements-nov-3-2026>. Retrieved 2026-10-30.

> Proposition F - Changes to Executive Branch Management - Vote NO

- SEIU Local 1021. Section: San Francisco, local ballot measures. Page type: endorsement list on the organisation's own site, page dated 2026-09-28. Source: <https://www.seiu1021.org/post/election-endorsements-nov-3-2026>. Retrieved 2026-10-30.

> Each election, SEIU 1021 members endorse candidates who will stand with us as we fight to win strong contracts and protect working standards.

- SEIU Local 1021. Section: Election Endorsements: Nov 3, 2026. Page type: endorsement list on the organisation's own site, page dated 2026-09-28. Source: <https://www.seiu1021.org/post/election-endorsements-nov-3-2026>. Retrieved 2026-10-30.

### 5.4 Why these two sit side by side

- Overlap (my reading): Same measures: the quote names 'THE CHARTER REFORM MEASURES PROPOSED BY MAYOR LURIE' (a spending ... mayoral hiring and firing authority, the City Administrator's term and procurement, and the signature threshold for initiatives); the union's page lists Props D, E and F with a recommendation on each.
- Positions (my reading): The quote asks for a cost analysis and says the measures 'SHIFT REAL POWER AWAY FROM THE BOARD OF SUPERVISORS'; the union's page says Vote NO on each. Both are critical of the measures on their face. (My reading.)

### 5.5 The money, by committee and filing

Money read from the Ethics Commission's Transactions dataset on DataSF (https://data.sf.gov/d/pitq-e56w), data loaded through 2026-10-30, retrieved 2026-10-30. Contributor names as filed: SEIU Local 1021; Service Employees International Union (SEIU) Local 1021. FPPC ids carried by those rows: 1296948, none.
How the committee is recognised as the organisation's: the id resolves in the Filers dataset to 'Service Employees International Union 1021 Candidate PAC'.

The committees that received the money are the Supervisor's own committees for the Board of Education (2012 and 2014), campaigns for another office years before his supervisor seat.

**Shamann Walton for School Board 2014** (filer 147120072; own committee for another office (School Board); status TERMINATED)

| Kind | Contribution date | Filing id (version) | Filing date | Amount | Giver as filed |
|---|---|---|---|---|---|
| Schedule A | 2015-04-22 | 155520026 (v1) | 2015-07-30 | $500 | Service Employees International Union (SEIU) Local 1021 |

Schedule A total for this committee: **$500** in 1 rows.

**Committee to Elect Shamann Walton for SF Board of Education 2012** (filer 130665917; own committee for another office (School Board); status TERMINATED)

| Kind | Contribution date | Filing id (version) | Filing date | Amount | Giver as filed |
|---|---|---|---|---|---|
| Schedule A | 2012-10-30 | 139507483 (v1) | 2013-02-01 | $500 | SEIU Local 1021 |

Schedule A total for this committee: **$500** in 1 rows.

Not added across committees: a total over committees would join money received by different committees. The per-committee Schedule A totals above are the figures to quote.

Outside spending apart: no form 496 report naming this official was filed by a committee the family's names take.

### 5.6 What this does not say

Two things shown side by side for a reader to check. Nothing here says why anyone said or gave anything, and the order of the dates is not an explanation.
The family is read from names as filed; a reader should confirm each is the organisation.

