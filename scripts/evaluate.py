"""Run both evaluation sets through the real API code and write eval/results.md."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend import excel, guide

EVAL_DIR = ROOT / "eval"


def normalise(value):
    return str(round(float(value))) if isinstance(value, (int, float)) else str(value)


def same_result(reference_rows, rows) -> bool:
    """Every reference row must appear (as a set of values) inside some returned row; extra columns are allowed."""
    got = [{normalise(v) for v in row} for row in rows]
    return len(rows) >= len(reference_rows) and all(
        any({normalise(v) for v in ref} <= g for g in got) for ref in reference_rows
    )


def evaluate_excel():
    lines = ["| Question | Route | Expected | Result |", "|---|---|---|---|"]
    passed = 0
    tests = json.loads((EVAL_DIR / "excel.json").read_text(encoding="utf-8"))
    for test in tests:
        try:
            out = excel.ask(excel.Question(question=test["question"]))
        except Exception as error:
            lines.append(f"| {test['question']} | error | {test['route']} | FAIL ({error}) |")
            continue
        if test["route"] == "sql":
            reference = excel.db.cursor().execute(test["reference_sql"]).fetchall()
            ok = out["route"] == "sql" and same_result(reference, out["rows"])
            detail = "values match" if ok else "values differ"
        else:
            descriptions = [row[out["columns"].index("description")].lower() for row in out["rows"]] if out["route"] == "semantic" else []
            relevant = sum(any(k in d for k in test["keywords"]) for d in descriptions)
            precision = relevant / len(descriptions) if descriptions else 0
            ok = out["route"] == "semantic" and precision >= 0.8
            detail = f"{relevant}/{len(descriptions)} relevant"
        passed += ok
        lines.append(f"| {test['question']} | {out['route']} | {test['route']} | {'PASS' if ok else 'FAIL'} ({detail}) |")
    return passed, len(tests), lines


def evaluate_guide():
    lines = ["| Question | Reader on | Expected page | Cited page | Result |", "|---|---|---|---|---|"]
    passed = 0
    tests = json.loads((EVAL_DIR / "guide.json").read_text(encoding="utf-8"))
    for test in tests:
        question = guide.Question(question=test["question"], page_id=test.get("current_page"), profile=test.get("profile", {}))
        out = guide.ask(question)
        cited = out["page_id"] if out["found"] else None
        ok = cited == test["expected_page"]
        # Profile tests: the answer must give the rule for the reader's situation.
        if "must_mention" in test:
            ok = ok and any(text in out["answer"].lower() for text in test["must_mention"])
        passed += ok
        lines.append(
            f"| {test['question']} | {test.get('current_page') or '-'} | {test['expected_page'] or 'not covered'} "
            f"| {cited or 'not found'} | {'PASS' if ok else 'FAIL'} |"
        )
    return passed, len(tests), lines


if __name__ == "__main__":
    excel_passed, excel_total, excel_lines = evaluate_excel()
    guide_passed, guide_total, guide_lines = evaluate_guide()
    report = "\n".join([
        "# Evaluation results",
        "",
        f"## Exercise 2 (Excel): {excel_passed}/{excel_total} passed",
        "",
        "SQL questions pass when the returned values match a hand-written reference query.",
        "Similarity questions pass when at least 80% of returned claims are relevant.",
        "",
        *excel_lines,
        "",
        f"## Exercise 3 (guide): {guide_passed}/{guide_total} passed",
        "",
        "A question passes when the cited page is the expected one, or when nothing is cited for questions the guide does not cover. Profile questions must also give the rule for the reader's situation (EU: 8 days, non-EU: 3 days).",
        "",
        *guide_lines,
    ])
    (EVAL_DIR / "results.md").write_text(report + "\n", encoding="utf-8")
    print(report)
