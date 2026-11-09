# Individual Life Underwriting Guidelines — Internal (Underwriter Use Only)

**Product scope:** Term 10/15/20/30, Universal Life (UL), Guaranteed UL (GUL). Issue ages 18–80.
**Audience:** Underwriters (UW), underwriting assistants, medical directors (MD). Not for distribution
to applicants or producers. Producers receive the separate *Field Guide*, which is a subset.
**Authority:** Decisions within these guidelines may be made at the UW's authority level (§GEN-3).
Anything marked **MD** requires medical director concurrence. Anything marked **CUO** requires the
Chief Underwriting Officer.

> Every rule has an ID (e.g. `TOB-2.1`). Cite rule IDs in the worksheet. If no rule applies, say so,
> cite `GRY-0`, and document the reasoning.

---

## GEN — General principles

**GEN-1 Underwrite the evidence, not the story.** A decision must be supportable from evidence in
file. Suspicion is a reason to order requirements, not a reason to rate.

**GEN-2 Disclosure.** The application (Part 1 and Part 2) is the applicant's representation.
- GEN-2.1 When third-party evidence (Rx, MIB, MVR, labs, APS) contradicts the application, the
  objective evidence controls the rating. Note the discrepancy in the file.
- GEN-2.2 A *material* misrepresentation (one that would change the class by ≥1 step, or change
  eligibility) discovered before issue: rate on the true facts, and add the note `MISREP` for the
  compliance queue. Do **not** decline solely for misrepresentation unless the true facts are
  declinable or the pattern is GEN-2.3.
- GEN-2.3 Two or more material misrepresentations in different categories (e.g. tobacco *and*
  DUI) → Decline (`GEN-2.3`, CUO notification).
- GEN-2.4 Honest mistakes (dates off by < 2 years, wrong drug name with right condition) are not
  misrepresentation. Correct and proceed.

**GEN-3 Authority levels.**

| Level | Max face (ages 18–65) | Max face (66–80) | May issue table ratings to | May decline |
|---|---|---|---|---|
| UW I | $1,000,000 | $500,000 | Table 4 | No (refer) |
| UW II | $3,000,000 | $1,000,000 | Table 8 | Yes |
| Senior UW | $10,000,000 | $3,000,000 | Table 16 | Yes |
| CUO | above | above | any | Yes |

**GEN-4 Insurance age** = age nearest birthday on the application signature date.

**GEN-5 Evidence currency.** Labs and paramed are valid 6 months (12 months if age < 50 and face ≤
$1M). APS covers what it covers; an APS with last visit > 24 months old is "stale" for active
conditions (order current APS or treat as uncontrolled — `APS-3`).

**GEN-6 Most-recent-value rule.** When multiple readings exist (BP, A1c, labs), use the **average
of the readings in the last 12 months** unless the guideline section says otherwise. A single
isolated outlier may be discarded if there are ≥ 3 other readings within range (document it).

---

## CLS — Risk classes and how to reach a decision

### CLS-1 Taxonomy

Two ladders. A case is on exactly one.

**Non-tobacco ladder (best → worst):** Elite · Preferred Plus · Preferred · Standard Plus · Standard ·
Table 1–16 · Postpone · Decline

**Tobacco ladder:** Preferred Tobacco · Standard Tobacco · Table Tobacco 1–16 · Postpone · Decline

**Modifiers (attach to any issued class):** flat extras (FE), exclusion endorsements (aviation,
avocation; where state-approved), rider approvals/denials, reduced face amount.

"Substandard" is an umbrella term = any Table rating and/or any flat extra. It is not a class.

### CLS-2 Ladder assignment
- CLS-2.1 Tobacco ladder if **any** of: tobacco/nicotine use within 12 months per §TOB; positive
  cotinine (`TOB-4`); smoking-cessation Rx within 12 months not explained by APS (`TOB-5`).
- CLS-2.2 Otherwise non-tobacco ladder.

### CLS-3 Debits, credits, and tables
- CLS-3.1 Each impairment chapter assigns **debits** (+) in units of 25 = one table.
- CLS-3.2 **Credits** (−) are available only per `CLS-6`. Credits never lift a case into Standard
  Plus or better and never offset Postpone/Decline triggers or flat extras.
- CLS-3.3 **Net debits → class**:

