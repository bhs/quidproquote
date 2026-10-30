# Official funding map: committees tied to the Mayor and the eleven supervisors, who gave through them, and which givers publish a priority

Written by `python build_map.py` from `data/money_snapshot.json` (Ethics Commission Transactions and Filers datasets on DataSF, 2026-10-30; data loaded through 2026-10-30) and `data/priorities.json`. Three kinds of money are kept apart and never added: **gifts** (Schedule A, per committee), **24-hour reports not yet on a periodic report** (listed with their own totals) and **outside spending** (form 496, by the committee that spent).

## 1. Committees tied to each official

Relation is read from the data's `filer_type` and the words of the committee's name; the data has no field for who controls a committee, so a ballot-measure committee is tied to an official by carrying the official's name, and that is a name tie. Own and measure committees are the official's; supporting and opposing committees are primarily formed committees that are not the official's own candidate committee (the data does not say who controls them) and their money is shown apart.

### Daniel Lurie (Mayor)

| Committee | Filer | Relation | Status | Schedule A rows | Schedule A total | 24-hour only | Last filing |
|---|---|---|---|---|---|---|---|
| Daniel Lurie for Prop E | 209443649 | ballot-measure committee carrying the official's name | terminated | 17 | $738,870 | - | 2024-04-11 |
| Mayor Lurie's Yes on D, E & F Committee | 216006060 | ballot-measure committee carrying the official's name | active | 51 | $12,766,000 | $1,018,533 | 2026-10-22 |
| Mayor Lurie's Yes on H Committee | 214099226 | ballot-measure committee carrying the official's name | active | 53 | $5,115,400 | $130,974 | 2026-10-22 |
| Our Future, Our SF Opposing Lurie & Farrell for Mayor 2024 | 212391140 | primarily formed committee opposing the official (not the official's own; control not stated in the data) | terminated | 1 | $250,000 | - | 2025-01-31 |
| Daniel Lurie for Mayor 2024 | 208599394 | own committee for Mayor | active | 2965 | $11,672,608 | - | 2026-09-24 |
| Believe in SF, Lurie for Mayor 2024 | 208769508 | primarily formed committee supporting the official (not the official's own candidate committee; control not stated in the data) | active | 231 | $6,726,796 | - | 2025-07-28 |

### Connie Chan (Supervisor, District 1)

| Committee | Filer | Relation | Status | Schedule A rows | Schedule A total | 24-hour only | Last filing |
|---|---|---|---|---|---|---|---|
| Coalition to Grow San Francisco - Grow SF PAC Opposing Chan for Supervisor 2024 | 205627644 | primarily formed committee opposing the official (not the official's own; control not stated in the data) | terminated | 71 | $79,840 | - | 2024-12-17 |
| Connie Chan for Supervisor 2020 | 185408350 | own committee for Supervisor | terminated | 645 | $106,044 | - | 2024-06-28 |
| Connie Chan for Supervisor 2024 | 206871404 | own committee for Supervisor | terminated | 808 | $168,146 | - | 2025-07-31 |
| Connie Chan for Democratic County Central Committee 2028 | 208675413 | own committee for another office (Democratic County Central Committee) | terminated | 57 | $55,200 | $9,439 | 2025-12-29 |

### Stephen Sherrill (Supervisor, District 2)

| Committee | Filer | Relation | Status | Schedule A rows | Schedule A total | 24-hour only | Last filing |
|---|---|---|---|---|---|---|---|
| Stephen Sherrill for Supervisor 2026 | 213987622 | own committee for Supervisor | active | 711 | $245,100 | - | 2026-08-17 |
| Stephen Sherrill for Supervisor 2026 General | 214620516 | own committee for Supervisor | active | 670 | $219,013 | - | 2026-10-22 |
| Committee to Support Supervisor Stephen Sherrill 2026 | 215838066 | primarily formed committee supporting the official (not the official's own candidate committee; control not stated in the data) | terminated | 12 | $52,750 | - | 2026-08-14 |
| GrowSF Supporting Stephen Sherrill for Supervisor 2026 | 214918275 | primarily formed committee supporting the official (not the official's own candidate committee; control not stated in the data) | active | 40 | $267,200 | - | 2026-08-14 |
| Working Families for Stephen Sherrill for Supervisor 2026, Sponsored by International Union of Operating Engineers Local 3 | 216673030 | primarily formed committee supporting the official (not the official's own candidate committee; control not stated in the data) | active | 4 | $60,000 | - | 2026-07-31 |

### Danny Sauter (Supervisor, District 3)

| Committee | Filer | Relation | Status | Schedule A rows | Schedule A total | 24-hour only | Last filing |
|---|---|---|---|---|---|---|---|
| Danny Sauter for Supervisor 2020 | 186293982 | own committee for Supervisor | terminated | 402 | $76,985 | - | 2021-02-01 |
| Danny Sauter for Supervisor 2024 Officerholder Committee | 208713856 | own committee for Supervisor | active | 845 | $206,180 | - | 2026-07-31 |

### Alan Wong (Supervisor, District 4)

| Committee | Filer | Relation | Status | Schedule A rows | Schedule A total | 24-hour only | Last filing |
|---|---|---|---|---|---|---|---|
| Friends of Alan S. Wong for Community College Board | 149050021 | General Purpose | terminated | 0 | $0 | - | - |
| Alan Wong for Supervisor 2026 | 215112140 | own committee for Supervisor | active | 549 | $162,156 | - | 2026-10-22 |
| Alan Wong for Supervisor 2026 General | 216198377 | own committee for Supervisor | active | 336 | $89,516 | - | 2026-10-22 |
| ALAN WONG FOR COLLEGE BOARD 2024 | 208761647 | own committee for another office (Community College Board) | terminated | 456 | $83,375 | - | 2025-07-28 |
| Alan Wong for College Board 2020 | 185325367 | own committee for another office (Community College Board) | terminated | 446 | $73,283 | - | 2023-07-31 |
| GrowSF Supporting Alan Wong for Supervisor 2026 | 215852865 | primarily formed committee supporting the official (not the official's own candidate committee; control not stated in the data) | active | 43 | $322,849 | - | 2026-08-14 |

### Bilal Mahmood (Supervisor, District 5)

| Committee | Filer | Relation | Status | Schedule A rows | Schedule A total | 24-hour only | Last filing |
|---|---|---|---|---|---|---|---|
| Bilal Mahmood for Supervisor 2024 | 209865652 | own committee for Supervisor | active | 922 | $264,282 | - | 2026-07-31 |
| Bilal Mahmood for DCCC Member 2024 | 208655996 | own committee for another office (Democratic County Central Committee) | terminated | 162 | $254,222 | $19,039 | 2024-09-26 |

### Matt Dorsey (Supervisor, District 6)

| Committee | Filer | Relation | Status | Schedule A rows | Schedule A total | 24-hour only | Last filing |
|---|---|---|---|---|---|---|---|
| Matt Dorsey for Supervisor 2022 | 203924838 | own committee for Supervisor | terminated | 916 | $276,777 | - | 2024-07-31 |
| Matt Dorsey for Supervisor 2026 | 215579031 | own committee for Supervisor | active | 370 | $119,417 | - | 2026-10-22 |
| Matt Dorsey for DCCC Member 2024 Officeholder Committee | 208697921 | own committee for another office (Democratic County Central Committee) | active | 167 | $218,826 | $32,056 | 2026-10-22 |
| Matt Dorsey for Democratic County Central Committee 2012 | 128797285 | own committee for another office (Democratic County Central Committee) | terminated | 1 | $500 | - | 2016-04-29 |
| Matt Dorsey for San Francisco Democratic County Central Committee 2016 | 158287639 | own committee for another office (Democratic County Central Committee) | terminated | 0 | $0 | - | - |

### Myrna Melgar (Supervisor, District 7)

| Committee | Filer | Relation | Status | Schedule A rows | Schedule A total | 24-hour only | Last filing |
|---|---|---|---|---|---|---|---|
| Myrna Melgar [Officeholder Board of Supervisors District 7] | 204210736 | officeholder account (Form 470) | terminated | 0 | $0 | - | - |
| Myrna Melgar for Supervisor 2020 | 186079773 | own committee for Supervisor | terminated | 817 | $162,258 | - | 2022-01-04 |
| Re-Elect Myrna Melgar for Supervisor 2024 | 208194309 | own committee for Supervisor | terminated | 635 | $157,276 | - | 2026-07-30 |
| Myrna Melgar for Democratic County Central Committee AD 19 2016 | 159911091 | own committee for another office (Democratic County Central Committee) | terminated | 19 | $7,717 | $1,100 | 2017-02-01 |

### Rafael Mandelman (Supervisor, District 8)

| Committee | Filer | Relation | Status | Schedule A rows | Schedule A total | 24-hour only | Last filing |
|---|---|---|---|---|---|---|---|
| Mandelman for Supervisor 2010 | 6685950 | own committee for Supervisor | terminated | 540 | $94,778 | - | 2013-08-01 |
| Rafael Mandelman for Supervisor 2018 General | 164729133 | own committee for Supervisor | terminated | 882 | $240,440 | - | 2020-11-16 |
| Rafael Mandelman for Supervisor 2018 Primary | 164723772 | own committee for Supervisor | terminated | 793 | $165,434 | - | 2018-08-28 |
| Rafael Mandelman for Supervisor 2022 | 200878648 | own committee for Supervisor | terminated | 774 | $223,785 | - | 2024-01-01 |
| Mandelman, Rafael [Democratic County Central Committee 2024 | 205793642 | the official's own filer record for another office | active | 0 | $0 | - | - |
| Rafael Mandelman for College Board 2016 Officeholder Account | 158383297 | own committee for another office (Community College Board) | terminated | 218 | $43,845 | - | 2017-01-31 |
| Rafael Mandelman for DCCC - 1262118 | 6667441 | own committee for another office (Democratic County Central Committee) | terminated | 0 | $0 | - | - |
| Rafael Mandelman for Democratic County Central Committee - 2010 | 6680481 | own committee for another office (Democratic County Central Committee) | terminated | 134 | $37,308 | - | 2013-07-31 |
| Rafael Mandelman for Democratic County Central Committee 2012 | 129712945 | own committee for another office (Democratic County Central Committee) | terminated | 0 | $0 | - | - |
| Rafael Mandelman for Democratic County Central Committee 2024 | 182919585 | own committee for another office (Democratic County Central Committee) | terminated | 160 | $44,461 | $4,697 | 2022-10-27 |
| Rafael Mandelman for San Francisco Community College District Board 2012 | 134025580 | own committee for another office (Community College Board) | terminated | 161 | $37,637 | - | 2015-09-30 |
| Rafael Mandelman for the Democratic County Central Committee 2016 | 158383905 | own committee for another office (Democratic County Central Committee) | terminated | 56 | $12,844 | $14,550 | 2017-07-06 |
| Teachers, Nurses, Muni riders, neighbors and working families supporting Mandelman for Supervisor 2010 sponsored by labor organizations | 10992373 | primarily formed committee supporting the official (not the official's own candidate committee; control not stated in the data) | terminated | 5 | $191,000 | $8,809 | 2011-01-31 |

### Jackie Fielder (Supervisor, District 9)

| Committee | Filer | Relation | Status | Schedule A rows | Schedule A total | 24-hour only | Last filing |
|---|---|---|---|---|---|---|---|
| Jackie Fielder for Supervisor 2024 | 208038450 | own committee for Supervisor | active | 1288 | $208,185 | - | 2026-10-29 |

### Shamann Walton (Supervisor, District 10)

| Committee | Filer | Relation | Status | Schedule A rows | Schedule A total | 24-hour only | Last filing |
|---|---|---|---|---|---|---|---|
| Shamann Walton for Supervisor  2022 | 197031455 | own committee for Supervisor | terminated | 472 | $135,967 | - | 2025-07-31 |
| Shamann Walton for Supervisor 2018 | 163932080 | own committee for Supervisor | terminated | 767 | $186,635 | - | 2023-08-01 |
| Committee to Elect Shamann Walton for SF Board of Education 2012 | 130665917 | own committee for another office (School Board) | terminated | 70 | $11,940 | - | 2013-02-01 |
| Shamann Walton for Democratic Central Committee 2020 | 183835609 | own committee for another office (Democratic County Central Committee) | terminated | 56 | $38,965 | $7,107 | 2021-02-23 |
| Shamann Walton for School Board 2014 | 147120072 | own committee for another office (School Board) | terminated | 355 | $62,668 | - | 2015-07-30 |
| United Democratic Club Supporting Shamann Walton for D10 Supervisor 2018 | 174388788 | primarily formed committee supporting the official (not the official's own candidate committee; control not stated in the data) | terminated | 4 | $26,000 | - | 2019-01-08 |

### Chyanne Chen (Supervisor, District 11)

| Committee | Filer | Relation | Status | Schedule A rows | Schedule A total | 24-hour only | Last filing |
|---|---|---|---|---|---|---|---|
| Chyanne Chen for Supervisor 2024 | 210823617 | own committee for Supervisor | terminated | 678 | $131,086 | - | 2025-01-23 |

## 2. Who gave through those committees

Organisations and committees by name (any amount), individuals only from $2,500 within one committee. Grouped by donor family where one takes the name (see section 3), else by name as filed. 'Recognised' says how: by the FPPC id the row carries, or by name.

**Daniel Lurie: gifts to the official's own and measure committees**

| Giver (as filed) | Kind | Amount | Recognised as | Committees |
|---|---|---|---|---|
| DANIEL LURIE; Daniel Lurie | IND | $10,738,206 | - | $10,738,206 Daniel Lurie for Mayor 2024 |
| Michael Moritz | IND | $2,987,500 | - | $2,987,500 Mayor Lurie's Yes on D, E & F Committee |
| Christian Larsen | IND | $1,487,500 | - | $1,487,500 Mayor Lurie's Yes on D, E & F Committee |
| Lyna Lam | IND | $1,000,000 | - | $1,000,000 Mayor Lurie's Yes on D, E & F Committee |
| John Pritzker | IND | $1,000,000 | - | $1,000,000 Mayor Lurie's Yes on D, E & F Committee |
| Emerson Collective LLC(Diedra Nelson) | OTH | $700,000 | Emerson Collective (name) | $500,000 Mayor Lurie's Yes on D, E & F Committee; $200,000 Mayor Lurie's Yes on H Committee |
| Committee to Expand the Middle Class Issues Committee, Sponsored by Airbnb, Inc. | COM | $500,000 | Airbnb (id) | $500,000 Mayor Lurie's Yes on H Committee |
| Anthropic | OTH | $500,000 | - | $500,000 Mayor Lurie's Yes on H Committee |

**Daniel Lurie: gifts to primarily formed committees supporting or opposing the official**

| Giver (as filed) | Kind | Amount | Recognised as | Committees |
|---|---|---|---|---|
| Miriam Haas | IND | $1,000,000 | - | $1,000,000 Believe in SF, Lurie for Mayor 2024 |
| Jonathan Adam Gans | IND | $301,000 | - | $301,000 Believe in SF, Lurie for Mayor 2024 |
| Jan Koum | IND | $250,000 | - | $250,000 Believe in SF, Lurie for Mayor 2024 |
| Jan Koum and Affiliated Entities | IND | $250,000 | - | $250,000 Believe in SF, Lurie for Mayor 2024 |
| Oleg Nodelman | IND | $250,000 | - | $250,000 Believe in SF, Lurie for Mayor 2024 |
| Christian Larsen | IND | $250,000 | - | $250,000 Our Future, Our SF Opposing Lurie & Farr |
| Garrison Mason Morfit | IND | $200,000 | - | $200,000 Believe in SF, Lurie for Mayor 2024 |
| Alan Waxman | IND | $200,000 | - | $200,000 Believe in SF, Lurie for Mayor 2024 |

**Connie Chan: gifts to the official's own and measure committees**

| Giver (as filed) | Kind | Amount | Recognised as | Committees |
|---|---|---|---|---|
| IFPTE Local 21; International Federation Professional and Technical Engineers Local 21 | COM | $26,750 | IFPTE Local 21 (id) | $25,750 Connie Chan for Democratic County Centra; $500 Connie Chan for Supervisor 2020 |
| Phil Ting for Treasurer 2026 | COM | $5,500 | - | $5,000 Connie Chan for Democratic County Centra; $500 Connie Chan for Supervisor 2024 |
| San Francisco Labor Council Labor and Neighbor | COM | $5,500 | San Francisco Labor Council (name) | $5,000 Connie Chan for Democratic County Centra; $500 Connie Chan for Supervisor 2024 |
| Dignity CA SEIU 2015 | COM | $2,500 | SEIU Local 2015 (name) | $2,500 Connie Chan for Democratic County Centra |
| UA Local 38 COPE Fund | COM | $2,500 | - | $2,500 Connie Chan for Democratic County Centra |
| New Deal Advisers | OTH | $2,500 | - | $2,500 Connie Chan for Democratic County Centra |
| Service Employees International Union Local 1021; Service Employees International Union Lo | COM | $1,000 | SEIU Local 1021 (name) | $500 Connie Chan for Supervisor 2020; $500 Connie Chan for Supervisor 2024 |
| California Nurses Association | COM | $1,000 | - | $500 Connie Chan for Supervisor 2020; $500 Connie Chan for Supervisor 2024 |

**Connie Chan: gifts to primarily formed committees supporting or opposing the official**

| Giver (as filed) | Kind | Amount | Recognised as | Committees |
|---|---|---|---|---|
| Building Owners and Managers Association of SF PAC - IE | COM | $20,000 | Building Owners and Managers Association of San Francisco (name) | $20,000 Coalition to Grow San Francisco - Grow S |
| Andrew Jordan | IND | $10,000 | - | $10,000 Coalition to Grow San Francisco - Grow S |
| Michael John Kerns | IND | $10,000 | - | $10,000 Coalition to Grow San Francisco - Grow S |
| Morgan Beller | IND | $4,990 | - | $4,990 Coalition to Grow San Francisco - Grow S |
| Calvin French-Owen | IND | $4,990 | - | $4,990 Coalition to Grow San Francisco - Grow S |
| John Lyons | IND | $4,990 | - | $4,990 Coalition to Grow San Francisco - Grow S |
| Ari Freisinger | IND | $4,000 | - | $4,000 Coalition to Grow San Francisco - Grow S |
| Stephen Hayes | IND | $3,500 | - | $3,500 Coalition to Grow San Francisco - Grow S |

**Stephen Sherrill: gifts to the official's own and measure committees**

| Giver (as filed) | Kind | Amount | Recognised as | Committees |
|---|---|---|---|---|
| GFC COURAGE COMMITTEE - BAY AREA CHAPTER; GFC COURAGE COMMITTEE - EXCELLENCE IN EDUCATION  | COM | $2,500 | Govern For California (name) | $1,500 Stephen Sherrill for Supervisor 2026; $1,000 Stephen Sherrill for Supervisor 2026 Gen |
| TEAMSTERS UNION LOCAL NO. 665 | COM | $1,000 | - | $500 Stephen Sherrill for Supervisor 2026; $500 Stephen Sherrill for Supervisor 2026 Gen |
| MATT HANEY FOR ASSEMBLY 2026 | COM | $500 | - | $500 Stephen Sherrill for Supervisor 2026 |
| U.A. LOCAL 38 COPE FUND | COM | $500 | - | $500 Stephen Sherrill for Supervisor 2026 |
| SAN FRANCISCO APARTMENT ASSOCIATION POLITICAL ACTION COMMITTEE | COM | $500 | San Francisco Apartment Association (name) | $500 Stephen Sherrill for Supervisor 2026 |
| OPERATING ENGINEERS LOCAL UNION 3 DISTRICT 01, 02 & 03 PAC | COM | $500 | Operating Engineers Local 3 (name) | $500 Stephen Sherrill for Supervisor 2026 |
| UNITED FOOD AND COMMERCIAL WORKERS WESTERN STATES COUNCIL CANDIDATE PAC | COM | $500 | - | $500 Stephen Sherrill for Supervisor 2026 |
| IBEW LOCAL 6 POLITICAL ACCOUNT | COM | $500 | - | $500 Stephen Sherrill for Supervisor 2026 |

**Stephen Sherrill: gifts to primarily formed committees supporting or opposing the official**

| Giver (as filed) | Kind | Amount | Recognised as | Committees |
|---|---|---|---|---|
| Nicholas Josefowitz | IND | $50,000 | - | $50,000 GrowSF Supporting Stephen Sherrill for S |
| Zach Jones | IND | $30,000 | - | $30,000 GrowSF Supporting Stephen Sherrill for S |
| Andrew Chatham | IND | $26,000 | - | $26,000 GrowSF Supporting Stephen Sherrill for S |
| North Coast States Regional Council of Carpenters Power PAC Small Contributor Committee | COM | $20,000 | - | $20,000 Working Families for Stephen Sherrill fo |
| Operating Engineers 3 Statewide PAC | SCC | $20,000 | Operating Engineers Local 3 (name) | $20,000 Working Families for Stephen Sherrill fo |
| Diana L. Nelson | IND | $15,000 | - | $15,000 Committee to Support Supervisor Stephen  |
| California Laborers for Equality and Progress (Small Contributor Committee) | COM | $10,000 | - | $10,000 Working Families for Stephen Sherrill fo |
| San Francisco Laborer's Local 261 PAC | COM | $10,000 | San Francisco Laborers Local 261 (name) | $10,000 Working Families for Stephen Sherrill fo |

**Danny Sauter: gifts to the official's own and measure committees**

| Giver (as filed) | Kind | Amount | Recognised as | Committees |
|---|---|---|---|---|
| DANIEL SAUTER | IND | $5,000 | - | $5,000 Danny Sauter for Supervisor 2024 Officer |
| GFC COURAGE COMMITTEE - BAY AREA CHAPTER; GFC COURAGE COMMITTEE - CALIFORNIA BUSINESS COAL | COM | $4,500 | Govern For California (name) | $4,500 Danny Sauter for Supervisor 2024 Officer |
| SAN FRANCISCO MARIN MEDICAL SOCIETY POLITICAL ACTION COMMITTEE | COM | $500 | - | $300 Danny Sauter for Supervisor 2024 Officer; $200 Danny Sauter for Supervisor 2020 |
| INTERNATIONAL UNION OF ELEVATOR CONSTRUCTORS LOCAL 8 PAC SPONSORED BY INTERNATIONAL UNION  | COM | $500 | names sponsor: International Union Of Elevator Constructors Local 8 | $500 Danny Sauter for Supervisor 2024 Officer |
| SAN FRANCISCO BUILDING AND CONSTRUCTION TRADES COUNCIL POLITICAL ORGANIZATION OF WORKERS F | COM | $500 | - | $500 Danny Sauter for Supervisor 2024 Officer |
| TEAMSTERS LOCAL UNION NO. 665 | COM | $500 | - | $500 Danny Sauter for Supervisor 2024 Officer |
| SPRINKLER FITTERS & APPRENTICES LOCAL 483 LOCAL POLITICAL ACTION COMM. | COM | $500 | - | $500 Danny Sauter for Supervisor 2024 Officer |
| THEATRICAL STAGE EMPLOYEES LOCAL 16 INTERNATIONAL ALLIANCE OF THEATRICAL STAGE EMPLOYEES ( | COM | $500 | - | $500 Danny Sauter for Supervisor 2024 Officer |

**Alan Wong: gifts to the official's own and measure committees**

| Giver (as filed) | Kind | Amount | Recognised as | Committees |
|---|---|---|---|---|
| OPERATING ENGINEERS LOCAL UNION 3 DISTRICT 01, 02 & 03 PAC; Operating Engineers Local 3 | COM | $1,500 | Operating Engineers Local 3 (name) | $500 Alan Wong for College Board 2020; $500 Alan Wong for Supervisor 2026 |
| SAN FRANCISCO LABORER'S LOCAL 261 PAC; San Francisco Laborer's Local 261; San Francisco La | COM | $1,500 | San Francisco Laborers Local 261 (name) | $500 Alan Wong for College Board 2020; $500 ALAN WONG FOR COLLEGE BOARD 2024 |
| TEAMSTERS LOCAL UNION 350 PAC; Teamsters Local Union 350 PAC | COM | $1,500 | - | $500 ALAN WONG FOR COLLEGE BOARD 2024; $500 Alan Wong for Supervisor 2026 |
| SAN FRANCISCO FIRE FIGHTERS LOCAL 798 P.A.C.; San Francisco Fire Fighters Local 798 P.a.c. | COM | $1,500 | - | $500 ALAN WONG FOR COLLEGE BOARD 2024; $500 Alan Wong for Supervisor 2026 |
| IBEW LOCAL 6 POLITICAL ACCOUNT; Ibew Local 6 Political Account | COM | $1,500 | - | $500 ALAN WONG FOR COLLEGE BOARD 2024; $500 Alan Wong for Supervisor 2026 |
| UNITED FOOD AND COMMERCIAL WORKERS WESTERN STATES COUNCIL CANDIDATE PAC; United Food and C | SCC | $1,500 | - | $500 ALAN WONG FOR COLLEGE BOARD 2024; $500 Alan Wong for Supervisor 2026 |
| THEATRICAL STAGE EMPLOYEES LOCAL 16 INTERNATIONAL ALLIANCE OF THEATRICAL STAGE EMPLOYEES ( | COM | $1,000 | - | $500 ALAN WONG FOR COLLEGE BOARD 2024; $500 Alan Wong for Supervisor 2026 |
| NATIONAL UNION OF HEALTHCARE WORKERS CANDIDATE COMMITTEE FOR QUALITY PATIENT CARE AND UNIO | COM | $1,000 | - | $500 ALAN WONG FOR COLLEGE BOARD 2024; $500 Alan Wong for Supervisor 2026 General |

**Alan Wong: gifts to primarily formed committees supporting or opposing the official**

| Giver (as filed) | Kind | Amount | Recognised as | Committees |
|---|---|---|---|---|
| Michael Moritz | IND | $250,000 | - | $250,000 GrowSF Supporting Alan Wong for Supervis |
| Noah Smith | IND | $10,000 | - | $10,000 GrowSF Supporting Alan Wong for Supervis |
| Maco Stewart | IND | $10,000 | - | $10,000 GrowSF Supporting Alan Wong for Supervis |
| Building Owners and Managers Association of San Francisco PAC Independent Expenditures aka | COM | $9,999 | Building Owners and Managers Association of San Francisco (name) | $9,999 GrowSF Supporting Alan Wong for Supervis |
| Amos Elliston | IND | $5,000 | - | $5,000 GrowSF Supporting Alan Wong for Supervis |
| Hilary Shirazi | IND | $5,000 | - | $5,000 GrowSF Supporting Alan Wong for Supervis |
| Jared Friedman | IND | $4,900 | - | $4,900 GrowSF Supporting Alan Wong for Supervis |
| Luke Miner | IND | $4,900 | - | $4,900 GrowSF Supporting Alan Wong for Supervis |

**Bilal Mahmood: gifts to the official's own and measure committees**

| Giver (as filed) | Kind | Amount | Recognised as | Committees |
|---|---|---|---|---|
| PAUL BUCHHEIT | IND | $20,000 | - | $20,000 Bilal Mahmood for DCCC Member 2024 |
| CHRIS LARSEN | IND | $20,000 | - | $20,000 Bilal Mahmood for DCCC Member 2024 |
| JEREMY LIEW | IND | $20,000 | - | $20,000 Bilal Mahmood for DCCC Member 2024 |
| JESSICA LIVINGSTON | IND | $20,000 | - | $20,000 Bilal Mahmood for DCCC Member 2024 |
| GFC COURAGE COMMITTEE - BAY AREA CHAPTER; GFC COURAGE COMMITTEE - CALIFORNIA BUSINESS COAL | COM | $18,000 | Govern For California (name) | $10,500 Bilal Mahmood for DCCC Member 2024; $7,500 Bilal Mahmood for Supervisor 2024 |
| SAIKAT CHAKRABARTI | IND | $10,000 | - | $10,000 Bilal Mahmood for DCCC Member 2024 |
| CAROLYN CHATHAM | IND | $10,000 | - | $10,000 Bilal Mahmood for DCCC Member 2024 |
| JEROME GUILLEN | IND | $10,000 | - | $10,000 Bilal Mahmood for DCCC Member 2024 |

**Matt Dorsey: gifts to the official's own and measure committees**

| Giver (as filed) | Kind | Amount | Recognised as | Committees |
|---|---|---|---|---|
| CHRIS LARSEN | IND | $25,000 | - | $25,000 Matt Dorsey for DCCC Member 2024 Officeh |
| SAN FRANCISCO ASSOCIATION OF REALTORS | OTH | $20,000 | San Francisco Association of Realtors (name) | $20,000 Matt Dorsey for DCCC Member 2024 Officeh |
| GARRY TAN | IND | $12,500 | - | $12,500 Matt Dorsey for DCCC Member 2024 Officeh |
| SAN FRANCISCO APARTMENT ASSOCIATION; SAN FRANCISCO APARTMENT ASSOCIATION POLITICAL ACTION  | COM | $11,000 | San Francisco Apartment Association (name) | $10,000 Matt Dorsey for DCCC Member 2024 Officeh; $500 Matt Dorsey for Supervisor 2022 |
| SAN FRANCISCO POLICE OFFICERS ASSOCIATION PAC | COM | $8,000 | San Francisco Police Officers Association (id) | $7,500 Matt Dorsey for DCCC Member 2024 Officeh; $500 Matt Dorsey for Supervisor 2022 |
| YERBA BUENA COMMONS ASSOCIATES, INC. | OTH | $7,500 | - | $7,500 Matt Dorsey for DCCC Member 2024 Officeh |
| JOSEPH COTCHETT | IND | $7,500 | - | $7,500 Matt Dorsey for DCCC Member 2024 Officeh |
| DANNY HABER | IND | $7,000 | - | $7,000 Matt Dorsey for DCCC Member 2024 Officeh |

**Myrna Melgar: gifts to the official's own and measure committees**

| Giver (as filed) | Kind | Amount | Recognised as | Committees |
|---|---|---|---|---|
| Myrna Melgar; Myrna Melgar (Iton) | IND | $8,467 | - | $5,000 Myrna Melgar for Supervisor 2020; $3,467 Myrna Melgar for Democratic County Centr |
| Dignity CA SEIU Local 2015 | COM | $1,000 | SEIU Local 2015 (name) | $500 Myrna Melgar for Supervisor 2020; $500 Re-Elect Myrna Melgar for Supervisor 202 |
| IFPTE Local 21 TJ Anthony PAC Fund; International Federation of Professional and Technical | COM | $1,000 | IFPTE Local 21 (id) | $500 Myrna Melgar for Supervisor 2020; $500 Re-Elect Myrna Melgar for Supervisor 202 |
| Operating Engineers Local Union NO. 3 District 01, 02, 03 PAC; Operating Engineers Local U | COM | $1,000 | Operating Engineers Local 3 (name) | $500 Myrna Melgar for Supervisor 2020; $500 Re-Elect Myrna Melgar for Supervisor 202 |
| San Francisco Laborer's Local 261; San Francisco Laborers Local 261 PAC | COM | $1,000 | San Francisco Laborers Local 261 (name) | $500 Myrna Melgar for Supervisor 2020; $500 Re-Elect Myrna Melgar for Supervisor 202 |
| McCarthy Engineering LLC | OTH | $500 | - | $500 Myrna Melgar for Democratic County Centr |
| Residential Builder's Association | OTH | $500 | - | $500 Myrna Melgar for Democratic County Centr |
| Teamsters Union Local #665 | COM | $500 | - | $500 Myrna Melgar for Supervisor 2020 |

**Rafael Mandelman: gifts to the official's own and measure committees**

| Giver (as filed) | Kind | Amount | Recognised as | Committees |
|---|---|---|---|---|
| Rafael Mandelman | IND | $13,978 | - | $9,841 Rafael Mandelman for San Francisco Commu; $4,138 Rafael Mandelman for Democratic County C |
| San Francisco Laborer's Local 261; San Francisco Laborer's Local 261 P.A.C.; San Francisco | OTH | $5,000 | San Francisco Laborers Local 261 (name) | $2,000 Rafael Mandelman for Democratic County C; $500 Rafael Mandelman for San Francisco Commu |
| Pinnacle Properties, INC. | OTH | $2,500 | - | $2,500 Rafael Mandelman for Democratic County C |
| SEIU Local 1021 Candidate PAC; Service Employees International Union Local 1021; Service E | COM | $2,000 | SEIU Local 1021 (name) | $500 Rafael Mandelman for San Francisco Commu; $500 Rafael Mandelman for College Board 2016  |
| United Educators of San Francisco - Candidate PAC; United Educators of San Francisco-Candi | COM | $1,500 | - | $500 Rafael Mandelman for College Board 2016 ; $500 Rafael Mandelman for Supervisor 2018 Gen |
| UA Local 38 COPE Fund; UA Local 38 Cope Fund | COM | $1,500 | - | $500 Rafael Mandelman for College Board 2016 ; $500 Rafael Mandelman for Democratic County C |
| IFPTE Local 21; International Federation Of Professional And Technical Engineers  Local 21 | COM | $1,500 | IFPTE Local 21 (id) | $500 Rafael Mandelman for College Board 2016 ; $500 Rafael Mandelman for Supervisor 2018 Gen |
| National Union of Healthcare Workers Candidate Committee | COM | $1,500 | - | $500 Rafael Mandelman for Supervisor 2018 Pri; $500 Rafael Mandelman for Supervisor 2018 Gen |

**Rafael Mandelman: gifts to primarily formed committees supporting or opposing the official**

| Giver (as filed) | Kind | Amount | Recognised as | Committees |
|---|---|---|---|---|
| Service Employees International Union Local 1021 | SCC | $100,000 | SEIU Local 1021 (name) | $100,000 Teachers, Nurses, Muni riders, neighbors |
| Standing up to Save San Francisco - No on Measures B and K / Yes on Measures J and N | COM | $45,000 | - | $45,000 Teachers, Nurses, Muni riders, neighbors |
| San Francisco Labor Council Labor & Neighbor Independent Expenditure PAC | COM | $39,000 | San Francisco Labor Council (name) | $39,000 Teachers, Nurses, Muni riders, neighbors |
| Friends Supporting Debra Walker for Supervisor 2010, sponsored by labor organizations | COM | $7,000 | names sponsor: Labor Organizations | $7,000 Teachers, Nurses, Muni riders, neighbors |

**Jackie Fielder: gifts to the official's own and measure committees**

| Giver (as filed) | Kind | Amount | Recognised as | Committees |
|---|---|---|---|---|
| International Union of Elevator Constructors Local #8 PAC | COM | $500 | - | $500 Jackie Fielder for Supervisor 2024 |
| Teamsters #853 Political Activities Committee Fund | COM | $500 | - | $500 Jackie Fielder for Supervisor 2024 |
| Teamsters Union Local No. 665 PAC | COM | $500 | - | $500 Jackie Fielder for Supervisor 2024 |
| Theatrical Stage Employees Local 16 IATSE | COM | $500 | - | $500 Jackie Fielder for Supervisor 2024 |
| United Educators of San Francisco - Candidate PAC | COM | $500 | - | $500 Jackie Fielder for Supervisor 2024 |
| National Union Of Healthcare Workers Candidate Committee for Quality Patient Care | COM | $500 | - | $500 Jackie Fielder for Supervisor 2024 |
| Dignity CA SEIU Local 2015 | COM | $500 | SEIU Local 2015 (name) | $500 Jackie Fielder for Supervisor 2024 |
| Teamsters Local Union 350 PAC | COM | $500 | - | $500 Jackie Fielder for Supervisor 2024 |

**Shamann Walton: gifts to the official's own and measure committees**

| Giver (as filed) | Kind | Amount | Recognised as | Committees |
|---|---|---|---|---|
| New Deal Advisers | OTH | $5,000 | - | $5,000 Shamann Walton for Democratic Central Co |
| BCSF, Inc. | OTH | $3,000 | - | $3,000 Shamann Walton for Democratic Central Co |
| FMSF, Inc. | OTH | $3,000 | - | $3,000 Shamann Walton for Democratic Central Co |
| Outer Sunset Holdings, Inc. | OTH | $3,000 | - | $3,000 Shamann Walton for Democratic Central Co |
| San Francisco Laborer's Local 261 PAC; San Francisco Laborer's Local 261 PAC #981076 | COM | $2,000 | San Francisco Laborers Local 261 (name) | $500 Shamann Walton for School Board 2014; $500 Shamann Walton for Supervisor 2018 |
| Nibbi Bros. Associates, Inc. | OTH | $2,000 | - | $2,000 Shamann Walton for Democratic Central Co |
| Yerba Buena Commons Associates, Inc. | OTH | $2,000 | - | $2,000 Shamann Walton for Democratic Central Co |
| Operating Engineers Local Union 3 District 01, 02 & 03 PAC; Operating Engineers Local Unio | COM | $1,500 | Operating Engineers Local 3 (name) | $500 Shamann Walton for School Board 2014; $500 Shamann Walton for Supervisor 2018 |

**Shamann Walton: gifts to primarily formed committees supporting or opposing the official**

| Giver (as filed) | Kind | Amount | Recognised as | Committees |
|---|---|---|---|---|
| Progress San Francisco | COM | $16,000 | - | $16,000 United Democratic Club Supporting Shaman |
| BCSF, INC. | OTH | $5,000 | - | $5,000 United Democratic Club Supporting Shaman |
| Boca Lake Retail, Inc. | OTH | $5,000 | - | $5,000 United Democratic Club Supporting Shaman |

**Chyanne Chen: gifts to the official's own and measure committees**

| Giver (as filed) | Kind | Amount | Recognised as | Committees |
|---|---|---|---|---|
| United Educators of SF | COM | $500 | - | $500 Chyanne Chen for Supervisor 2024 |
| National Union of Healthcare Workers Candidate Committee for Quality Patient Care | COM | $500 | - | $500 Chyanne Chen for Supervisor 2024 |
| SEIU Local 99 PAC | COM | $500 | - | $500 Chyanne Chen for Supervisor 2024 |
| Dignity CA SEIU Local 2015 | COM | $500 | SEIU Local 2015 (name) | $500 Chyanne Chen for Supervisor 2024 |
| Asian Americans for Progressive Alameda PAC | COM | $500 | - | $500 Chyanne Chen for Supervisor 2024 |
| Andy Li for College Board 2018 | COM | $500 | - | $500 Chyanne Chen for Supervisor 2024 |
| IFPTE LOCAL 21 TJ Anthony PAC Fund | COM | $500 | IFPTE Local 21 (id) | $500 Chyanne Chen for Supervisor 2024 |
| American Federation of Teachers Local 2121 | OTH | $500 | - | $500 Chyanne Chen for Supervisor 2024 |

## 3. How a gift from an organisation's own committee is recognised as the organisation's

Of 568 committee and small-contributor-committee giver rows, grouped by committee and donor name:

- with an FPPC id: 562
- id resolves in the Filers dataset: 338
- name states a sponsor: 11
- taken by a donor family: 133
- by id: 19
- by name: 114

| Family | Names the rows carry |
|---|---|
| San Francisco Chamber of Commerce | San Francisco Forward sponsored by San Francisco Chamber of Commerce |
| Airbnb | Committee to Expand the Middle Class Issues Committee, Sponsored by Airbnb, Inc. |
| San Francisco Police Officers Association | SAN FRANCISCO POLICE OFFICERS ASSOCIATION PAC; San Francisco Police Officers Association Issues PAC |
| SEIU Local 1021 | SEIU Local 1021 Candidate PAC; Service Employees International Union (SEIU) Local 1021; Service Employees International Union Local #1021 Candidate PAC; Service Employees International Union Local 1021; Service Employees International Union Local 1021 Candidate PAC; Service Employees International U |
| SEIU Local 2015 | DIGNITY CA SERVICE EMPLOYEES INTERNATIONAL UNION SEIU LOCAL 2015; Dignity CA SEIU 2015; Dignity CA SEIU Local 2015 |
| IFPTE Local 21 | IFPTE LOCAL 21 TJ Anthony PAC Fund; IFPTE Local 21; IFPTE Local 21 TJ Anthony PAC Fund; International Federation Of Professional And Technical Engineers  Local 21 Tj Anthony Pac Fund; International Federation Professional and Technical Engineers Local 21; International Federation of Professional and |
| San Francisco Labor Council | San Francisco Labor Council Labor & Neighbor; San Francisco Labor Council Labor & Neighbor Independent Expenditure PAC; San Francisco Labor Council Labor & Neighbor PAC; San Francisco Labor Council Labor and Neighbor |
| Govern For California | GFC COURAGE COMMITTEE - BAY AREA CHAPTER; GFC COURAGE COMMITTEE - CALIFORNIA BUSINESS COALITION; GFC COURAGE COMMITTEE - COMMON SENSE CHAPTER; GFC COURAGE COMMITTEE - EAST BAY CHAPTER; GFC COURAGE COMMITTEE - EXCELLENCE IN EDUCATION CHAPTER; GFC COURAGE COMMITTEE - FUTURE GENERATIONS CHAPER; GFC COU |
| San Francisco Apartment Association | SAN FRANCISCO APARTMENT ASSOCIATION; SAN FRANCISCO APARTMENT ASSOCIATION POLITICAL ACTION COMMITTEE; San Francisco Apartment Association; San Francisco Apartment Association Political Action Committee |
| Building Owners and Managers Association of San Francisco | Building Owners and Managers Association of SF PAC - IE; Building Owners and Managers Association of San Francisco PAC Independent Expenditures aka (BOMA-SF-PAC-IE) |
| Transport Workers Union Local 250-A | Transport Workers Union, Local 250 A, Afl Cio C.O.P.E.; Transport Workers Union, Local 250-A, AFL-CIO COPE |
| Operating Engineers Local 3 | OPERATING ENGINEERS LOCAL 3 DISTRICT 01 POLITICAL ACTION COMMITTEE; OPERATING ENGINEERS LOCAL UNION 3 DISTRICT 01, 02 & 03 PAC; OPERATING ENGINEERS LOCAL UNION NO. 3 DISTRICT 01, 02, 03 PAC; Operating Engineers 3 Dist#1,2,3 PAC; Operating Engineers 3 Dist.#1,2,3; Operating Engineers 3 Statewide PAC; |
| San Francisco Laborers Local 261 | SAN FRACISCO LABORER'S LOCAL 261; SAN FRANCISCO LABORER'S LOCAL 261 P.A.C.; SAN FRANCISCO LABORER'S LOCAL 261 PAC; San Francisco Laborer's Local 261; San Francisco Laborer's Local 261 P.A.C.; San Francisco Laborer's Local 261 P.a.c.; San Francisco Laborer's Local 261 PAC; San Francisco Laborer's Loc |

## 4. Donor families, whether they publish a priority, and where their money reached

| Family | Kind | Publishes a priority in its own words (retrieved) | Gifts by receiving committee (Schedule A) | Outside spending (form 496) naming an official |
|---|---|---|---|---|
| San Francisco Chamber of Commerce | business association | <https://sfchamber.com/november-2026-voter-guide/> (2026-10-30) | measure $499,000 | none |
| Airbnb | company | <https://news.airbnb.com/an-update-about-our-community-in-san-francisco> (2026-10-30) | measure $500,000 | none |
| San Francisco Police Officers Association | union | <https://sfpoa.org/mayor-lurie-joined-by-firefighters-and-police-officers-in-strong-opposition-to-proposition-i/> (2026-10-30) | measure $10,000, own $1,500, own-other $7,500 | $1,149 |
| SEIU Local 1021 | union | <https://www.seiu1021.org/post/election-endorsements-nov-3-2026> (2026-10-30) | own $2,000, own-other $2,000, supporting $100,000 | none |
| SEIU Local 2015 | union | none found | own $3,000, own-other $2,500 | none |
| IFPTE Local 21 | union | none found | own $4,500, own-other $26,750 | none |
| San Francisco Labor Council | labor federation | none found | own $2,500, own-other $5,000, supporting $39,000 | $279,314 |
| Govern For California | advocacy group | <https://www.governforcalifornia.org/news/2026/10/21/sf-voter-guide> (2026-10-30) | own $14,500, own-other $10,500 | none |
| San Francisco Association of Realtors | trade association | none found | own-other $20,000 | none |
| San Francisco Apartment Association | trade association | <https://www.sfaa.org/advocacy> (2026-10-30) | own $4,500, own-other $10,000 | none |
| Building Owners and Managers Association of San Francisco | trade association | <https://bomasf.org/advocacy/policy-priorities> (2026-10-30) | opposing $20,000, supporting $9,999 | none |
| Transport Workers Union Local 250-A | union | none found | measure $50,000 | none |
| Operating Engineers Local 3 | union | none found | measure $25,000, own $8,000, own-other $2,100, supporting $20,000 | $31,495 |
| San Francisco Laborers Local 261 | union | none found | measure $10,000, own $6,500, own-other $6,000, supporting $10,000 | none |
| Emerson Collective | foundation and investment firm | none found | measure $700,000 | none |
| GrowSF | advocacy group | <https://growsf.org/voter-guide/> (2026-10-30) | none | $675,124 |
| Neighbors for a Better San Francisco (Blueprint) | advocacy group | none found | none | $148,743 |

Families with no money in these committees (none found) are still listed so a reader sees the search. Individuals:

| Official | Giver | Amount | Survey class of own statement | Own source |
|---|---|---|---|---|
| Daniel Lurie | Michael Moritz | $2,987,500 (controlled) | B | None |
| Daniel Lurie | Christian Larsen | $1,487,500 (controlled) | C | None |
| Daniel Lurie | Lyna Lam | $1,000,000 (controlled) | C | None |
| Daniel Lurie | John Pritzker | $1,000,000 (controlled) | C | None |
| Daniel Lurie | Dagmar Dolby | $500,000 (controlled) | C | None |
| Daniel Lurie | John Wolthuis | $500,000 (controlled) | D | None |
| Daniel Lurie | Jeffrey Lawson | $350,000 (controlled) | C | None |
| Alan Wong | Michael Moritz | $250,000 (third-party) | B | None |
| Daniel Lurie | Jean-Pierre Conte | $250,000 (controlled) | C | None |
| Daniel Lurie | Michael Seibel | $250,000 (controlled) | D | None |
| Daniel Lurie | Jan Koum | $250,000 (third-party) | C | None |
| Daniel Lurie | Christian Larsen | $250,000 (third-party) | C | None |
| Daniel Lurie | Jean Pierre Conte | $100,000 (third-party) | C | None |
| Matt Dorsey | CHRIS LARSEN | $25,000 (controlled) | C | None |
| Daniel Lurie | Jeremy Stoppelman | $25,000 (controlled) | A | https://x.com/jeremys |
| Daniel Lurie | Dagmar Dolby | $25,000 (third-party) | C | None |
| Bilal Mahmood | CHRIS LARSEN | $20,000 (controlled) | C | None |
| Bilal Mahmood | SAIKAT CHAKRABARTI | $10,000 (controlled) | B | None |
| Bilal Mahmood | EMMETT SHEAR | $10,000 (controlled) | D | None |
| Stephen Sherrill | Jeff Lawson | $4,900 (third-party) | C | None |

## 5. Outside spending naming an official, apart from gifts

Form 496 reports, by the committee that filed them; spending by the committee, not a gift to the official's committees. A committee that is itself tied to the official (for example 'Believe in SF, Lurie for Mayor 2024') appears in section 1 as a committee and here as a spender.

**Daniel Lurie**

| Spender | Stance | Amount | Filings | Dates |
|---|---|---|---|---|
| Believe in SF, Lurie for Mayor 2024 | supports | $3,740,031 | 56 | 2024-08-07 to 2024-11-04 |
| Safer San Francisco for Mark Farrell for Mayor 2024 | opposes | $2,882,465 | 15 | 2024-09-26 to 2024-10-30 |
| TogetherSF Action | opposes | $174,138 | 1 | 2024-10-14 to 2024-10-30 |
| Our Future, Our SF Opposing Lurie & Farrell for Mayor 2024 | opposes | $113,128 | 3 | 2024-10-28 to 2024-10-31 |
| San Francisco Working Families Voter Guide Sponsored by Healthcare and Hospitali | opposes | $54,026 | 3 | 2024-10-11 to 2024-11-01 |
| Coalition to Grow San Francisco - Grow SF PAC | supports | $14,940 | 4 | 2024-09-29 to 2024-10-28 |

**Connie Chan**

| Spender | Stance | Amount | Filings | Dates |
|---|---|---|---|---|
| Fix our City SF, Sponsored by Labor Organizations | supports | $693,473 | 20 | 2024-08-09 to 2024-11-01 |
| SF Workforce Housing Alliance PAC 2020, sponsored by Neighbors for a Better San  | opposes | $120,743 | 7 | 2020-10-21 to 2020-11-02 |
| Asian Americans for Representation | supports | $90,913 | 5 | 2024-09-06 to 2024-10-11 |
| Building a Working SF Sponsored by Labor Organizations | supports | $39,294 | 3 | 2024-10-20 to 2024-10-31 |
| San Francisco Tenants and Families for Affordable Housing, sponsored by communit | supports | $30,867 | 1 | 2020-10-15 to 2020-10-15 |
| Rose Pak Democratic Club | supports | $22,158 | 1 | 2020-10-25 to 2020-10-27 |

**Stephen Sherrill**

| Spender | Stance | Amount | Filings | Dates |
|---|---|---|---|---|
| SF Believes | supports | $233,231 | 8 | 2026-03-17 to 2026-05-26 |
| GrowSF Supporting Stephen Sherrill for Supervisor 2026 | supports | $122,045 | 10 | 2026-03-16 to 2026-05-18 |
| Committee to Support Supervisor Stephen Sherrill 2026 | supports | $75,500 | 1 | 2026-05-08 to 2026-05-14 |
| California Alliance of Family Owned Businesses PAC | supports | $65,401 | 4 | 2026-05-03 to 2026-05-26 |
| GrowSF Voter Guide | supports | $36,565 | 5 | 2026-04-09 to 2026-10-18 |
| Working Families for Stephen Sherrill for Supervisor 2026, Sponsored by Internat | supports | $31,495 | 3 | 2026-05-26 to 2026-06-02 |

**Danny Sauter**

| Spender | Stance | Amount | Filings | Dates |
|---|---|---|---|---|
| Families for a Vibrant SF Sponsored by Abundance Network | supports | $161,877 | 7 | 2024-09-30 to 2024-10-30 |
| Coalition to Grow San Francisco - Grow SF PAC | supports | $70,910 | 5 | 2024-08-31 to 2024-10-28 |
| San Francisco Labor Council Labor & Neighbor Independent Expenditure Political A | opposes | $55,746 | 5 | 2024-10-11 to 2024-11-02 |

**Alan Wong**

| Spender | Stance | Amount | Filings | Dates |
|---|---|---|---|---|
| SF Believes | supports | $409,908 | 23 | 2026-03-17 to 2026-05-28 |
| GrowSF Supporting Alan Wong for Supervisor 2026 | supports | $206,372 | 14 | 2026-03-05 to 2026-05-19 |
| California Alliance of Family Owned Businesses PAC | supports | $176,871 | 9 | 2026-05-03 to 2026-10-22 |
| GrowSF Voter Guide | supports | $40,506 | 8 | 2026-04-09 to 2026-10-18 |
| Affordable SF Now supporting Natalie Gee for Supervisor 2026, Sponsored by Labor | opposes | $24,754 | 5 | 2026-05-06 to 2026-05-28 |
| Neighbors For A Better San Francisco Advocacy | supports | $20,000 | 1 | 2026-05-28 to 2026-05-28 |

**Bilal Mahmood**

| Spender | Stance | Amount | Filings | Dates |
|---|---|---|---|---|
| Fix our City SF, Sponsored by Labor Organizations | opposes | $134,178 | 3 | 2024-10-09 to 2024-10-27 |
| Coalition to Grow San Francisco - Grow SF PAC Opposing Preston for Supervisor 20 | supports | $131,170 | 7 | 2024-09-05 to 2024-10-20 |
| San Francisco Labor Council Labor & Neighbor Independent Expenditure Political A | opposes | $65,879 | 5 | 2024-10-11 to 2024-11-02 |
| Coalition to Grow San Francisco - Grow SF PAC | supports | $14,940 | 4 | 2024-09-29 to 2024-10-28 |

**Matt Dorsey**

| Spender | Stance | Amount | Filings | Dates |
|---|---|---|---|---|
| San Francisco Labor Council Labor & Neighbor Independent Expenditure Political A | opposes | $37,977 | 4 | 2022-10-14 to 2022-10-28 |
| Coalition to Grow San Francisco - Grow SF PAC | supports | $29,155 | 6 | 2022-09-29 to 2026-10-18 |
| Alice B. Toklas Lesbian and Gay Democratic Club PAC | supports | $4,369 | 1 | 2022-09-16 to 2022-09-16 |
| San Francisco Deputy Sheriffs' Association Political Action Committee | supports | $4,207 | 2 | 2022-10-21 to 2022-11-08 |
| SAN FRANCISCO ELECTRICAL CONTRACTORS ASSOCIATION PAC | supports | $2,500 | 1 | 2026-10-16 to 2026-10-16 |

**Myrna Melgar**

| Spender | Stance | Amount | Filings | Dates |
|---|---|---|---|---|
| San Francisco Tenants and Families for Affordable Housing, sponsored by communit | supports | $16,009 | 1 | 2020-10-15 to 2020-10-15 |
| Neighbors For A Better San Francisco | supports | $8,000 | 1 | 2020-10-08 to 2020-10-08 |
| San Francisco Labor Council Labor & Neighbor Independent Expenditure Political A | supports | $3,104 | 3 | 2020-10-30 to 2024-11-02 |
| Alice B. Toklas Lesbian and Gay Democratic Club PAC | supports | $2,006 | 2 | 2024-10-03 to 2024-10-28 |
| TogetherSF Action | opposes | $1,739 | 1 | 2024-10-23 to 2024-10-23 |

**Rafael Mandelman**

| Spender | Stance | Amount | Filings | Dates |
|---|---|---|---|---|
| Teachers, Nurses, Muni riders, neighbors and working families supporting Mandelm | supports | $49,100 | 11 | 2010-10-18 to 2010-11-02 |
| SAN FRANCISCO DEMOCRATIC COUNTY CENTRAL COMMITTEE | supports | $11,890 | 4 | 2010-10-21 to 2016-10-21 |
| Alliance For Jobs And Sustainable Growth, A Coalition Of Labor Unions And Busine | opposes | $10,202 | 1 | 2010-10-25 to 2010-10-25 |
| Harvey Milk LGBT Democratic Club PAC | supports | $6,973 | 1 | 2010-10-21 to 2010-10-21 |
| Alice B. Toklas Lesbian and Gay Democratic Club PAC | supports | $6,585 | 5 | 2018-04-13 to 2022-09-16 |
| Coalition to Grow San Francisco - Grow SF PAC | supports | $3,521 | 1 | 2022-09-29 to 2022-10-07 |

**Jackie Fielder**

| Spender | Stance | Amount | Filings | Dates |
|---|---|---|---|---|
| Building a Working SF Sponsored by Labor Organizations | supports | $54,306 | 3 | 2024-10-10 to 2024-10-24 |
| Families for a Vibrant San Francisco Supporting Trevor Chandler for Supervisor,  | opposes | $38,500 | 2 | 2024-10-11 to 2024-10-24 |
| Yes on B, Committee to Restore Police Minimum Staffing and Public Safety, Sponso | supports | $29,600 | 1 | 2024-10-12 to 2024-10-12 |
| TogetherSF Action | opposes | $2,686 | 1 | 2024-10-16 to 2024-10-16 |

**Shamann Walton**

| Spender | Stance | Amount | Filings | Dates |
|---|---|---|---|---|
| San Francisco Labor Council Labor & Neighbor Independent Expenditure Political A | supports | $106,888 | 12 | 2018-09-27 to 2022-10-24 |
| United Democratic Club Supporting Shamann Walton for D10 Supervisor 2018 | supports | $22,714 | 2 | 2018-10-27 to 2018-11-02 |
| San Francisco Deputy Sheriffs' Association Political Action Committee | supports | $8,045 | 1 | 2018-10-15 to 2018-10-16 |
| San Francisco Tenants and Families for Affordable Housing, sponsored by communit | supports | $3,890 | 1 | 2018-08-29 to 2018-08-29 |
| SAN FRANCISCO DEMOCRATIC COUNTY CENTRAL COMMITTEE | supports | $2,488 | 2 | 2014-10-08 to 2014-10-23 |

**Chyanne Chen**

| Spender | Stance | Amount | Filings | Dates |
|---|---|---|---|---|
| Building a Working SF Sponsored by Labor Organizations | supports | $296,872 | 16 | 2024-08-16 to 2024-11-01 |
| Fix our City SF, Sponsored by Labor Organizations | supports | $60,000 | 2 | 2024-10-11 to 2024-10-24 |
| Asian Americans for Representation | supports | $45,091 | 4 | 2024-09-06 to 2024-10-08 |
| Tenants and Families United PAC sponsored by Center for Empowered Politics | supports | $38,276 | 5 | 2024-09-06 to 2024-11-01 |
| Yes on B, Committee to Restore Police Minimum Staffing and Public Safety, Sponso | supports | $17,600 | 1 | 2024-10-01 to 2024-10-01 |
| San Francisco Working Families Voter Guide Supporting Aaron Peskin for Mayor, Sp | supports | $6,201 | 1 | 2024-10-25 to 2024-10-25 |


## 6. The city's limits on who may give, and where organisations' money reached

Rules as the Ethics Commission publishes them (read 2026-10-30): contributions to a candidate committee for City office are limited to $500 per source per election (<https://sfethics.org/guidance/campaigns/contributors/contributor-third-party-restrictions>); corporations, limited liability companies and limited liability partnerships may not contribute to candidate committees, though they may fund a separate segregated fund that does; non-candidate committees, including ballot-measure committees, are generally not limited, and candidate-controlled ballot-measure committees are not currently limited (<https://sfethics.org/ethics/2026/04/april-10-2026-agenda-item-5-report-discussion-on-proposed-campaign-finance-reforms-to-reinforce-contribution-limits-and-ensure-accountability-for-violations-of-city-law.html>); independent spending is not limited. A proposal to apply the limit to candidate-controlled committees was approved by the Commission in August 2026 and needs the Board of Supervisors, taking effect no earlier than 1 January 2027 (<https://growsf.org/news/2026-08-14-ethics-commission-campaign-finance-loopholes/>).

What the filings show, Schedule A by the relation of the receiving committee (all committees tied to the twelve officials, any year):

| Receiving committee | Individuals | Organisations and committees | Organisation share | Committee giver code COM |
|---|---|---|---|---|
| own committee, Mayor or Supervisor | $15,104,861 | $207,207 | 1.4% | $179,424 |
| own committee, another office | $762,542 | $220,249 | 22.4% | $118,099 |
| ballot-measure committee carrying the official's name | $13,035,270 | $5,585,000 | 30.0% | $1,389,000 |
| primarily formed committee supporting the official | $7,353,554 | $293,041 | 3.8% | $156,999 |
| primarily formed committee opposing the official | $309,840 | $20,000 | 6.1% | $20,000 |

Outside spending (form 496) naming the twelve officials, by whether the spender's name is taken by a donor family:

- Form 496 spending naming an official, all spenders: $11,061,689 over 78 spender-official-stance groups; of which by committees a donor family's names take: $1,135,826. Not added to any gift.
- Gifts by an official in their own name to their own and measure committees are inside the 'Individuals' column above: Rafael Mandelman $13,978; Myrna Melgar $8,467; Daniel Lurie $10,738,206; Bilal Mahmood $5,000.
- Of the spending, committees whose names state a sponsor: $1,943,621 (a sponsor such as 'Labor Organizations' names no single organisation).
