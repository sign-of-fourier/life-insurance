# Phase 6 notes check

cases 1000; notes missing 0; validation errors 0; hallucinated drug names 0

LLM-voiced lines 18020/19134 (94%); rest kept the code skeleton

stated decision != golden: 87 ({'grey_divergence': 54, 'wrong_final': 33}); grey-area cases 285, diverged 54 (19%)

## Corruptions (all cases)

- omitted_step: 8163 (8.2/case)
- fragment: 2329 (2.3/case)
- unstated_assumption: 218 (0.2/case)
- abbrev_t1: 2748 (2.7/case)
- abbrev_t2: 10788 (10.8/case)
- abbrev_t3: 7832 (7.8/case)
- typo: 869 (0.9/case)
- rider_code: 372 (0.4/case)
- fact_not_in_extraction: 766 (0.8/case)
- arithmetic_error: 42 (0.0/case)
- wrong_final: 33 (0.0/case)
- grey_divergence: 54 (0.1/case)

## Persona fidelity (Spearman rho, parameter vs observed, 12 personas; gate >= 0.6)
t1/t2 = substitutions / (substitutions + phrases left unabbreviated); t3 = tags per line; div direction = mean of +1 (more lenient alternative) / -1 (stricter) vs leniency

- typo: +0.99
- omit: +1.00
- t1: +0.76
- t2: +0.96
- t3: +1.00
- words/line: +0.76
- div direction: +0.84

## Per persona

| persona | cases | omit/step | typo/word | t1 rate | t2 rate | t3/line | words/line | div/grey | div dir |
|---|---|---|---|---|---|---|---|---|---|
| uw_01 R. Okafor | 81 | 0.22 | 0.002 | 0.53 | 0.64 | 0.17 | 9.2 | 0.12 | -0.33 |
| uw_02 D. Lindqvist | 87 | 0.19 | 0.004 | 0.31 | 0.32 | 0.04 | 8.9 | 0.28 | -0.78 |
| uw_03 M. 'Mags' Ferreira | 78 | 0.44 | 0.008 | 0.76 | 0.85 | 0.62 | 7.4 | 0.08 | +0.00 |
| uw_04 J. Thibodeaux | 90 | 0.28 | 0.002 | 0.83 | 0.70 | 0.41 | 8.2 | 0.33 | -1.00 |
| uw_05 P. Raman | 91 | 0.24 | 0.002 | 0.62 | 0.66 | 0.32 | 7.9 | 0.24 | -0.33 |
| uw_06 S. Kowalczyk | 72 | 0.36 | 0.011 | 0.79 | 0.80 | 0.57 | 8.4 | 0.43 | -1.00 |
| uw_07 T. Nakamura-Hale | 99 | 0.30 | 0.006 | 0.77 | 0.53 | 0.25 | 7.9 | 0.04 | +1.00 |
| uw_08 L. Abernathy | 91 | 0.40 | 0.001 | 0.72 | 0.69 | 0.23 | 8.0 | 0.20 | -0.60 |
| uw_09 K. Mbeki | 75 | 0.25 | 0.003 | 0.53 | 0.65 | 0.48 | 8.1 | 0.11 | -1.00 |
| uw_10 A. Gustafsson | 85 | 0.33 | 0.004 | 0.81 | 0.75 | 0.51 | 7.7 | 0.04 | +1.00 |
| uw_11 H. Castellanos | 77 | 0.24 | 0.007 | 0.54 | 0.42 | 0.13 | 8.9 | 0.41 | -1.00 |
| uw_12 B. 'Doc' Whitcombe | 74 | 0.49 | 0.009 | 0.75 | 0.91 | 0.69 | 7.2 | 0.00 | +0.00 |

## Validation errors


## Hallucinated drug names