| Net debits | Non-tobacco ladder | Tobacco ladder | Notes "shorthand" |
|---|---|---|---|
| ≤ 0 | evaluate preferred matrix (CLS-5) | evaluate Pref Tobacco (CLS-5.6) | |
| +1 to +25 | Standard (max) | Standard Tobacco (max) | "std" / "100" |
| +26 to +50 | Table 1 (+25%) | Table Tobacco 1 | "T1", "A", "+125", "125%" |
| +51 to +75 | Table 2 (+50%) | Table Tobacco 2 | "T2", "B", "+150" |
| +76 to +100 | Table 3 (+75%) | Table Tobacco 3 | "C", "+175" |
| +101 to +125 | Table 4 (+100%) | Table Tobacco 4 | "D", "+200" |
| +126 to +150 | Table 5 | … | "E", "+225" |
| +151 to +175 | Table 6 | | "F", "+250" |
| +176 to +200 | Table 7 | | "G" |
| +201 to +225 | Table 8 | | "H", "+300" |
| +226 to +250 | Table 9 | | "I" |
| +251 to +275 | Table 10 | | "J" |
| +276 to +300 | Table 11 | | "K" |
| +301 to +325 | Table 12 | | "L" |
| +326 to +350 | Table 13 | | "M" |
| +351 to +375 | Table 14 | | "N" |
| +376 to +400 | Table 15 | | "O" |
| +401 to +425 | Table 16 (+400%) | Table Tobacco 16 | "P", "+500" |
| > +425 | Decline | Decline | |

Formula: Table = ceil((net − 25) / 25) for net in 26..425. Premium = Standard (or Standard Tobacco)
premium × (1 + 0.25 × Table).
- CLS-3.4 Issue-age limit on tables: ages 71–80 max Table 8; a higher indicated table at those
  ages → Decline (`CLS-8.1`).

### CLS-4 Order of operations (the worksheet)
Every worksheet follows these steps; skipped steps must still be shown as "n/a".
1. **Eligibility** — age, residence/citizenship (`FN`), face vs. financial justification (`FIN`).
2. **Ladder** — `CLS-2`.
3. **Knockouts** — any Decline trigger (`CLS-8`) → stop. Any Postpone trigger (`CLS-7`) → stop.
4. **Impairment debits** — one line per impairment with rule ID. Apply combination rules (`CMB`).
5. **Credits** — `CLS-6`, only if net debits after step 4 are > 0.
6. **Net debits → class** — `CLS-3.3`.
7. **If net ≤ 0** — preferred matrix (`CLS-5`) and per-chapter **class caps**; best class = the
   worst of (matrix result, all caps).
8. **Flat extras** — aviation, avocation, occupation, travel, certain cancers.
9. **Riders** — `RID`.
10. **Amount** — final face, reduced if `FIN` requires.

### CLS-5 Preferred criteria matrix (non-tobacco ladder)
A case qualifies for a class only if it meets **every** row for that class. Age band = insurance age.

| Criterion | Elite | Preferred Plus | Preferred | Standard Plus |
|---|---|---|---|---|
| Ages eligible | 18–65 | 18–75 | 18–80 | 18–80 |
| Build | Elite col. `BLD-1` | Pref Plus col. | Preferred col. | Std Plus col. |
| BP, ages 18–59 | ≤ 130/80, untreated | ≤ 135/85; treated OK | ≤ 140/90; treated OK | ≤ 145/90; treated OK |
| BP, ages 60+ | ≤ 135/85, untreated | ≤ 140/88; treated OK | ≤ 145/90; treated OK | ≤ 150/92; treated OK |
| Total cholesterol | ≤ 220, untreated | ≤ 250; treated OK | ≤ 280; treated OK | ≤ 300; treated OK |
| TC/HDL ratio | ≤ 4.5 | ≤ 5.0 | ≤ 5.5 | ≤ 6.5 |
| Nicotine-free | 10 yrs (any form) | 5 yrs | 3 yrs | 2 yrs |
| Family history (`FH-1`) | no parent/sibling CVD or cancer dx < 65 | no parent/sibling death from CVD/cancer < 60 | ≤ 1 parent/sibling death from CVD/cancer < 60 | any |
| MVR (`MVR-2`) | 0 moving viol. 5 yrs; no DUI/reckless ever | ≤ 1 moving in 3 yrs; no DUI 10 yrs | ≤ 2 moving in 3 yrs; no DUI 5 yrs | ≤ 3 moving in 3 yrs; no DUI 3 yrs |
| Alcohol/drug history | none | none in 10 yrs | none in 5 yrs | none in 3 yrs |
| Personal medical | no history of any ratable impairment, ever | no CAD, stroke, diabetes, cancer (except BCC/SCC skin) ever; no current ratable impairment | Chapter class caps permit | Chapter class caps permit |
| Aviation/avocation | none requiring FE or exclusion | none requiring FE | FE permitted only per `AVO-1.4` | FE permitted |
| Foreign travel/residence | Tier A only | Tier A/B | Tier A/B/C (≤ 4 wks C) | any issuable |
| Face amount | ≥ $250,000 | ≥ $100,000 | any | any |

