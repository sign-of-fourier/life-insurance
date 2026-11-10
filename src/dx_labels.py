"""Diagnosis labels as a physician would write them (shared by the truth generator and the engine).

The impairment catalog's labels are category names ("Cancer (see type table)"); documents must show a specific diagnosis.
"""
from __future__ import annotations

CANCER_LABEL = {"bcc_scc": "Basal cell carcinoma of skin", "melanoma_in_situ": "Melanoma in situ", "melanoma_1": "Malignant melanoma, stage I",
                "melanoma_2": "Malignant melanoma, stage II", "melanoma_3_4": "Malignant melanoma, stage III", "breast_dcis": "Ductal carcinoma in situ (DCIS), breast",
                "breast_1": "Breast cancer, stage I", "breast_2": "Breast cancer, stage II", "breast_3": "Breast cancer, stage III",
                "prostate_surveillance": "Prostate adenocarcinoma, Gleason 3+3, active surveillance",
                "prostate_le7_surgery": "Prostate adenocarcinoma, s/p radical prostatectomy", "prostate_ge8": "Prostate adenocarcinoma, high grade",
                "colon_1": "Colon adenocarcinoma, stage I", "colon_2": "Colon adenocarcinoma, stage II", "colon_3": "Colon adenocarcinoma, stage III",
                "thyroid": "Papillary thyroid carcinoma", "hodgkin_1_2": "Hodgkin lymphoma, early stage", "nhl_indolent": "Follicular lymphoma (indolent NHL)",
                "nhl_aggressive": "Diffuse large B-cell lymphoma", "cll_rai0": "Chronic lymphocytic leukemia, Rai stage 0", "acute_leukemia": "Acute myeloid leukemia, in remission",
                "testicular_seminoma_1": "Testicular seminoma, stage I", "lung_pancreas_esophagus_brain": "Non-small cell lung cancer",
                "other_unlisted": "Renal cell carcinoma"}
NO_STAGE = {"melanoma_1": "Malignant melanoma", "melanoma_2": "Malignant melanoma", "melanoma_3_4": "Malignant melanoma", "breast_1": "Breast cancer",
            "breast_2": "Breast cancer", "breast_3": "Breast cancer", "colon_1": "Colon adenocarcinoma", "colon_2": "Colon adenocarcinoma",
            "colon_3": "Colon adenocarcinoma", "hodgkin_1_2": "Hodgkin lymphoma"}
KIND_LABEL = {("arrhythmia_other", "svt"): "Supraventricular tachycardia (SVT)", ("arrhythmia_other", "wpw"): "Wolff-Parkinson-White syndrome",
              ("arrhythmia_other", "lbbb"): "Left bundle branch block", ("arrhythmia_other", "rbbb"): "Right bundle branch block",
              ("arrhythmia_other", "pvc"): "Premature ventricular contractions", ("arrhythmia_other", "pacemaker"): "Sick sinus syndrome, s/p pacemaker",
              ("arrhythmia_other", "vasovagal"): "Vasovagal syncope", ("adrenal_pituitary", "adrenal"): "Adrenal insufficiency",
              ("adrenal_pituitary", "pituitary"): "Pituitary adenoma", ("pad_aaa", "pad"): "Peripheral arterial disease",
              ("pad_aaa", "aaa"): "Abdominal aortic aneurysm", ("anemia", "factor_v_leiden"): "Factor V Leiden mutation",
              ("anemia", "sickle_cell_disease"): "Sickle cell disease", ("anemia", "itp"): "Immune thrombocytopenia (ITP)",
              ("anemia", "other"): "Iron deficiency anemia", ("valve", "mvp"): "Mitral valve prolapse", ("valve", "innocent_murmur"): "Innocent heart murmur",
              ("valve", "other"): "Aortic valve disease", ("thyroid", "graves_active"): "Graves' disease", ("thyroid", "other"): "Thyroid nodule",
              ("lupus", "systemic"): "Systemic lupus erythematosus", ("lupus", "other"): "Cutaneous lupus"}


def specific_label(key, d, default):
    """The diagnosis a physician would write (catalog labels are category names, e.g. 'Cancer (see type table)')."""
    if key == "cancer":
        t = d.get("type", "")
        return NO_STAGE.get(t, CANCER_LABEL.get(t, "Malignant neoplasm")) if d.get("stage_documented") is False else CANCER_LABEL.get(t, "Malignant neoplasm")
    if key == "cad":
        return {"MI": "Coronary artery disease, s/p myocardial infarction", "stent": "Coronary artery disease, s/p PCI/stent",
                "CABG": "Coronary artery disease, s/p CABG"}.get(d.get("event"), "Coronary artery disease")
    if key == "substance_use_hard":
        sub = d.get("substance", "opioids")
        return f"{'Opioid' if 'opioid' in sub or sub == 'heroin' else sub.capitalize()} use disorder" + (", on maintenance therapy" if d.get("maintenance") else "")
    if key == "benign_tumor":
        return "Colon polyp (adenoma)" + (", high-grade dysplasia" if d.get("high_grade_dysplasia") else "")
    if key == "cad_nonobstructive":
        return "Non-obstructive coronary artery disease" if d.get("stenosis_pct") else "Coronary artery calcification"
    if key == "organ_transplant_other":
        return f"{(d.get('organ') if d.get('organ') not in (None, 'other') else 'Lung').capitalize()} transplant recipient"
    k = d.get("kind")
    if (key, k) in KIND_LABEL:
        return KIND_LABEL[(key, k)]
    if key in ("adrenal_pituitary", "pad_aaa", "anemia", "arrhythmia_other", "valve"):
        return {"adrenal_pituitary": "Adrenal insufficiency", "pad_aaa": "Peripheral arterial disease", "anemia": "Anemia",
                "arrhythmia_other": "Cardiac arrhythmia", "valve": "Heart murmur"}[key]
    return default



def kind_from_label(key: str, label: str | None):
    """Reverse lookup used by the engine when only the written diagnosis is in file (no APS detail)."""
    if not label:
        return None
    lo = label.lower()
    for (k, kind), lbl in KIND_LABEL.items():
        if k == key and lbl.lower() in lo:
            return kind
    return None
