# Condition chunks: cosine vs cosine + Cohere Rerank 3.5 (top-30 candidates), k=3, split(s) 11, first 50 test cases

rerank queries billed this run: 360 ($0.720)

| metric | slice | cosine | + rerank |
|---|---|---|---|
| label@k | all | 0.866 | 0.840 |
| label@k | grey | 0.822 | 0.752 |
| label@k | partial | 0.868 | 0.898 |
| label@k | clean | 0.917 | 0.885 |
| debit@k | all | 0.659 | 0.619 |
| debit@k | grey | 0.655 | 0.566 |
| debit@k | partial | 0.571 | 0.589 |
| debit@k | clean | 0.758 | 0.714 |
| vote_coarse | all | 0.500 | 0.400 |
| vote_coarse | grey | 0.412 | 0.353 |
| vote_coarse | partial | 0.438 | 0.312 |
| vote_coarse | clean | 0.647 | 0.529 |
| net_abs_err | all | 39.655 | 41.379 |
| net_abs_err | grey | 55.455 | 55.455 |
| net_abs_err | partial | 50.000 | 57.143 |
| net_abs_err | clean | 17.273 | 17.273 |
