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

| Ht | min +50 | min +25 | min Std | Elite | Pref Plus | Preferred | Std Plus | Standard | +25 | +50 | +75 | +100 | +150 | +200 | +250 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4'10" | 77 | 82 | 87 | 129 | 136 | 143 | 150 | 157 | 167 | 177 | 186 | 196 | 205 | 215 | 224 |
| 4'11" | 80 | 85 | 90 | 133 | 141 | 148 | 155 | 163 | 173 | 183 | 193 | 203 | 212 | 222 | 232 |
| 5'0" | 82 | 88 | 93 | 138 | 145 | 153 | 161 | 168 | 179 | 189 | 199 | 209 | 220 | 230 | 240 |
| 5'1" | 85 | 90 | 96 | 142 | 150 | 158 | 166 | 174 | 185 | 195 | 206 | 217 | 227 | 238 | 248 |
| 5'2" | 88 | 93 | 99 | 147 | 155 | 164 | 172 | 180 | 191 | 202 | 213 | 224 | 235 | 246 | 256 |
| 5'3" | 91 | 96 | 102 | 152 | 160 | 169 | 177 | 186 | 197 | 208 | 220 | 231 | 242 | 254 | 265 |
| 5'4" | 94 | 100 | 105 | 157 | 166 | 174 | 183 | 192 | 203 | 215 | 227 | 238 | 250 | 262 | 273 |
| 5'5" | 97 | 103 | 109 | 162 | 171 | 180 | 189 | 198 | 210 | 222 | 234 | 246 | 258 | 270 | 282 |
| 5'6" | 100 | 106 | 112 | 167 | 176 | 185 | 195 | 204 | 216 | 229 | 241 | 254 | 266 | 278 | 291 |
| 5'7" | 103 | 109 | 115 | 172 | 181 | 191 | 201 | 210 | 223 | 236 | 249 | 261 | 274 | 287 | 300 |
| 5'8" | 106 | 112 | 119 | 177 | 187 | 197 | 207 | 217 | 230 | 243 | 256 | 269 | 282 | 295 | 309 |
| 5'9" | 109 | 116 | 122 | 182 | 193 | 203 | 213 | 223 | 237 | 250 | 264 | 277 | 291 | 304 | 318 |
| 5'10" | 112 | 119 | 126 | 188 | 198 | 209 | 219 | 230 | 243 | 257 | 271 | 285 | 299 | 313 | 327 |
| 5'11" | 115 | 122 | 130 | 193 | 204 | 215 | 225 | 236 | 250 | 265 | 279 | 293 | 308 | 322 | 337 |
| 6'0" | 118 | 126 | 133 | 199 | 210 | 221 | 232 | 243 | 258 | 272 | 287 | 302 | 317 | 331 | 346 |
| 6'1" | 122 | 129 | 137 | 204 | 216 | 227 | 238 | 250 | 265 | 280 | 295 | 310 | 325 | 341 | 356 |
| 6'2" | 125 | 133 | 141 | 210 | 222 | 233 | 245 | 257 | 272 | 288 | 303 | 319 | 334 | 350 | 366 |
| 6'3" | 129 | 137 | 145 | 216 | 228 | 240 | 252 | 264 | 280 | 296 | 312 | 328 | 344 | 360 | 376 |
| 6'4" | 132 | 140 | 148 | 221 | 234 | 246 | 258 | 271 | 287 | 304 | 320 | 336 | 353 | 369 | 386 |
| 6'5" | 135 | 144 | 152 | 227 | 240 | 253 | 265 | 278 | 295 | 312 | 328 | 345 | 362 | 379 | 396 |
| 6'6" | 139 | 148 | 156 | 233 | 246 | 259 | 272 | 285 | 302 | 320 | 337 | 354 | 372 | 389 | 406 |
| 6'7" | 143 | 151 | 160 | 239 | 253 | 266 | 279 | 292 | 310 | 328 | 346 | 363 | 381 | 399 | 417 |
| 6'8" | 146 | 155 | 164 | 245 | 259 | 273 | 286 | 300 | 318 | 336 | 355 | 373 | 391 | 409 | 427 |


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
- FIN-1.3 Income for retirees = 50% of net worth basis.
- FIN-2 Over the limit:
  - FIN-2.1 ≤ 10% over → issue as applied, note.
  - FIN-2.2 10%–100% over → counter-offer the justified amount (`approved_face_amount`).
  - FIN-2.3 Business/key-person coverage: use 10× key person's compensation; requires FIN-Q.
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


