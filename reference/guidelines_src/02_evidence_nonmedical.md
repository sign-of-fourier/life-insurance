
---

## REQ — Requirements (what to order and when)

**REQ-1 Age/amount grid (routine requirements).** Ordered automatically at app intake. "Accel" =
accelerated path: no fluids, no paramed if all `REQ-3` checks pass.

| Insurance age | ≤ $250K | $250,001–$1M | $1,000,001–$3M | $3,000,001–$10M | > $10M |
|---|---|---|---|---|---|
| 18–40 | Accel | Accel | PM, B, U | PM, B, U, EKG, FIN-Q | + 2 yr APS, inspection report |
| 41–50 | Accel | PM, B, U | PM, B, U | PM, B, U, EKG, FIN-Q | + APS, NT-proBNP |
| 51–60 | PM, S | PM, B, U | PM, B, U, EKG | PM, B, U, EKG, FIN-Q, APS | + stress test (MD) |
| 61–70 | PM, B, U | PM, B, U, EKG | PM, B, U, EKG, APS | PM, B, U, EKG, APS, FIN-Q | CUO |
| 71–80 | PM, B, U, APS, COG | PM, B, U, EKG, APS, COG | + FIN-Q | CUO | CUO |

Codes: PM = paramedical exam (height, weight, BP ×3, pulse); B = blood profile; U = urinalysis;
S = oral fluid (saliva) panel (cotinine, HIV, cocaine); EKG = resting 12-lead; APS = attending
physician statement (primary care, last 5 years); COG = cognitive screen (`GER`);
FIN-Q = financial questionnaire; NT-proBNP is part of B when ordered.

Always ordered regardless of grid (at intake): **MIB check, Rx history, MVR** (ages ≤ 75; ages 76+
only if the applicant still drives per app).

**REQ-2 Underwriter-triggered requirements.** Order when evidence suggests an impairment the
routine requirements will not resolve. Each impairment chapter lists its "Order:" items.
- REQ-2.1 Any disclosed or indicated (Rx/MIB) impairment with debits ≥ +50 possible → APS from the
  treating provider.
- REQ-2.2 Discrepancy between app and Rx/MIB on a ratable condition → APS (and fluids if accel).
- REQ-2.3 Positive or ambiguous tobacco evidence on an accel case → oral fluid (S) for cotinine.
- REQ-2.4 MVR with DUI in 5 years → alcohol questionnaire + blood (CDT, GGT).
- REQ-2.5 Aviation/avocation disclosed → corresponding questionnaire (`AVI-1`, `AVO-1`).
- REQ-2.6 Foreign national or foreign travel > 4 wks/yr to Tier C → foreign questionnaire (`FN`, `TRV`).
- REQ-2.7 Do not order what cannot change the decision (e.g. an APS for a condition already at
  Decline from objective evidence). Note "not ordered — would not change outcome".

**REQ-3 Accelerated path eligibility.** All must be true; otherwise convert to fluids per next
column of the grid: no "Yes" answers to Part 2 medical questions except the allowed list (seasonal
allergies, resolved minor injuries, uncomplicated pregnancy, contraception, acne, GERD on PPI only);
Rx history shows no drug flagged "high-impact" in `RX-2`; MIB returns no codes in categories 1–6
within 10 yrs; MVR no major violations 5 yrs; build within Standard column; face ≤ grid limit.
Accelerated cases may be issued at any class except Elite (Elite requires fluids).

**REQ-4 APS handling.** Order from the provider with the most visits in the last 3 years (Rx
prescriber data identifies them). Up to two APSs on routine cases; more requires note justifying.
An APS outstanding > 45 days: issue on available evidence if rateable, else close as incomplete.

---

## MVR — Motor vehicle record

- MVR-1 Lookback from application date. Violations are classified in `reference/mvr_codes.yaml`
  as **minor moving** (speeding ≤ 25 over, failure to yield, improper lane change, etc.),
  **major** (reckless driving, speeding > 25 over, driving while suspended, leaving the scene,
  eluding), **DUI** (DUI/DWI/OWI, refusal of chemical test), and **non-moving** (equipment,
  registration, parking — always ignore).

