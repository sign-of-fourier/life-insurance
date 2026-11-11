# LLM runs (lite, k=3, prompt v1) - 200 cases

| setup | slice | n | parsed | decision | coarse | derived_coarse | ladder | net_abs_err | derived_net_err | item_recall | item_precision | rule_acc | debit_close | arith_ok | class_follows | fe_recall | grey_recall | overrate_partial | worksheet |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1-G1-N4 | all | 200 | 0.97 | 0.13 | 0.31 | 0.21 | 0.80 | 69.72 | 77.40 | 0.52 | 0.40 | 0.74 | 0.37 | 0.46 | 0.28 | 0.00 | 0.21 | 0.00 | 0.37 |
| S1-G1-N4 | grey | 57 | 0.96 | 0.11 | 0.24 | 0.13 | 0.84 | 96.64 | 98.18 | 0.54 | 0.51 | 0.67 | 0.36 | 0.42 | 0.16 | 0.00 | 0.21 | 0.00 | 0.34 |
| S1-G1-N4 | partial | 54 | 0.98 | 0.09 | 0.21 | 0.26 | 0.72 | 79.62 | 83.40 | 0.55 | 0.42 | 0.74 | 0.36 | 0.38 | 0.24 | 0.00 | - | 0.00 | 0.34 |
| S1-G1-N4 | clean | 89 | 0.97 | 0.17 | 0.43 | 0.23 | 0.84 | 46.40 | 60.41 | 0.49 | 0.31 | 0.81 | 0.39 | 0.55 | 0.37 | 0.00 | - | - | 0.40 |