---

# Medical impairment chapters

Each chapter gives: **Order** (requirements to resolve), **Debits**, **Best class** (cap applied in
CLS-4 step 7 when net ≤ 0, and also the best class reachable if debits are small), and
Postpone/Decline triggers. "Best class Standard" means the case can be no better than Standard /
Standard Tobacco even with 0 debits.

## HTN — Hypertension

Order: APS if treated with ≥ 2 agents, or any BP avg > 150/95, or end-organ findings.

| Treated/untreated BP average (`BP-1`) | Debits |
|---|---|
| ≤ 140/90 | 0 |
| 141–150 / 91–95 | +25 |
| 151–160 / 96–100 | +50 |
| 161–170 / 101–105 | +75 |
| 171–180 / 106–110 | +100 |
| > 180 / > 110 | Postpone pending control |

- HTN-1 Use the worse of systolic and diastolic rows.
- HTN-2 Ages 60+: subtract one row for systolic only (e.g. 145/85 at 65 = 0).
- HTN-3 End-organ damage: LVH on EKG/echo +25; proteinuria → `REN`; retinopathy +25.
- HTN-4 ≥ 3 antihypertensive agents: +25 (resistant HTN), best Standard.
- HTN-5 Best class: treated ≤ 1 agent and controlled → Preferred Plus (per `CLS-5`); 2 agents →
  Preferred; ≥ 3 → Standard.

## CV — Cardiovascular

Order: cardiac APS (cardiologist), EKG, NT-proBNP; stress test/echo per MD.

**CV-1 Coronary artery disease (CAD), MI, stent (PCI), CABG.**

| Age at first event | 6–12 mo since event | 1–2 yrs | 2–5 yrs | > 5 yrs |
|---|---|---|---|---|
| < 40 | Decline | +200 | +150 | +125 |
| 40–49 | +200 | +150 | +100 | +75 |
| 50–59 | +150 | +100 | +75 | +50 |
| 60–69 | +100 | +75 | +50 | +25 |
| 70+ | +75 | +50 | +25 | +25 |

- CV-1.1 < 6 months → Postpone (`CLS-7.4`).
- CV-1.2 Modifiers: EF 40–49% +50; EF 30–39% +100; EF < 30% Decline. Ongoing angina +50. Continued
  smoking +50. Abnormal stress test after event +75 (MD). Multi-vessel (≥ 3) +25. LDL < 70 and
  normal stress within 12 mo −25 (exception to CLS-6 "no credits for cardiac").
- CV-1.3 Best class Standard (never Standard Plus or better).
- CV-1.4 Non-obstructive CAD (< 50% stenosis) on CT/cath, no event: +25, best Standard.
- CV-1.5 Coronary calcium score: 0 → no action; 1–99 → 0; 100–399 → +25; ≥ 400 → +50 (without
  CAD dx).

**CV-2 Atrial fibrillation / flutter.**

| Type | Debits |
|---|---|
| Single episode, > 1 yr ago, normal echo | 0, best Preferred |
| Paroxysmal, normal echo, CHA₂DS₂-VASc ≤ 1 | +25 |
| Persistent/permanent, rate controlled, normal echo | +50 |
| With structural heart disease, CHF, or prior stroke | +100 to Decline (MD) |
| Successful ablation > 1 yr, no recurrence | 0, best Standard Plus |

**CV-3 Valvular disease / murmurs.** Innocent murmur, normal echo: 0. Mitral valve prolapse,
trace/mild regurgitation: 0 (best Preferred Plus). Moderate regurgitation/stenosis: +50; severe
not repaired: Decline; valve replacement > 1 yr, normal function: +75; < 1 yr: Postpone.

**CV-4 Heart failure / cardiomyopathy.** EF ≥ 50% recovered (e.g. postpartum, viral) > 2 yrs: +50.
EF 40–49% stable: +100. EF < 40%: Decline. Hypertrophic cardiomyopathy: +75 to Decline (MD).