- MVR-2 Preferred limits in `CLS-5`.

- MVR-3 Debits:

| Record (3 yrs unless stated) | Debits |
|---|---|
| ≤ 3 minor | 0 |
| 4 minor | +25 |
| 5–6 minor | +50 |
| ≥ 7 minor | Decline |
| 1 major | +25 |
| 2 major (5 yrs) | +75 |
| ≥ 3 major (5 yrs) | Decline |
| 1 DUI 1–2 yrs ago | +75 (and best class Standard) |
| 1 DUI 2–5 yrs ago | +25 (best class Standard Plus) |
| 1 DUI 5–10 yrs ago | 0 (best class Preferred) |
| DUI < 12 months | Postpone (`CLS-7.6`) |
| 2 DUIs in 5 yrs | Decline (`CLS-8.3`) |

- MVR-3.1 Minor + major combinations: compute each row and add.
- MVR-3.2 Accidents (at-fault) count as 1 minor; at-fault with injury counts as 1 major.
- MVR-3.3 DUI + alcohol chapter: DUI debits and `ALC` debits are added (they are separate risks).
- MVR-4 MVR "no record found" for a stated licensed driver aged 21+ → note; not ratable. Foreign
  license only → MVR n/a; use `FN-2`.

---

## RX — Prescription history

- RX-1 Rx history lists fills (drug, strength, quantity, days supply, fill date, prescriber,
  pharmacy). It does **not** list diagnoses. Infer indication from drug + prescriber specialty +
  pattern, and confirm with APS when the drug is high-impact.
- RX-2 Drug classes and default interpretation are in `reference/rx_map.yaml`. Each drug is
  tagged **high-impact** (likely ratable; order APS if undisclosed), **ambiguous** (multiple
  plausible indications; see list), or **low-impact** (ignore).
  - RX-2.1 A single fill of a drug ≥ 3 years ago with no refills: treat as resolved; ignore unless
    high-impact oncology/HIV/antipsychotic.
  - RX-2.2 Ongoing fills (≥ 3 fills in 12 months) = active condition.
  - RX-2.3 Ambiguous drugs: metoprolol/propranolol (HTN, arrhythmia, migraine, anxiety, tremor),
    gabapentin (neuropathy — check DM; pain; seizure; anxiety), bupropion (depression vs. cessation
    — dose/duration: 150 mg BID > 12 wks = depression), trazodone (sleep vs. depression), prednisone
    (short burst = acute, ignore; chronic = autoimmune/COPD), metformin (DM vs. PCOS vs.
    prediabetes — check A1c and sex), spironolactone (HTN, CHF, acne/hirsutism in women),
    hydroxychloroquine (lupus/RA vs. travel prophylaxis), amitriptyline (depression, neuropathy,
    migraine, sleep), clonidine (HTN, ADHD, withdrawal), topiramate (seizure, migraine, weight).
  - RX-2.4 When ambiguous and no APS, rate the **least severe** plausible indication supported by
    other evidence, and document (`GRY-2`).
- RX-3 Undisclosed high-impact fills → `GEN-2.1`, `REQ-2.2`.
- RX-4 "No Rx history found" is common for young healthy applicants and for foreign nationals; it is
  not evidence of anything.

---

## MIB — Medical Information Bureau

- MIB-1 MIB codes are **alerts**, not evidence. **Never rate on an MIB code alone.** A code tells
  you a prior insurer received information; you must corroborate with app admission, Rx, labs, or
  APS before rating.
- MIB-2 Code structure (full codebook: `reference/mib_codebook.md`): six digits `SSC D R Q`
  — `SSC` (3) condition (first digit = body system), `D` degree/severity, `R` source of the
  information, `Q` qualifier (time/treatment). Decode every code and write the decode in notes.
- MIB-3 Code older than 7 years (per report date) → informational only; ignore unless it relates to
  a currently disclosed condition.
- MIB-4 Code for a condition **not disclosed** on the app and within 7 years → order APS for that
  condition (`REQ-2.2`). If APS negative/not found, ignore the code and note "MIB not corroborated".
- MIB-5 Foreign nationals and recent immigrants (< 5 yrs in US): MIB "no record" carries no weight;
  require the full fluid set and a foreign APS or US APS of 12 months (`FN-2`).
