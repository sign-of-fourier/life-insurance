# MIB codebook (synthetic) — underwriter reference

Generated from `reference/mib_codebook.yaml` by `src/gen_mib.py`. Read with guidelines §MIB.

Code format: **S C C D R Q** — `SCC` condition (S = body system), `D` degree, `R` source, `Q` qualifier.
Example: `803416` → Breast cancer · severe · attending physician statement · 1–5 years ago.

## Reading rules
- Never rate on a code alone (MIB-1).
- Code report date > 7 years ago -> informational (MIB-3).
- Undisclosed condition within 7 years -> APS (MIB-4); not corroborated -> ignore.
- Retired/old-format codes (x90 and 180) are informational only.
- Foreign nationals / recent immigrants: absence of codes is not favorable (MIB-5).
- Degree 7 (under investigation) + no follow-up evidence -> GRY-8 territory.

## Degree (4th digit)

| Digit | Meaning |
|---|---|
| 0 | unspecified |
| 1 | history of / resolved |
| 2 | mild / slight |
| 3 | moderate |
| 4 | severe / marked |
| 5 | abnormal test value, borderline |
| 6 | abnormal test value, significant |
| 7 | under investigation / unconfirmed |
| 8 | treated, reported controlled |
| 9 | degree not reported |

## Source (5th digit)

| Digit | Meaning |
|---|---|
| 0 | applicant admission (prior application) |
| 1 | attending physician statement / medical records |
| 2 | lab or paramedical exam |
| 3 | prescription database |
| 4 | motor vehicle / public record |
| 5 | electronic health record (eMed) feed |
| 6 | claim (health/disability/life) |
| 7 | other insurer, source not stated |
| 8 | interview / inspection report |
| 9 | foreign source |

## Qualifier (6th digit)

| Digit | Meaning |
|---|---|
| 0 | none |
| 1 | surgical treatment |
| 2 | medication |
| 3 | hospitalized |
| 4 | emergency visit |
| 5 | within past 12 months |
| 6 | 1–5 years ago |
| 7 | more than 5 years ago |
| 8 | recurrence / relapse |
| 9 | prior insurer rated, postponed or declined |

## Condition codes (SCC)

### 0xx — General & administrative (build, insurance activity, hazardous activity, driving)

| SCC | Condition | Note |
|---|---|---|
| 001 | Build - overweight |  |
| 002 | Build - underweight |  |
| 003 | Weight loss |  |
| 010 | Prior application - life | insurance activity |
| 011 | Prior application - disability |  |
| 012 | Prior application - LTC |  |
| 015 | Applied multiple carriers within 90 days | anti-selection alert |
| 020 | Hazardous avocation - unspecified |  |
| 021 | Scuba diving |  |
| 022 | Skydiving / parachuting |  |
| 023 | Motor racing |  |
| 024 | Mountaineering |  |
| 025 | Aviation - private pilot |  |
| 026 | Aviation - student pilot / unusual flying |  |
| 030 | Driving record - adverse |  |
| 031 | Driving under influence |  |
| 032 | License suspended / revoked |  |
| 040 | Foreign residence / travel |  |
| 045 | Criminal record / incarceration |  |
| 050 | Tobacco use reported |  |
| 051 | Nicotine test positive |  |
| 055 | Tobacco use denied - inconsistent | discrepancy alert |
| 090 | Old-format code (pre-2012) - general | informational only (MIB-3) **(retired)** |

### 1xx — Cardiovascular