**CV-5 Other.** PVCs isolated, normal echo: 0. SVT ablated: 0; unablated, infrequent: +25.
WPW ablated: 0; not ablated asymptomatic: +25. Bundle branch block: right 0, left +25 (normal echo
required) . Pacemaker for heart block, otherwise normal: +25. Syncope, vasovagal, single: 0.

**CV-6 Peripheral arterial disease:** +75, best Standard; with smoking +125. Abdominal aortic
aneurysm < 4.0 cm monitored: +50; 4.0–5.0 cm: +100; > 5.0 cm unrepaired: Decline; repaired > 6 mo:
+50.

**CV-9 Positive genetic test for HCM / familial hypercholesterolemia (applicant):** see CV-4 /
LIP-3; best class Standard.

## DM — Diabetes and glucose

**DM-1 Prediabetes** (A1c 5.7–6.4, or fasting glucose 110–125, or metformin with A1c < 6.5 and no
DM dx): 0 debits; best class Preferred (A1c ≤ 6.0) / Standard Plus (6.1–6.4).

**DM-2 Type 2 diabetes.** Order: APS (last 2 yrs incl. A1c history), urine microalbumin if available.

Base debits by age at application and average A1c (last 12 months, `GEN-6`):

| Age | A1c < 7.0 | 7.0–7.9 | 8.0–8.9 | 9.0–9.9 | ≥ 10.0 |
|---|---|---|---|---|---|
| 18–39 | +75 | +100 | +150 | +200 | Decline |
| 40–49 | +50 | +75 | +125 | +175 | Decline |
| 50–59 | +25 | +50 | +100 | +150 | +200 |
| 60–69 | 0 | +25 | +75 | +125 | +175 |
| 70+ | 0 | 0 | +50 | +100 | +150 |

- DM-2.1 Add: insulin use +25; duration > 15 yrs +25; diagnosed before age 30 +25.
- DM-2.2 Complications: microalbuminuria/proteinuria +50 (see `REN`); neuropathy +25;
  retinopathy (non-proliferative) +25, proliferative +75; CAD → rate CV-1 and add DM debits
  **plus** +50 (`CMB-2`).
- DM-2.3 Best class: diet/oral only, A1c < 7.0, age 60+, no complications → Standard Plus;
  otherwise Standard.
- DM-2.4 No A1c in last 12 months (APS stale or not obtained) → assume A1c 8.0–8.9 column
  (`APS-3`, `GRY-5`).
- DM-2.5 GLP-1 agonist (semaglutide, tirzepatide, liraglutide) use: if prescribed for DM rate per
  DM-2; if for weight loss only (no DM dx, A1c < 6.5) rate build on current weight (`BLD-1.7` does
  not apply) and note.

**DM-3 Type 1 diabetes:** use DM-2 table, +50 additional; ages < 30 at application with A1c ≥ 8.5:
Decline. Insulin pump/CGM with A1c < 7.0 and age 40+: −25 from table (MD).

**DM-4 Gestational diabetes,** resolved, normal A1c postpartum: 0; best Preferred.

## CA — Cancer

General: rate from date of **last treatment** (surgery, chemo, radiation; hormonal therapy such as
tamoxifen/AI does not count as active treatment after year 1). Order: oncology APS with pathology.
Cancers are rated with **flat extras** ($ per $1000 face, for N years) and/or debits. Best class:
Standard unless the table says otherwise. Credits never apply.

