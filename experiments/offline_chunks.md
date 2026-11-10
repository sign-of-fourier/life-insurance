# Offline condition-chunk retrieval (U2, Cohere cosine on extracted items, k=3, 3 splits)

chunks 8886 (aligned 8111, rated 2332); align threshold 0.35

| metric | all | grey | partial | clean |
|---|---|---|---|---|
| detect | 0.930±0.006 | 0.937±0.016 | 0.958±0.011 | 0.904±0.010 |
| label@k | 0.836±0.012 | 0.812±0.022 | 0.824±0.008 | 0.863±0.019 |
| debit@k | 0.675±0.006 | 0.605±0.017 | 0.681±0.032 | 0.726±0.021 |
| vote_coarse | 0.483±0.009 | 0.427±0.041 | 0.426±0.040 | 0.554±0.026 |
| wholecase_vote_coarse | 0.422±0.049 | 0.398±0.093 | 0.401±0.057 | 0.449±0.028 |
| net_abs_err | 28.355±0.977 | 39.696±6.352 | 34.384±2.752 | 17.469±3.766 |
