# LLM runs (lite, k=3, prompt v1) - 30 cases

| setup | slice | n | parsed | decision | coarse | derived_coarse | ladder | net_abs_err | derived_net_err | item_recall | item_precision | rule_acc | debit_close | arith_ok | class_follows | fe_recall | grey_recall | overrate_partial | worksheet |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B1-G1 | all | 30 | 0.97 | 0.24 | 0.41 | 0.24 | 0.69 | 82.07 | 114.83 | 0.44 | 0.26 | 0.66 | 0.33 | 0.28 | 0.24 | 0.00 | 0.00 | 0.00 | 0.28 |
| B1-G1 | grey | 12 | 1.00 | 0.25 | 0.42 | 0.25 | 0.75 | 51.67 | 74.17 | 0.56 | 0.41 | 0.68 | 0.42 | 0.25 | 0.25 | 0.00 | 0.00 | 0.00 | 0.33 |
| B1-G1 | partial | 9 | 0.89 | 0.25 | 0.25 | 0.38 | 0.38 | 143.12 | 151.88 | 0.50 | 0.27 | 0.67 | 0.37 | 0.38 | 0.25 | - | - | 0.00 | 0.32 |
| B1-G1 | clean | 9 | 1.00 | 0.22 | 0.56 | 0.11 | 0.89 | 68.33 | 136.11 | 0.22 | 0.06 | 0.50 | 0.17 | 0.22 | 0.22 | - | - | - | 0.17 |