- CLS-5.1 "Treated OK" means on medication with values at or below the threshold on treatment.
- CLS-5.2 **Standard Plus rule:** a case with net ≤ 0 that fails Preferred on **one or two** rows
  is Standard Plus if it meets every Standard Plus row. Failing Preferred on three or more rows →
  Standard regardless of Standard Plus thresholds.
- CLS-5.3 Failing Standard Plus on any row (with net ≤ 0) → Standard.
- CLS-5.4 The family-history row is waived at ages 70+ for all classes.
- CLS-5.5 Values exactly at a threshold qualify (≤ is inclusive).
- CLS-5.6 **Preferred Tobacco** requires: (a) no cigarette use in 12 months (cigarette users are
  capped at Standard Tobacco — `TOB-2.1`); (b) meets every **Preferred** row except nicotine-free;
  (c) net ≤ 0. Otherwise Standard Tobacco (net ≤ +25) or Table Tobacco.

### CLS-6 Credits
Available only to reduce net debits on a case with net > 0 after impairment debits. Maximum total
credit −50. Credits cannot produce a class better than Standard / Standard Tobacco.

| ID | Credit | Amount |
|---|---|---|
| CLS-6.1 | TC/HDL ratio ≤ 3.5 untreated | −15 |
| CLS-6.2 | BP ≤ 125/80 untreated (avg) | −10 |
| CLS-6.3 | Both parents alive past 80 (or died after 80 of non-CVD/cancer) | −15 |
| CLS-6.4 | Documented regular exercise in APS + resting pulse ≤ 65 | −10 |
| CLS-6.5 | NT-proBNP < 50 pg/mL (age 50+) | −10 |
| CLS-6.6 | Normal stress test / echo within 24 months (age 50+, non-cardiac case) | −10 |

Credits do **not** apply to: cardiac impairments rated per `CV` (sole exception: the `CV-1.2` LDL/stress-test modifier), any cancer, any substance use
chapter, any rating ≥ +150 before credits, and the tobacco-driven ladder change.

### CLS-7 Postpone triggers (stop; give reconsideration date)
| ID | Trigger | Reconsider after |
|---|---|---|
| CLS-7.1 | Diagnostic workup pending (biopsy, imaging, referral) for an unexplained finding | results + 3 mo |
| CLS-7.2 | Surgery scheduled or within last 3 months (non-trivial) | 3 mo post-op, full recovery |
| CLS-7.3 | Cancer under active treatment (excl. hormonal maintenance — see `CA`) | 6–24 mo per `CA` table |
| CLS-7.4 | MI, stent, CABG, stroke within 6 months | 6 mo |
| CLS-7.5 | Pregnancy with complication (pre-eclampsia, gestational DM uncontrolled) | 3 mo postpartum |
| CLS-7.6 | DUI within 12 months, or license currently suspended for DUI | 12 mo from DUI |
| CLS-7.7 | Completed alcohol/drug treatment within 12 months | 12 mo from completion |
| CLS-7.8 | Psychiatric hospitalization within 12 months | 12 mo |
| CLS-7.9 | Unexplained weight loss > 10% in 6 months | workup complete |
| CLS-7.10 | Pending criminal charges (felony) | disposition |
| CLS-7.11 | Underweight below `BLD-1.5` band without explanation | workup |