- MIB-6 Codes in the "administrative/non-medical" range (e.g. prior applications, hazardous
  avocation alerts) route to the relevant non-medical chapter.

---

## LAB — Laboratory values

**LAB-1 Units.** Rules use US conventional units. Convert SI before applying: cholesterol mmol/L ×
38.67 = mg/dL; glucose mmol/L × 18 = mg/dL; creatinine µmol/L ÷ 88.4 = mg/dL; A1c IFCC mmol/mol →
NGSP %: (IFCC/10.929) + 2.15. Lab reports from different vendors flag differently; **do not rely
on vendor flags** — apply these thresholds.

**LAB-2 Values and actions (adults).**

| Test | Normal for UW | Action / debits |
|---|---|---|
| Glucose (fasting) | ≤ 109 | 110–125: check A1c; > 125: diabetes workup (`DM`) |
| Glucose (non-fasting) | ≤ 139 | ≥ 200: treat as diabetes pending A1c |
| HbA1c | < 5.7 | 5.7–6.4 prediabetes (`DM-1`); ≥ 6.5 diabetes (`DM-2`) |
| Fructosamine (legacy A1c substitute, pre-2015 reports) | ≤ 285 µmol/L | 286–350 = treat as A1c 6.0–7.0; > 350 = treat as A1c > 7.5 |
| AST, ALT (U/L) | ≤ 1.5× ULN | 1.5–3× ULN: +25; > 3× ULN: APS; > 5× ULN: Postpone |
| GGT (U/L) | ≤ 2× ULN | 2–3× ULN: +25 (+50 if CDT also elevated); > 3× ULN: +50, alcohol workup |
| Alkaline phosphatase | ≤ 1.5× ULN | > 1.5× ULN: +25 unless bone source / pregnancy |
| Bilirubin total | ≤ 1.5 mg/dL | Isolated ≤ 3.0 with normal LFTs: Gilbert's, 0; else APS |
| CDT (%dCDT) | < 1.7% | 1.7–2.4: +25; ≥ 2.5: +50 and `ALC` |
| Creatinine / eGFR | eGFR ≥ 60 | see `REN` |
| Urine protein | ≤ 30 mg/dL | see `REN-2` |
| Urine glucose | negative | positive with normal A1c: renal glycosuria, 0; else `DM` |
| Urine blood (RBC) | ≤ 5 /hpf | > 5: +0 if female and menstruating noted; else APS/repeat |
| Hemoglobin (g/dL) | M 13–17.5, F 12–15.5 | < 10: Postpone, workup; 10–lower limit: +25 if unexplained |
| PSA (males 40+) | age-adjusted (< 2.5 <50; < 3.5 50–59; < 4.5 60–69; < 6.5 70+) | above: APS/urology; > 10 untreated: Postpone |
| NT-proBNP (pg/mL) | < 125 (age < 75), < 450 (75+) | 125–299: +25; 300–899: +75, order cardiac APS; ≥ 900: Decline unless explained (renal) |
| Albumin | ≥ 3.5 g/dL | < 3.5: +25 (malnutrition/liver) |
| HIV (B or S) | negative | positive: see `IMM-1` |
| Cocaine metabolite (U or S) | negative | positive: `DRG-2` (Decline) |
| Cotinine | `TOB-4` | |

- LAB-3 Lab panel naming differs: some vendors report "Lipid ratio" only (no HDL), some report
  "Non-HDL". Ratio-only reports are acceptable for `CLS-5`; Non-HDL is not a substitute for HDL.
- LAB-4 Legacy test methods: reports before 2015 may show fructosamine instead of A1c (use the
  conversion row); before 2019 cotinine may be qualitative (`TOB-4.4`).
- LAB-5 Hemolyzed / insufficient specimen: values affected (potassium, LDH, AST) are disregarded;
  re-draw only if the result could change class.

---

## APS — Attending physician statements

- APS-1 Read the most recent 24 months first; then the problem list; then older history only for
  ratable conditions.