| Cancer | Stage/grade | Years since treatment → rating |
|---|---|---|
| Basal/squamous cell skin (BCC/SCC) | any, excised | 0 (no impact on preferred) |
| Melanoma in situ | excised | 0; best Preferred after 2 yrs |
| Melanoma | Stage I (≤ 1.0 mm) | 0–2 yrs: FE $10 ×3 yrs; 2–5: FE $5 ×2; > 5: 0, best Standard Plus |
| Melanoma | Stage II | < 2 yrs: Postpone; 2–5: FE $10 ×4 yrs; 5–10: FE $5 ×3; > 10: 0 |
| Melanoma | Stage III–IV | Decline < 10 yrs; then MD |
| Breast DCIS | excised ± radiation | < 1 yr Postpone; 1–3: FE $5 ×2; > 3: 0, best Standard Plus |
| Breast | Stage I | < 1 yr Postpone; 1–3: FE $10 ×4; 3–5: FE $7.50 ×3; 5–10: FE $5 ×2; > 10: 0 |
| Breast | Stage II | < 2 yrs Postpone; 2–5: FE $15 ×5; 5–10: FE $7.50 ×3; > 10: +25 |
| Breast | Stage III | < 5 yrs Decline; 5–10: FE $15 ×5 + 25; > 10: +50 |
| Prostate | Gleason ≤ 6, active surveillance, PSA stable | +25, best Standard |
| Prostate | Gleason ≤ 7, prostatectomy, PSA undetectable | < 1 yr Postpone; 1–3: FE $5 ×3; > 3: 0, best Standard Plus |
| Prostate | Gleason ≥ 8 | < 3 yrs Decline; 3–5: FE $15 ×5; > 5: FE $7.50 ×3 |
| Colon/rectal | Stage I | < 1 yr Postpone; 1–5: FE $10 ×3; > 5: 0 |
| Colon/rectal | Stage II | < 2 yrs Postpone; 2–5: FE $15 ×4; > 5: FE $5 ×2 |
| Colon/rectal | Stage III | < 5 yrs Decline; 5–10: FE $10 ×3; > 10: 0 |
| Thyroid papillary/follicular | Stage I–II, thyroidectomy ± RAI | < 1 yr: FE $5 ×2; > 1 yr: 0, best Preferred (> 5 yrs) |
| Hodgkin lymphoma | Stage I–II | < 2 yrs Postpone; 2–5: FE $10 ×5; 5–10: +50; > 10: +25 (late effects) |
| Non-Hodgkin lymphoma, indolent | watch & wait | +75, best Standard |
| Non-Hodgkin lymphoma, aggressive | remission | < 3 yrs Decline; 3–5: FE $15 ×5; > 5: +50 |
| CLL | Rai 0, stable 2 yrs | +75 (age < 60), +25 (60+) |
| Leukemia, acute | remission | < 5 yrs Decline; > 5: MD |
| Testicular seminoma | Stage I | < 1 yr Postpone; 1–3: FE $5 ×2; > 3: 0 |
| Lung, pancreas, esophagus, brain (glioblastoma) | any | Decline (lung Stage IA > 5 yrs: MD) |
| Recurrence/metastasis of any cancer | | Decline (< 10 yrs since last treatment), then MD |

- CA-1 Unknown stage/grade (no pathology in APS): rate as the next worse stage (`GRY-6`).
- CA-2 Two primary cancers (excluding BCC/SCC): MD; usually Decline < 10 yrs.
- CA-3 Benign tumors (lipoma, fibroadenoma, uterine fibroids, colon polyps benign) → 0; colon
  polyps with high-grade dysplasia → +25 until clear colonoscopy.
- CA-9 BRCA1/2 or Lynch positive, no cancer: no prophylactic surgery +50; prophylactic surgery
  completed → 0, best Standard Plus.

## MH — Mental health

Order: APS (psychiatrist if one in Rx data). Ask: hospitalizations, suicide attempts, work loss.

| Condition | Profile | Debits / best class |
|---|---|---|
| Depression/anxiety, mild | outpatient, ≤ 1 med, no time off work | 0; best Preferred Plus (Preferred if dx < 2 yrs) |
| Depression/anxiety, moderate | ≥ 2 meds, or time off work < 3 mo, or psychiatrist care | +25; best Standard Plus |
| Depression, severe | hospitalization > 12 mo ago, or ECT, or disability | +75 to +100; best Standard |
| Bipolar I/II | stable ≥ 2 yrs, compliant, no hospitalization 5 yrs | +50 (II), +75 (I) |
| Bipolar | hospitalization 1–5 yrs, or non-compliance | +125 to Decline |
| Schizophrenia / schizoaffective | | Decline (stable > 5 yrs on monotherapy: +150, MD) |
| ADHD | stimulant, functioning, no substance issues | 0; best Preferred Plus |
| PTSD | outpatient, working | +25; with substance use add `ALC`/`DRG` |
| Eating disorder | recovered > 3 yrs, normal build | +25; < 3 yrs: Postpone/MD |
| Suicide attempt | < 2 yrs | Decline |
| Suicide attempt | 2–5 yrs, single, stable | +100 |
| Suicide attempt | > 5 yrs, single, stable | +50 |