### CLS-8 Decline triggers (stop)
| ID | Trigger |
|---|---|
| CLS-8.1 | Net debits > +425 (or > Table 8 equivalent at ages 71–80) |
| CLS-8.2 | Any impairment listed "Decline" in its chapter |
| CLS-8.3 | Two DUIs within 5 years; or any DUI with injury/fatality within 10 years |
| CLS-8.4 | Current IV drug use; cocaine/methamphetamine/opioid misuse within 5 years (`DRG-2`) |
| CLS-8.5 | Incarceration current, or released < 2 years |
| CLS-8.6 | Applicant not physically present in US/approved jurisdiction at signing (`FN-1.5`) |
| CLS-8.7 | GEN-2.3 multiple material misrepresentations |
| CLS-8.8 | Financial over-insurance > 2× justified amount with no explanation (`FIN-2.4`) |
| CLS-8.9 | Terminal illness, or ADL dependency/cognitive impairment (ages 66+) per `GER` |

---

## BLD — Build

**BLD-1 Build chart.** Use measured height/weight from the paramed or exam if available (`GEN-5`);
otherwise application stated values. If paramed and application differ by > 15 lb, use paramed and
note it. Weights are maximums (columns) or minimums (left columns), in pounds.

{{BUILD_CHART}}

- BLD-1.1 A weight at or under a column's max qualifies for that column.
- BLD-1.2 Debits from the +25…+250 columns are impairment debits (they count in step 4).
- BLD-1.3 Heights outside 4'10"–6'8": compute BMI; use the same BMI bands (Elite ≤ 27.0, PP ≤ 28.5,
  P ≤ 30.0, SP ≤ 31.5, Std ≤ 33.0, then +25 per band as in the chart).
- BLD-1.4 Over the +250 column (BMI > 47) → Decline.
- BLD-1.5 Under "min +50" (BMI < 16) → Postpone pending explanation (`CLS-7.11`).
- BLD-1.6 **Build + other impairments:** if build debits ≥ +50 and the case also has diabetes,
  hypertension, sleep apnea, or CAD, add an extra +25 (`CMB-2`).
- BLD-1.7 Weight loss: documented intentional loss (bariatric surgery ≥ 12 months ago, stable
  weight 6 months) → use current weight; weight regain after bariatric surgery → current weight
  (no special treatment). Bariatric surgery < 12 months → use pre-op weight debits
  minus 50% (`GRY-3`).
- BLD-1.8 Ages 70+: use one column more lenient for Standard and above (e.g. a 70-year-old at
  the Std Plus max qualifies as Preferred on build only).

---

## BP — Blood pressure (as a preferred criterion and as an impairment)

BP-1 Use the average of all readings in the last 12 months (`GEN-6`): paramed readings (usually
3) plus APS readings. Report as systolic/diastolic average, rounded to the nearest whole number.

BP-2 Preferred thresholds are in `CLS-5`. Debits for hypertension are in `HTN`.

BP-3 A single paramed reading > 160/100 with no history → order a repeat BP (paramed recheck) or
APS before rating; if recheck unavailable, rate on the average of what you have.

---

## LIP — Cholesterol / lipids

- LIP-1 Use the most recent lab TC and HDL; ratio = TC/HDL rounded to one decimal.
- LIP-2 Preferred thresholds in `CLS-5`.
- LIP-3 Debits (impairment, step 4):

| Condition | Debits |
|---|---|
| TC ≤ 300 and ratio ≤ 7.0 | 0 |
| TC 301–350 or ratio 7.1–8.0 | +25 |
| TC 351–400 or ratio 8.1–9.0 | +50 |
| TC > 400 or ratio > 9.0 | +75; order APS (familial hypercholesterolemia) |

- LIP-3.1 Use the worse of the TC row and the ratio row; do not add both.
- LIP-4 HDL < 30 alone: +15 (no rating if ratio row already rated).
- LIP-5 Triglycerides: ≤ 500 ignore; 501–1000 +25; > 1000 +50 and screen for pancreatitis/DM.
- LIP-6 Labs from a non-fasting specimen: ignore triglycerides; TC/HDL still valid.
- LIP-7 Treated lipids: rate on treated values; statin use alone carries no debit.

---

## TOB — Tobacco and nicotine

**TOB-1 Definitions.** *Tobacco/nicotine use* = any cigarette, cigar, pipe, chewing tobacco, snuff,
snus, vaping/e-cigarette with nicotine, heated tobacco, or nicotine replacement (gum, patch,
lozenge). Marijuana is *not* tobacco (see `TOB-7`, `DRG-3`).

