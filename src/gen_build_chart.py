"""Single source of truth for the build chart: BMI cutoffs -> rules/build.yaml + markdown fragment."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
# (column label, max BMI, debits, class_cap)
UPPER = [("Elite", 27.0, 0, "Elite"), ("Pref Plus", 28.5, 0, "Preferred Plus"), ("Preferred", 30.0, 0, "Preferred"),
         ("Std Plus", 31.5, 0, "Standard Plus"), ("Standard", 33.0, 0, "Standard"),
         ("+25", 35.0, 25, None), ("+50", 37.0, 50, None), ("+75", 39.0, 75, None), ("+100", 41.0, 100, None),
         ("+150", 43.0, 150, None), ("+200", 45.0, 200, None), ("+250", 47.0, 250, None)]
# above +250 column -> Decline (BLD-1.4)
LOWER = [("min Std", 18.0, 0), ("min +25", 17.0, 25), ("min +50", 16.0, 50)]  # below min +50 -> Postpone/IC (BLD-1.5)

w = lambda bmi, h: int(bmi * h * h / 703)  # max weight (lb) at/under BMI, floored

def main():
    rows = []
    for h in range(58, 81):
        rows.append({"height_in": h, "max": {lab: w(b, h) for lab, b, *_ in UPPER},
                     "min": {lab: w(b, h) + 1 for lab, b, _ in LOWER}})
    y = {"rule": "BLD-1", "units": "lb, height in inches, shoes off",
         "upper_bands": [{"label": l, "max_bmi": b, "debits": d, "best_class": c} for l, b, d, c in UPPER],
         "lower_bands": [{"label": l, "min_bmi": b, "debits": d} for l, b, d in LOWER],
         "over_last_band": "Decline (BLD-1.4)", "under_last_band": "Postpone / individual consideration (BLD-1.5)",
         "chart": rows}
    (ROOT / "rules").mkdir(exist_ok=True)
    (ROOT / "rules/build.yaml").write_text(yaml.safe_dump(y, sort_keys=False))
    hdr = ["Ht"] + [l for l, *_ in LOWER][::-1] + [l for l, *_ in UPPER]
    md = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
    for r in rows:
        ft = f"{r['height_in']//12}'{r['height_in']%12}\""
        md.append("| " + " | ".join([ft] + [str(r["min"][l]) for l, *_ in LOWER][::-1] + [str(r["max"][l]) for l, *_ in UPPER]) + " |")
    (ROOT / "reference/fragments/build_chart.md").write_text("\n".join(md) + "\n")
    print(f"build chart: {len(rows)} heights")

if __name__ == "__main__":
    main()
