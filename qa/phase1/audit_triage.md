# Nova Pro audit #1 triage (2026-11-09, $0.022)
Raw output: nova_audit_1.md

| # | Verdict | Action |
|---|---|---|
| 1 | False: cigars vs cigarettes are intentionally different products (TOB-2.1 vs TOB-3.1) | none |
| 2 | False: ≤3 minor = 0 covers a single minor | none |
| 3 | False: CLS-5.6 is explicit (cigarettes only excluded) | none |
| 4 | Covered by GRY-3 | none |
| 5 | False: T16 = +401–425, decline > +425 | none |
| 6 | Minor; "normal" left to UW | none |
| 7 | **Valid** gap: other cancers | added MISC-3 |
| 8 | False: ALC-1 says use the higher | none |
| 9 | **Valid** gap: benign conditions | added MISC-1 no-rating list |
| 10 | Minor | none |
| 11 | **Valid**: non-kidney transplant | added MISC-4 |
| 12 | False: CLS-5.4 says all classes | none |
| 13,17,19,21,23,25 | False: RA/lupus (MSK/IMM), COPD (RSP), DRG-2, REN-1, GI, NEU tables exist | none |
| 14 | **Valid** | defined in MISC-5 |
| 15 | **Valid** small | BLD-1.7 regain clause |
| 16,18 | False / covered (MVR-1 defines DUI) | none |
| 20,22,24 | **Valid** definitions | MISC-5 |
| own | net +1..+4 unassigned in CLS-3.3 | fixed to "+1 to +25" |
| own | no catch-all for unlisted conditions | MISC-2 |
