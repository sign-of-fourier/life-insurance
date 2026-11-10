# LLM runs (lite, k=3, prompt v1) - 200 cases

| setup | slice | n | parsed | decision | coarse | derived_coarse | ladder | net_abs_err | derived_net_err | item_recall | item_precision | rule_acc | debit_close | arith_ok | class_follows | fe_recall | grey_recall | overrate_partial | worksheet |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S4R-G2-N3 | all | 200 | 0.99 | 0.16 | 0.32 | 0.15 | 0.81 | 79.72 | 103.17 | 0.54 | 0.31 | 0.60 | 0.40 | 0.30 | 0.11 | 0.11 | 0.00 | 0.02 | 0.28 |
| S4R-G2-N3 | grey | 57 | 1.00 | 0.17 | 0.30 | 0.16 | 0.81 | 89.47 | 122.46 | 0.66 | 0.41 | 0.65 | 0.44 | 0.23 | 0.04 | 0.00 | 0.00 | 0.00 | 0.29 |
| S4R-G2-N3 | partial | 54 | 0.98 | 0.15 | 0.24 | 0.15 | 0.70 | 80.38 | 89.72 | 0.59 | 0.38 | 0.62 | 0.42 | 0.41 | 0.19 | 0.33 | - | 0.03 | 0.36 |
| S4R-G2-N3 | clean | 89 | 1.00 | 0.15 | 0.37 | 0.15 | 0.88 | 73.09 | 98.82 | 0.44 | 0.20 | 0.55 | 0.35 | 0.28 | 0.10 | 0.00 | - | - | 0.23 |