- MH-1 Psychiatric hospitalization < 12 months → Postpone (`CLS-7.8`).
- MH-2 Depression + alcohol rating → add +25 (`CMB-2`).
- MH-3 Insomnia only (trazodone/zolpidem, no other psych dx) → 0.

## RSP — Respiratory

| Condition | Profile | Debits |
|---|---|---|
| Asthma, mild | rescue inhaler only / seasonal | 0; best Elite eligible if no ER 5 yrs |
| Asthma, moderate | daily controller (ICS), no ER/hospital 2 yrs | +0; best Preferred |
| Asthma, severe | oral steroids ≥ 2 bursts/yr, or ER/hospital 2 yrs, or biologic | +50 to +100 |
| COPD, mild (FEV1 ≥ 70% pred) | non-smoker | +50; smoker +75 |
| COPD, moderate (FEV1 50–69%) | | +100; smoker +150 |
| COPD, severe (FEV1 < 50%) or home O₂ | | Decline |
| Sleep apnea, treated, CPAP compliant | | 0; best Preferred |
| Sleep apnea, untreated or non-compliant | AHI 5–30 | +25; AHI > 30 +75 |
| Sarcoidosis, pulmonary, stable > 2 yrs | | +25; active +75 |
| Pulmonary embolism, single, provoked, > 6 mo | | 0; unprovoked +25; recurrent +75 |

- RSP-1 Sleep apnea + BMI > 40 → `CMB-2` (+25).
- RSP-2 No FEV1 documented for COPD → rate as moderate (`GRY-5`).

## GI — Digestive / liver

| Condition | Profile | Debits |
|---|---|---|
| GERD, gastritis, IBS | | 0 (low-impact) |
| Crohn's disease | mild, no surgery 2 yrs, ≤ 1 med | +25 |
| Crohn's disease | moderate/biologic or surgery within 2 yrs | +75 |
| Ulcerative colitis | mild, colonoscopy < 3 yrs normal dysplasia | 0–+25; > 10 yrs duration w/o surveillance +50 |
| Barrett's esophagus | no dysplasia | +25; low-grade dysplasia +50; high-grade Postpone |
| Fatty liver (NAFLD) | normal LFTs | 0; LFTs per `LAB-2`; fibrosis F2–F3 +75; cirrhosis Decline |
| Hepatitis B, chronic | inactive carrier, normal LFTs, low viral load | +50 |
| Hepatitis C | cured (SVR ≥ 12 wks), no cirrhosis | 0 (> 1 yr), +25 (< 1 yr) |
| Hepatitis C | untreated | +100; with cirrhosis Decline |
| Pancreatitis | single, gallstone, resolved | 0; alcohol-related → `ALC` + 50; chronic +100 |
| Cirrhosis, any cause | | Decline |
| Gastric bypass / sleeve | `BLD-1.7` | rate build |

## REN — Kidney

**REN-1 eGFR** (age-adjusted): ≥ 60: 0. 45–59: +25 (age < 60), 0 (60+). 30–44: +75. 15–29: +150 MD.
< 15 or dialysis: Decline. Transplant > 3 yrs, stable: +150 (MD).

**REN-2 Proteinuria** (urine protein): 31–100 mg/dL +25; 101–300 +50; > 300 +100 and APS.
With diabetes → add per `DM-2.2`, do not double count (use the higher of REN-2 and DM-2.2).

**REN-3** Kidney stones: 0. Polycystic kidney disease: normal eGFR +25; reduced → REN-1 + 25.

## NEU — Neurological

| Condition | Profile | Debits |
|---|---|---|
| Migraine | any treatment | 0 (low-impact); if on topiramate note `RX-2.3` |
| Epilepsy | seizure-free > 2 yrs, 1 med | 0; best Standard Plus |
| Epilepsy | 1–3 seizures/yr | +50 |
| Epilepsy | > 3/yr or uncontrolled | +100 to Decline |
| TIA | single, > 1 yr, normal workup | +50 (age < 50), +25 (50+) |
| Stroke | > 1 yr, no residual deficit | +100 (age < 50), +75 (50–69), +50 (70+) |
| Stroke | residual deficit | add +50; recurrent Decline |
| Multiple sclerosis | relapsing-remitting, minimal disability (EDSS ≤ 2) | +50 |
| Multiple sclerosis | EDSS 2.5–5 | +100 to +150 |
| Multiple sclerosis | progressive or EDSS > 5 | Decline |
| Parkinson's disease | mild, onset age 60+ | +50 to +100; onset < 50 +150 |
| Peripheral neuropathy | idiopathic | 0; diabetic per `DM-2.2` |
| Concussion / TBI | full recovery > 1 yr | 0; with residual deficits +50 to +100 |

