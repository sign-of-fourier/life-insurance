# LLM runs (lite, k=3, prompt v1) - 50 cases

| setup | slice | n | parsed | decision | coarse | derived_coarse | ladder | net_abs_err | derived_net_err | item_recall | item_precision | rule_acc | debit_close | arith_ok | class_follows | fe_recall | grey_recall | overrate_partial | worksheet |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1-G1@pro | all | 50 | 0.98 | 0.20 | 0.33 | 0.35 | 0.94 | 61.43 | 69.59 | 0.76 | 0.62 | 0.74 | 0.58 | 0.63 | 0.31 | 0.33 | 0.12 | 0.00 | 0.53 |
| S1-G1@pro | grey | 20 | 1.00 | 0.20 | 0.25 | 0.35 | 1.00 | 64.25 | 74.25 | 0.73 | 0.62 | 0.64 | 0.54 | 0.55 | 0.20 | - | 0.12 | 0.00 | 0.48 |
| S1-G1@pro | partial | 15 | 0.93 | 0.29 | 0.29 | 0.29 | 0.79 | 66.07 | 75.00 | 0.79 | 0.65 | 0.89 | 0.61 | 0.64 | 0.36 | 0.00 | - | 0.00 | 0.55 |
| S1-G1@pro | clean | 15 | 1.00 | 0.13 | 0.47 | 0.40 | 1.00 | 53.33 | 58.33 | 0.76 | 0.59 | 0.72 | 0.61 | 0.73 | 0.40 | 0.50 | - | - | 0.59 |
