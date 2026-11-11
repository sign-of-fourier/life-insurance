# LLM runs (lite, k=3, prompt v1) - 200 cases

| setup | slice | n | parsed | decision | coarse | derived_coarse | ladder | net_abs_err | derived_net_err | item_recall | item_precision | rule_acc | debit_close | arith_ok | class_follows | fe_recall | grey_recall | overrate_partial | worksheet |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1-G1-N4 | all | 200 | 0.99 | 0.20 | 0.36 | 0.21 | 0.78 | 71.18 | 87.19 | 0.59 | 0.39 | 0.72 | 0.46 | 0.46 | 0.31 | 0.00 | 0.30 | 0.00 | 0.40 |
| S1-G1-N4 | grey | 57 | 1.00 | 0.21 | 0.25 | 0.23 | 0.68 | 94.12 | 102.98 | 0.66 | 0.50 | 0.67 | 0.49 | 0.44 | 0.21 | 0.00 | 0.30 | 0.00 | 0.40 |
| S1-G1-N4 | partial | 54 | 0.98 | 0.17 | 0.40 | 0.21 | 0.70 | 72.08 | 86.70 | 0.58 | 0.40 | 0.69 | 0.43 | 0.43 | 0.40 | 0.00 | - | 0.00 | 0.41 |
| S1-G1-N4 | clean | 89 | 1.00 | 0.20 | 0.40 | 0.20 | 0.89 | 55.95 | 77.36 | 0.55 | 0.32 | 0.80 | 0.45 | 0.48 | 0.32 | 0.00 | - | - | 0.39 |