| SCC | Condition | Note |
|---|---|---|
| 100 | Blood pressure elevated / hypertension |  |
| 101 | Hypertension with end-organ change |  |
| 105 | Blood pressure low |  |
| 110 | Coronary artery disease |  |
| 111 | Myocardial infarction |  |
| 112 | Coronary stent / angioplasty |  |
| 113 | Coronary bypass surgery |  |
| 114 | Angina / chest pain | chest pain often non-cardiac; corroborate |
| 115 | Coronary calcium / non-obstructive disease |  |
| 120 | Atrial fibrillation / flutter |  |
| 121 | Supraventricular tachycardia |  |
| 122 | Ventricular ectopy / PVCs |  |
| 123 | Conduction disorder / bundle branch block |  |
| 124 | Pacemaker / implanted device |  |
| 125 | Syncope |  |
| 126 | Pre-excitation (WPW) |  |
| 130 | Heart murmur |  |
| 131 | Valve disorder |  |
| 132 | Valve replacement / repair |  |
| 140 | Cardiomyopathy |  |
| 141 | Heart failure |  |
| 150 | Peripheral arterial disease |  |
| 151 | Aortic aneurysm |  |
| 160 | Deep vein thrombosis |  |
| 170 | Abnormal EKG | corroborate; may be normal variant |
| 171 | Abnormal stress test |  |
| 175 | Abnormal echocardiogram | corroborate |
| 180 | Lipid disorder (legacy cardiovascular placement) | pre-2012; now 640 **(retired)** |
| 190 | Old-format cardiovascular code | **(retired)** |

### 2xx — Digestive & liver

| SCC | Condition | Note |
|---|---|---|
| 200 | Gastroesophageal reflux |  |
| 201 | Barrett's esophagus |  |
| 205 | Peptic ulcer |  |
| 210 | Crohn's disease |  |
| 211 | Ulcerative colitis |  |
| 212 | Irritable bowel syndrome |  |
| 215 | Colon polyps |  |
| 220 | Liver function tests abnormal |  |
| 221 | Fatty liver |  |
| 222 | Hepatitis B |  |
| 223 | Hepatitis C |  |
| 224 | Cirrhosis |  |
| 225 | Hepatitis | order serology/APS |
| 230 | Pancreatitis |  |
| 235 | Gallbladder disease |  |
| 240 | Bariatric surgery |  |
| 245 | GI bleeding | corroborate; cause drives rating |

### 3xx — Nervous system

| SCC | Condition | Note |
|---|---|---|
| 300 | Headache / migraine |  |
| 305 | Seizure disorder / epilepsy |  |
| 306 | Single seizure |  |
| 310 | Transient ischemic attack |  |
| 311 | Stroke |  |
| 315 | Multiple sclerosis |  |
| 316 | Demyelinating event / optic neuritis | may precede MS dx |
| 320 | Parkinson's disease |  |
| 321 | Tremor |  |
| 325 | Peripheral neuropathy |  |
| 330 | Head injury / concussion |  |
| 335 | Dementia / memory impairment |  |
| 340 | Sleep disorder |  |
| 345 | Vertigo / dizziness |  |
| 390 | Old-format neuro code | **(retired)** |

### 4xx — Psychiatric & substance use

| SCC | Condition | Note |
|---|---|---|
| 400 | Depression |  |
| 401 | Anxiety disorder |  |
| 402 | Adjustment disorder / situational |  |
| 405 | Bipolar disorder |  |
| 406 | Schizophrenia / psychotic disorder |  |
| 410 | Attention deficit disorder |  |
| 411 | Post-traumatic stress disorder |  |
| 412 | Eating disorder |  |
| 415 | Suicide attempt / self-harm |  |
| 420 | Alcohol use - excessive |  |
| 421 | Alcohol use disorder - treated |  |
| 425 | Marijuana use |  |
| 426 | Drug use - cocaine/stimulant |  |
| 427 | Drug use - opioid |  |
| 428 | Drug use - unspecified | corroborate |
| 430 | Insomnia |  |
| 490 | Old-format psychiatric code | **(retired)** |

### 5xx — Respiratory

| SCC | Condition | Note |
|---|---|---|
| 500 | Asthma |  |
| 505 | Chronic obstructive pulmonary disease |  |
| 506 | Emphysema |  |
| 510 | Sleep apnea |  |
| 515 | Sarcoidosis |  |
| 520 | Pulmonary embolism |  |
| 525 | Pulmonary nodule | workup status drives decision (CLS-7.1) |
| 530 | Pneumonia |  |
| 535 | Abnormal pulmonary function test |  |
| 540 | Chronic sinusitis / allergic rhinitis |  |