## END — Endocrine (non-diabetic)
Hypothyroid on levothyroxine: 0. Hyperthyroid treated (RAI/surgery) > 6 mo: 0. Graves active:
Postpone. Adrenal insufficiency, stable: +50. Pituitary adenoma, benign, stable: 0–+25.

## MSK — Musculoskeletal
Back pain, no surgery, no opioids: 0. Back surgery > 6 mo, recovered: 0 (WP declined, `RID`).
Chronic opioid therapy for pain (> 90 days) → +25 to +50; with benzodiazepine co-prescription +75.
Rheumatoid arthritis: mild 0–+25; on biologics +50. Osteoarthritis: 0. Fibromyalgia: 0 (with
depression rate `MH`).

## HEM — Blood
Iron-deficiency anemia, explained (menstrual): 0. Unexplained anemia → `LAB-2`. Hemochromatosis
treated, normal ferritin: 0. Thrombocytopenia (ITP) stable: +25. Factor V Leiden heterozygous no
clots: 0; with VTE +25. Sickle cell trait: 0; sickle cell disease: Decline.

## IMM — Immune / infectious
- IMM-1 HIV: on ART ≥ 2 yrs, undetectable viral load ≥ 12 mo, CD4 ≥ 500, age 20–60, no AIDS-defining
  illness, no hep B/C co-infection → +100 (Table 3), max face $2M, MD. Otherwise Decline.
  Positive HIV on fluids with app denial → Decline (and `GEN-2.2`).
- IMM-2 Lupus: cutaneous only 0; systemic without organ involvement +50; with renal/CNS +150/Decline.
- IMM-3 Psoriasis: 0; psoriatic arthritis treated with biologics +25.

## GER — Older age (71+) and frailty
- GER-1 Cognitive screen (COG) failure, any dementia/MCI diagnosis, or donepezil/memantine fill →
  Decline.
- GER-2 ADL dependency (any of bathing, dressing, eating, toileting, transferring, continence) →
  Decline.
- GER-3 Use of walker/wheelchair, falls ≥ 2 in 12 months, or hospitalizations ≥ 2 in 24 months →
  +50 each item.
- GER-4 Independent living, active, no GER findings → age 71–80 eligible for Preferred Plus.

## OBS — Pregnancy and women's health
Normal pregnancy: rate at pre-pregnancy weight; no debits; best class unaffected. Complicated
pregnancy: `CLS-7.5`. PCOS on metformin, A1c < 5.7: 0. Abnormal pap/HPV with colposcopy: 0 if
LEEP done or follow-up normal; CIN III pending → Postpone.

## MISC — Unlisted, benign, and catch-all conditions

- MISC-1 **No-rating list** (low-impact; never debits, never affect preferred eligibility unless a
  chapter says otherwise): seasonal allergies, acne, rosacea, eczema, GERD, hemorrhoids, inguinal/
  umbilical hernia (repaired or asymptomatic), cataracts, glaucoma (controlled), myopia, tinnitus,
  benign prostatic hyperplasia (PSA within `LAB-2`), erectile dysfunction, osteopenia, carpal tunnel,
  plantar fasciitis, gout (≤ 2 flares/yr, normal renal function), kidney stones, varicose veins,
  uncomplicated hypothyroidism, contraception, infertility treatment, tonsillectomy/appendectomy/
  cholecystectomy (recovered), vitamin D deficiency, uncomplicated UTI, sinusitis.
- MISC-2 **Unlisted ratable condition:** cite `GRY-0`; obtain APS; MD referral if the UW estimates
  ≥ +50; otherwise rate by analogy to the closest chapter and name the analogy in the worksheet.
- MISC-3 **Other cancers not in the CA table** (e.g. Merkel cell, sarcoma, kidney, bladder,
  ovarian, cervical invasive): < 5 yrs since treatment → Decline; ≥ 5 yrs → MD. Cervical CIN /
  bladder papillary Ta low-grade with clear surveillance > 2 yrs → 0, best Standard Plus.