**TOB-2 Cigarettes.**
- TOB-2.1 **Any cigarette use within 12 months (admitted or proven) → tobacco ladder, best class
  Standard Tobacco.** Preferred Tobacco is not available to cigarette smokers.
- TOB-2.2 Cigarettes quit 12–24 months ago → non-tobacco ladder, best class **Standard** (fails the
  Standard Plus nicotine-free row).
- TOB-2.3 Quit-date ladder (all nicotine forms, from `CLS-5` nicotine-free row): quit 24–36 mo →
  best Standard Plus; 3–5 yrs → best Preferred; 5–10 yrs → best Preferred Plus; ≥ 10 yrs → Elite
  eligible. Unknown/undocumented quit date → treat as the most recent date consistent with the
  evidence (`GRY-4`).
- TOB-2.4 Heavy history: ≥ 30 pack-years (current or quit < 10 yrs), age 50+ → order NT-proBNP
  and spirometry/APS if any respiratory symptoms in file; +25 debit if FEV1 not documented normal.

**TOB-3 Other tobacco/nicotine.**
- TOB-3.1 Cigars: ≤ 12 per year, **negative cotinine**, admitted on app → non-tobacco ladder,
  best class Preferred. Cotinine positive → tobacco ladder (Preferred Tobacco eligible).
- TOB-3.2 Pipe, chew, snuff, vape, heated tobacco, NRT within 12 months → tobacco ladder;
  Preferred Tobacco eligible (`CLS-5.6`).
- TOB-3.3 NRT used only as part of a cessation program, quit date documented in APS ≥ 12 months
  before app → non-tobacco; NRT within 12 months → tobacco ladder.

**TOB-4 Cotinine.**
- TOB-4.1 Urine cotinine ≥ 200 ng/mL, or saliva (oral fluid) cotinine ≥ 30 ng/mL = positive.
- TOB-4.2 Positive cotinine with app denial of all nicotine → tobacco ladder; apply `GEN-2.2` if
  the app said no nicotine in 12 months; best class Standard Tobacco (treated as if cigarettes
  unless the applicant later provides a signed statement of the actual product — then `TOB-3`).
- TOB-4.3 Borderline urine cotinine 100–199: non-tobacco ladder, but best class Standard Plus; note
  passive exposure/NRT question.
- TOB-4.4 Legacy lab reports (before 2019) may show cotinine as "POS/NEG" at a 500 ng/mL screening
  cutoff. A "NEG" on a legacy report is acceptable as negative only if within `GEN-5` currency.

**TOB-5 Rx evidence.** Varenicline or bupropion-SR/Zyban fill within 12 months is evidence of
tobacco use within 12 months unless (a) bupropion is clearly for depression (`RX-2.3`) or (b) APS
documents a quit date ≥ 12 months before app. Varenicline = tobacco ladder absent (b).

**TOB-6 Lookbacks are measured from the application signature date to the last use date.**

**TOB-7 Marijuana** (smoked, vaped, edible): non-tobacco ladder if cotinine negative. Frequency
rules in `DRG-3`.

---

## FH — Family history

- FH-1 Count only biological parents and siblings. Relevant conditions: coronary artery disease,
  MI, stroke, cardiomyopathy, sudden cardiac death (CVD); and cancers of breast, ovary, colon,
  prostate, pancreas; melanoma (Cancer). Other conditions are not counted.
- FH-1.1 "Dx < 65" (Elite) counts diagnosis age; PP/P count **death** age.
- FH-1.2 Unknown family history (adopted, no information) → treat as meeting Preferred but not PP or
  Elite.
- FH-2 Family history alone never generates debits **except**: two or more parents/siblings with
  CVD death < 60 → +25 (non-tobacco and tobacco ladders), waived if applicant age 60+ with normal
  stress test or coronary calcium score 0 within 24 months.
- FH-3 Hereditary syndromes (BRCA1/2, Lynch, familial hypercholesterolemia, hypertrophic
  cardiomyopathy) in a first-degree relative: applicant **tested negative** → ignore; **untested**
  → best class Preferred; **tested positive** → see `CA-9` / `CV-9`.
- FH-4 Waived entirely at ages 70+ (`CLS-5.4`).
