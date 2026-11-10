# Phase 5 manual review (10 cases + C0061)

Picked one case per outcome family (seeded): Elite, Preferred Tobacco, Table, Postpone, Decline, flat extra, grey area,
Standard Plus, Table Tobacco, Preferred Plus. Each golden `.md` read against `reference/guidelines.md`.

| Case | Decision | Verdict | Notes |
|---|---|---|---|
| C0061 | Table 1 | fixed | CLS-6.5 credit was applied although CAD is rated under CV (credits excluded) -> fixed: any CV/CA/ALC/DRG-rated impairment blocks credits even at 0 net chapter debits. Undisclosed oxycodone (back pain) was flagged material MISREP though it changes nothing -> materiality now requires debits / terminal / FE / a cap worse than Preferred Plus. |
| C0829 | Elite | fixed | FIN counter-offer to $225K but Elite requires face >= $250K -> face row now uses the approved amount. |
| C0820 | Preferred Tobacco | ok | NRT current, all Preferred rows met (CLS-5.6). App wording "nicotine_gum_patch" is the form's product code (left as is). |
| C0972 | Table 6 | ok | Bipolar w/o APS -> APS-6 mildest ratable row (+50); WMD declined for psych rating; XCR declined (table). |
| C0550 | Postpone | ok | Breast biopsy pending (CLS-7.1) governs; stale APS for Crohn's documented as GRY-5. |
| C0670 | Decline | fixed wording | Cognitive impairment profile 'any' was described as "default - attributes not documented"; single match-all profiles now read "diagnosis documented". |
| C0773 | Preferred + FE | ok | Student pilot FE $2.50 x 2 yrs; AVO-1.4 allows Preferred. |
| C0381 | Standard | ok | Ratio > 6.5 fails Std Plus row (CLS-5.3); fatty liver default row (APS-6, GRY-5). |
| C0227 | Standard Plus | fixed wording | GRY-10 listed raw keys; findings used catalog labels ("Cocaine / methamphetamine / opioid misuse") instead of the documented diagnosis -> both now use the diagnosis as written. |
| C0910 | Table Tobacco 2 | fixed | Borderline-cotinine step said "non-tobacco ladder" after varenicline had already moved the case to the tobacco ladder (evaluation order) -> varenicline now evaluated first; an app quit date >= 12 months contradicted by a recent varenicline fill is now a MISREP with best Standard Tobacco (TOB-2.1/TOB-5). |
| C0748 | Preferred Plus | ok (design gap) | Design intended over-insurance decline; generator's $18K income floor made the face justified. Golden follows the evidence. |

Generator/data bugs found through the engine and fixed upstream (truth/evidence regenerated deterministically; only
affected APS re-written by Nova):
- diabetes A1c drawn from 0.3-6.9 for the "<7" grid column (impossible values) -> 5.95-6.94.
- paramed BP/build noise moved cases across class bands -> paramed readings nudged so the BP-1 average equals the true BP;
  build re-recorded when noise changed the column.
- "minimized" tobacco answers claimed a *more recent* quit date -> now claim an older one.
- HTN "<=140/90" band generated up to 145 for Std Plus targets.
- Std-row lipids rarely failed Std Plus -> ratio 6.55-7.0 with TC 240-290.
- nm_misrep (GEN-2.3) had no evidence -> realized as an undisclosed DUI (MVR) + undisclosed treated depression (Rx).
- unemployed/retired net worth and in-force coverage ignored FIN intent -> fixed.
- varenicline fills listed newest-first (first > last).
- catalog category labels leaked into documents ("Cancer (see type table)", "PVCs / SVT / WPW / BBB ...") -> specific
  diagnoses (src/dx_labels.py); 402 APS re-written.
- Elite targets: police/fire occupation, visa holders, family-history noise < 65 -> made consistent with Elite.

Guideline additions (rebuilt, check_rules PASS): BP-4 (untreated BP is a matrix criterion; HTN table only > 150/95),
APS-6 (no APS in file -> chapter default row, GRY-5), FIN-1.3 clarified (greater of income multiple and 50% NW),
FIN-2.3 clarified (key-person test applies to the KPE endorsement, not the base policy).