### 6xx — Endocrine & metabolic

| SCC | Condition | Note |
|---|---|---|
| 600 | Diabetes mellitus type 2 |  |
| 601 | Diabetes mellitus type 1 |  |
| 602 | Diabetes | type from APS/Rx |
| 603 | Gestational diabetes |  |
| 605 | Glucose elevated / prediabetes |  |
| 606 | HbA1c elevated | value decides DM-1 vs DM-2 |
| 610 | Hypothyroidism |  |
| 611 | Hyperthyroidism / Graves |  |
| 612 | Thyroid nodule | check biopsy |
| 620 | Adrenal disorder |  |
| 621 | Pituitary disorder |  |
| 630 | Gout / hyperuricemia |  |
| 640 | Cholesterol / lipids elevated |  |
| 641 | Triglycerides elevated |  |
| 650 | Vitamin deficiency |  |
| 690 | Old-format endocrine code | **(retired)** |

### 7xx — Genitourinary, renal & reproductive

| SCC | Condition | Note |
|---|---|---|
| 700 | Protein in urine |  |
| 701 | Blood in urine | LAB-2 urine RBC |
| 702 | Glucose in urine | check A1c |
| 705 | Chronic kidney disease |  |
| 706 | Kidney function abnormal (creatinine/eGFR) |  |
| 707 | Dialysis |  |
| 708 | Kidney transplant |  |
| 710 | Kidney stones |  |
| 711 | Polycystic kidney disease |  |
| 715 | Prostate enlargement |  |
| 716 | PSA elevated |  |
| 720 | Pregnancy |  |
| 721 | Pregnancy complication |  |
| 725 | Abnormal Pap / cervical dysplasia |  |
| 730 | Infertility / reproductive treatment |  |
| 735 | Urinary tract infection |  |

### 8xx — Neoplasm & blood

| SCC | Condition | Note |
|---|---|---|
| 800 | Cancer - type unspecified | order oncology APS |
| 801 | Skin cancer - basal / squamous |  |
| 802 | Melanoma |  |
| 803 | Breast cancer |  |
| 804 | Breast - carcinoma in situ |  |
| 805 | Prostate cancer |  |
| 806 | Colon / rectal cancer |  |
| 807 | Thyroid cancer |  |
| 808 | Lymphoma |  |
| 809 | Leukemia |  |
| 810 | Lung cancer |  |
| 811 | Testicular cancer |  |
| 812 | Other solid tumor |  |
| 815 | Benign tumor |  |
| 816 | Breast mass / biopsy | benign vs pending (CLS-7.1) |
| 820 | Genetic predisposition (BRCA/Lynch) |  |
| 830 | Anemia |  |
| 831 | Platelet disorder |  |
| 832 | Clotting disorder |  |
| 833 | Hemochromatosis |  |
| 834 | Sickle cell |  |
| 840 | HIV infection |  |
| 841 | HIV test positive |  |
| 890 | Old-format neoplasm code | **(retired)** |

### 9xx — Musculoskeletal, immune, skin & other

| SCC | Condition | Note |
|---|---|---|
| 900 | Back / spine disorder |  |
| 901 | Back surgery |  |
| 905 | Arthritis - osteo |  |
| 906 | Rheumatoid arthritis |  |
| 907 | Fibromyalgia |  |
| 910 | Lupus |  |
| 911 | Psoriasis / psoriatic arthritis |  |
| 915 | Chronic pain / opioid therapy |  |
| 920 | Organ transplant (non-kidney) |  |
| 925 | Fracture / injury |  |
| 930 | Eye disorder |  |
| 935 | Hearing disorder |  |
| 940 | Skin disorder |  |
| 950 | Activities of daily living impairment |  |
| 951 | Mobility aid / falls |  |
| 960 | Disability claim | check cause |
| 990 | Old-format miscellaneous code | **(retired)** |