- APS-2 Diagnoses in a problem list without supporting visit notes, tests, or treatment ("history
  of", "r/o", "rule out") are not rated unless corroborated. "R/O" = suspected, not diagnosed.
- APS-3 Stale APS (last visit > 24 months) for an active ratable condition: rate as **uncontrolled
  / worst documented** for that condition, or obtain current records. Document choice (`GRY-5`).
- APS-4 Physician non-compliance notes ("pt non-compliant with meds", "no-showed ×3") → +25 on the
  condition being treated (on top of its chapter debits).
- APS-5 Conflicting values between APS and paramed: average per `GEN-6`.
- APS-6 Condition with no APS in file (not ordered under `REQ-2.7`, or not received): rate on the
  application, Rx, and labs; when the severity attributes a chapter needs are not documented, use the
  chapter's unqualified (default) row and document `GRY-5`.

---

## FIN — Financial justification

- FIN-1 **Income replacement multiples** (total in-force + applied for, all carriers):

| Age | Max multiple of earned income |
|---|---|
| 18–40 | 30× |
| 41–50 | 20× |
| 51–60 | 15× |
| 61–65 | 10× |
| 66–70 | 5× |
| 71–80 | net worth basis only (≤ 50% of net worth) |

- FIN-1.1 Non-working spouse: up to 100% of the working spouse's in-force coverage, max $3M.
- FIN-1.2 Students / no income (age 18–24): up to $500K if parents insured for ≥ the amount.
- FIN-1.3 Retirees and other applicants with no earned income (not covered by FIN-1.1/1.2): justified
  amount = the greater of stated income × the age multiple and 50% of net worth.
- FIN-2 Over the limit:
  - FIN-2.1 ≤ 10% over → issue as applied, note.
  - FIN-2.2 10%–100% over → counter-offer the justified amount (`approved_face_amount`).
  - FIN-2.3 Business/key-person coverage (KPE rider): the endorsement requires face ≤ 10× the key
    person's compensation and a FIN-Q; if not met, decline the endorsement (`RID-2`) and justify the
    base policy under FIN-1.
  - FIN-2.4 > 100% over with no business purpose → Decline (`CLS-8.8`).
- FIN-3 Replacement of existing coverage with a lapse of the old policy is allowed; count only net
  new coverage.

---

## FN — Foreign nationals, residency, citizenship

- FN-1 Eligibility:
  - FN-1.1 US citizens residing abroad: Tier A/B countries eligible to $5M; Tier C to $1M at
    Standard or worse; Tier D Decline.
  - FN-1.2 Permanent residents (green card): treat as US citizens.
  - FN-1.3 Visa holders (H-1B, L-1, E-2, O-1, TN): eligible if ≥ 12 months in US and intent to
    remain; best class Preferred; face ≤ $3M.
  - FN-1.4 Other visas (F-1 student, B-1/B-2, no status): Decline (non-resident) except F-1
    dependent of an eligible visa holder (≤ $250K, Standard best).
  - FN-1.5 Must sign app and complete medical requirements in the US.
- FN-2 Evidence for foreign nationals/recent immigrants (< 5 yrs in US): full fluids regardless of
  age/amount; US APS covering ≥ 12 months or translated foreign medical records; MIB/Rx/MVR absence
  is not favorable evidence (`MIB-5`, `RX-4`).
- FN-3 Country tiers: `reference/country_tiers.yaml`. Tier A (e.g. Canada, UK, Western EU, Japan,
  Australia, NZ, Singapore); Tier B (e.g. Mexico—non-border states, Brazil, China, India, Chile,
  Eastern EU, South Korea, UAE); Tier C (e.g. Colombia, Egypt, Philippines, Peru, Kenya, Turkey);
  Tier D (e.g. Afghanistan, Syria, Yemen, Somalia, South Sudan, Libya, regions under travel ban).

## TRV — Foreign travel

| Destination tier | ≤ 4 wks/yr | 4–13 wks/yr | > 13 wks/yr |
|---|---|---|---|
| A | none | none | none |
| B | none | none | best Preferred |
| C | best Preferred | FE $2.50/1000 or best Standard | FE $5/1000, max face $1M |
| D | Decline | Decline | Decline |

- TRV-1 Humanitarian/military contractor travel to Tier C/D zones → refer (Senior UW), usually FE
  $7.50–$10 or Decline.
- TRV-2 Past travel is not rated; only planned/ongoing travel in the next 24 months.

---

## OCC — Occupation

Occupation classes (`reference/occupations.yaml`):

| Class | Examples | Rating |
|---|---|---|
| 1A | office, professional, retail management | none |
| 2A | skilled trades indoors, nurse, teacher, sales with driving | none |
| 3A | HVAC, electrician, roofer (≤ 3 stories), police patrol, firefighter (municipal) | none; Elite not available for police/fire |
| 4A | commercial fisher, logger, structural steel worker > 3 stories, offshore oil, long-haul truck with MVR issues | FE $2.50–$5/1000 |
| 5A | bomb disposal, wildland smoke jumper, mercenary/private security abroad, active-duty special forces deploying | FE $7.50/1000 or Decline (Senior UW) |

- OCC-1 Military: active duty non-deploying → no rating; deployment orders to a combat zone within
  12 months → Postpone until return (or war-exclusion where filed).
- OCC-2 Commercial pilots on scheduled airlines → no aviation rating (`AVI-2`).

## AVO — Avocations (hazardous sports)

| Activity | Criteria | Rating |
|---|---|---|
| Scuba | ≤ 100 ft, certified, ≤ 50 dives/yr | none |
| Scuba | 100–130 ft or > 50 dives/yr | FE $2.50/1000 |
| Scuba | > 130 ft, cave, wreck penetration, solo | FE $5/1000; > 200 ft Decline |
| Skydiving | ≤ 50 jumps/yr | FE $2.50/1000 |
| Skydiving | > 50 jumps/yr or wingsuit | FE $5/1000; BASE jumping Decline |
| Mountain climbing | ≤ 14,000 ft, established routes | none |
| Mountain climbing | 14,000–20,000 ft | FE $3/1000 |
| Mountain climbing | > 20,000 ft or ice/solo technical | FE $7.50/1000; > 26,000 ft Decline |
| Motor racing | amateur, ≤ 10 events/yr, sanctioned | FE $2.50/1000 |
| Motor racing | professional or speeds > 150 mph | FE $5/1000 or exclusion |
| Hang gliding / paragliding | ≤ 25 flights/yr | FE $2.50/1000 |
| Hang gliding / paragliding | > 25 flights/yr or competition | FE $5/1000 |
| Heli-skiing / backcountry skiing | any | FE $2.50/1000 |
| Rodeo, bull riding | competitive | FE $5/1000 |

- AVO-1.1 Amateur activities not listed (hunting, recreational boating, marathon running,
  martial arts) → no rating.
- AVO-1.2 Avocation FE is temporary only if the applicant states intent to stop; otherwise permanent.
- AVO-1.3 Multiple avocations: FEs add.
- AVO-1.4 Preferred class allowed with an avocation FE ≤ $2.50/1000; FE > $2.50 → best Standard Plus.
- AVO-1.5 Exclusion endorsement may replace the FE at applicant request where state-approved; with
  exclusion, class is unaffected.

## AVI — Aviation

- AVI-1 Private pilots (aviation questionnaire required):

| Pilot profile | Rating |
|---|---|
| ≥ 100 total hrs, ≤ 200 hrs/yr, IFR rated, age 18–70 | none |
| ≥ 100 total hrs, not IFR rated | none if ≤ 100 hrs/yr; else FE $2.50/1000 |
| < 100 total hrs (student/new pilot) | FE $2.50/1000 (temporary 2 yrs) |
| Homebuilt/experimental/ultralight | FE $2.50–$5/1000 |
| Crop dusting, firefighting, test flying, aerobatics | FE $5–$10/1000 or exclusion |
| Age 71+ | FE $2.50/1000 minimum |

- AVI-1.1 Pilot with any rated medical impairment ≥ +75 → aviation exclusion required or Decline.
- AVI-1.2 Aviation rating combines with class per `AVO-1.4`.
- AVI-2 Commercial airline pilots and crew → no aviation rating.

## ALC — Alcohol

| History | Debits / action |
|---|---|
| ≤ 14 drinks/wk, no history | 0 |
| 15–21 drinks/wk, normal LFT/CDT | +25; best Standard Plus |
| 22–35 drinks/wk or abnormal LFT/CDT | +50 to +75; best Standard |
| > 35 drinks/wk | +100 to Decline (MD) |
| Alcohol use disorder, abstinent with treatment completed: < 1 yr | Postpone (`CLS-7.7`) |
| 1–2 yrs abstinent | +75 |
| 2–5 yrs abstinent | +25 |
| > 5 yrs abstinent | 0; best Preferred (≥ 10 yrs → PP eligible) |
| Relapse after treatment | add +50 to the abstinence row; ≥ 2 relapses Decline |

- ALC-1 Drinks/wk from app vs. APS: use the **higher**.
- ALC-2 CDT ≥ 2.5 with app ≤ 14 drinks/wk → treat as 22–35 row and note `GEN-2.1`.

## DRG — Drugs and controlled substances

- DRG-1 Prescribed controlled substances taken as directed → rate the underlying condition.
- DRG-2 Cocaine, methamphetamine, heroin, illicit opioids: current/within 5 yrs → Decline; 5–10 yrs
  abstinent → +50; > 10 yrs abstinent → 0, best Standard Plus. Positive cocaine metabolite → Decline.
- DRG-3 Marijuana (legal states and otherwise): ≤ 2 uses/wk → 0 (non-tobacco ladder if cotinine
  neg., best Preferred Plus); 3–7 uses/wk → best Standard Plus; daily multiple times → +25, best
  Standard; with DUI involving marijuana → `MVR-3` DUI rows.
- DRG-4 Opioid use disorder on buprenorphine/methadone maintenance: < 2 yrs → Decline; ≥ 2 yrs
  stable, compliant → +100 (MD).

---

## RID — Riders

Rider codes are used throughout notes. Approval is decided after the base class.

| Code | Rider | Eligibility / UW rules |
|---|---|---|
| **WP** | Waiver of Premium (premiums waived during total disability > 6 mo, to age 65) | Ages 18–55. Class Standard Tobacco or better and Table ≤ 4. Decline WP if: any back/spine impairment rated, any psychiatric impairment rated, any FE for occupation, BMI > 40, or applicant unemployed/non-earning. |
| **WMD** | Waiver of Monthly Deduction (UL version of WP) | Same rules as WP. |
| **ADB** | Accidental Death Benefit (extra face for accidental death, max $250K) | Ages 18–65. Decline if: any MVR major/DUI in 5 yrs, any avocation/aviation FE, alcohol/drug rating, Occupation 4A/5A. Table ≤ 4. |
| **CTR** | Children's Term Rider ($5K–$25K per child) | Base insured age 18–55; any class except Decline/Postpone. Children reviewed only by short questions; any child with serious impairment → CTR declined. |
| **GIO** | Guaranteed Insurability Option (buy more later without evidence) | Ages 18–40; class Standard or better (non-tobacco or tobacco); no FE; no Table. |
| **ABR** | Accelerated Benefit Rider — terminal illness | Free, attached to all issued policies; no UW action. |
| **CIA** | Chronic Illness Acceleration (accelerate for ADL loss) | Ages 18–75; Table ≤ 2; decline if any neuro/cognitive impairment rated (MS, Parkinson's, prior stroke) or ages 66+ with any `GER` finding. |
| **XCR** | Extended Conversion Rider (term convertible to age 75 instead of 65) | Any class Standard Plus or better; ages ≤ 60. |
| **OIR** | Other-Insured Rider (term coverage on spouse/partner) | The other insured is fully underwritten as a mini-case; OIR class may differ from base; document separately. Max OIR face = base face. |
| **ROP-T** | Return of Premium (term) | Term 20/30 only; ages 18–55; class Table 2 or better. |
| **KPE** | Key-Person Endorsement (business owner, salary-continuation link) | FIN-2.3 met; any issuable class; requires FIN-Q. |
| **LTA** | Level Term Addition (adds 10-yr term layer on UL) | Ages 18–65; class Table 4 or better; total face within FIN-1. |

- RID-1 A rider decline does not change the base class.
- RID-2 Riders requested but ineligible are declined with reason code in the notes.
