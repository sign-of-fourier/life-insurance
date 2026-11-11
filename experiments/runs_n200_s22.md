# LLM runs (lite, k=3, prompt v1) - 200 cases

| setup | slice | n | parsed | decision | coarse | derived_coarse | ladder | net_abs_err | derived_net_err | item_recall | item_precision | rule_acc | debit_close | arith_ok | class_follows | fe_recall | grey_recall | overrate_partial | worksheet |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1-G1-N4 | all | 200 | 0.96 | 0.17 | 0.36 | 0.19 | 0.79 | 61.68 | 79.69 | 0.51 | 0.37 | 0.78 | 0.37 | 0.43 | 0.27 | 0.07 | 0.21 | 0.00 | 0.35 |
| S1-G1-N4 | grey | 57 | 0.93 | 0.19 | 0.28 | 0.15 | 0.77 | 72.74 | 77.45 | 0.54 | 0.47 | 0.76 | 0.40 | 0.34 | 0.11 | 0.00 | 0.21 | 0.00 | 0.32 |
| S1-G1-N4 | partial | 54 | 0.98 | 0.06 | 0.38 | 0.13 | 0.70 | 64.81 | 96.98 | 0.52 | 0.38 | 0.83 | 0.41 | 0.36 | 0.30 | 0.25 | - | 0.00 | 0.36 |
| S1-G1-N4 | clean | 89 | 0.98 | 0.22 | 0.40 | 0.24 | 0.86 | 53.05 | 70.52 | 0.47 | 0.30 | 0.76 | 0.32 | 0.53 | 0.34 | 0.00 | - | - | 0.37 |