- MISC-4 **Organ transplant other than kidney** (heart, lung, liver, pancreas, bone marrow):
  Decline (liver transplant > 5 yrs, normal function → MD, minimum +150).
- MISC-5 **Definitions.** *Terminal illness* (`CLS-8.9`): physician-documented life expectancy
  < 24 months, or hospice/palliative referral. *Psychiatric hospitalization* (`CLS-7.8`): any
  inpatient admission or ≥ 23-hour observation stay for a psychiatric diagnosis (ER visit without
  admission does not count). *Misuse* (`CLS-8.4`): any non-prescribed use, or prescribed use outside
  directions documented in APS. *Acceptable explanation for low weight* (`BLD-1.5`): APS documenting
  long-standing stable constitutional thinness (≥ 3 yrs stable) with normal albumin/hemoglobin,
  or endurance athlete with normal labs.

---

## CMB — Combining multiple impairments

- CMB-1 Default: debits **add**.
- CMB-2 **Interaction surcharges** (added once each):
  - Build ≥ +50 with diabetes, HTN, sleep apnea, or CAD: +25 (`BLD-1.6`).
  - Diabetes + CAD: +50.
  - Current tobacco + CAD/PAD/COPD: per chapter (already included there) — do not add again.
  - Depression + alcohol rating: +25.
  - Sleep apnea + BMI > 40: +25.
- CMB-3 Same physiologic system double counting: when two rules rate the same finding (e.g.
  proteinuria under REN-2 and DM-2.2), use the higher, not the sum.
- CMB-4 Class caps: take the **worst** (most restrictive) best-class cap across all chapters.
- CMB-5 Flat extras: add across sources; for different durations list separately (e.g.
  "FE $5 ×3 yrs (melanoma) + FE $2.50 perm (scuba)").
- CMB-6 Total debits including FE equivalents (each $2.50/1000 FE ≈ +25 for reporting only) > +500
  → Decline (MD).

---

## GRY — Grey areas (documented UW discretion)

These are recognized areas where competent underwriters reach different results. Each permits a
range; the UW must state the choice and reason in the worksheet.

| ID | Situation | Permitted range |
|---|---|---|
| GRY-0 | No rule applies | MD consult or UW judgment, documented |
| GRY-1 | Value within 2% of a class threshold (build, BP, lipids) with improving trend in APS | may award the better class, or not |
| GRY-2 | Ambiguous Rx indication with no APS (`RX-2.4`) | least severe plausible indication (default) or order APS and hold |
| GRY-3 | Bariatric surgery < 12 months (`BLD-1.7`) | 50%–100% of pre-op build debits, or Postpone to 12 mo |
| GRY-4 | Unknown tobacco quit date | most recent consistent date (default) or accept applicant's date if APS supports within 6 mo |
| GRY-5 | Stale/missing data for an active condition (`APS-3`, `DM-2.4`, `RSP-2`) | rate as worst documented / default column, or ±1 table if APS shows a clear trend |
| GRY-6 | Unknown cancer stage (`CA-1`) | next worse stage (default) or Postpone pending pathology |
| GRY-7 | Borderline debits (net exactly at a band edge after rounding of averaged values) | either adjacent table |
| GRY-8 | MIB code corroborated only by an "r/o" note in APS | ignore (default) or rate as mild form |
| GRY-9 | Applicant-stated intent to stop hazardous avocation | temporary FE (2 yrs) or permanent |
| GRY-10 | Two mild impairments in unrelated systems each at 0 debits | Standard Plus (default) or Preferred if both minor-impact |
| GRY-11 | Conflicting alcohol quantity between app, APS, and labs | higher stated (default per `ALC-1`) or lab-consistent estimate |
| GRY-12 | Credits partially applicable (e.g. exercise documented but pulse 66–70) | apply or withhold credit |

---

## Appendix — Notes conventions (for reference; see `reference/abbreviations.yaml`)
Worksheets cite rule IDs. Class shorthand used in this office: **E** / **PP** / **P** / **SP** /
**S** (std) / **PT** (pref tob) / **ST** (std tob) / **T1–T16** or letters **A–P** or "+125…+500" for
tables / **PPN** postpone / **DEC** decline / **FE** flat extra written "FE 5/3" = $5 per $1000 for
3 years, "FE 2.5 perm".
