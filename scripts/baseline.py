"""Compare the usual "RAG on Excel" with the routed approach on the same 20 questions.

Naive RAG: every row is written as a sentence and embedded; the 20 rows closest to the question go to the LLM.
Routed: the app's real pipeline (SQL over all rows, or vector search on descriptions).
Writes eval/baseline_results.md. The naive index (100,000 embeddings, a few cents) is built once in eval/baseline_chroma.
"""

import json
import re
import sys
from pathlib import Path

import chromadb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend import excel
from backend.llm import chat_json, embed

TOP_K = 20

NAIVE_PROMPT = """You answer questions about an insurance claims Excel file.
Below are the rows of the file that are most similar to the question. Answer using only these rows, in 2 to 4 sentences.
Reply with JSON: {"answer": "..."}"""


def row_to_text(row: dict) -> str:
    return (
        f"Claim {row['claim_id']} on {row['claim_date']}: {row['product']} / {row['peril']} in {row['canton']}, "
        f"channel {row['channel']}, customer age {row['customer_age']}, claimed {row['claimed_amount']} EUR, "
        f"paid {row['paid_amount']} EUR, status {row['status']}, settled in {row['settlement_days']} days. "
        f"{row['description']}"
    )


def naive_index():
    client = chromadb.PersistentClient(path=str(ROOT / "eval" / "baseline_chroma"))
    collection = client.get_or_create_collection("rows", metadata={"hnsw:space": "cosine"})
    if collection.count() > 0:
        return collection

    cursor = excel.db.cursor().execute("SELECT * FROM claims")
    columns = [d[0] for d in cursor.description]
    rows = [dict(zip(columns, values)) for values in cursor.fetchall()]
    texts = [row_to_text(row) for row in rows]
    print(f"Embedding {len(texts):,} rows for the naive index (one time)...")
    vectors = embed(texts)
    for i in range(0, len(rows), 5000):
        collection.add(
            ids=[row["claim_id"] for row in rows[i : i + 5000]],
            embeddings=vectors[i : i + 5000],
            documents=texts[i : i + 5000],
        )
    return collection


def naive_answer(question: str, collection) -> tuple[str, list[str]]:
    hits = collection.query(query_embeddings=embed([question]), n_results=TOP_K)
    rows = hits["documents"][0]
    reply = chat_json(NAIVE_PROMPT, f"Question: {question}\n\nRows:\n" + "\n".join(rows))
    return reply["answer"], rows


def answer_is_correct(answer: str, reference_rows: list) -> bool:
    """Every value of the reference result (first 5 rows) must appear in the answer text.
    Numbers may differ by 0.5 % (rounding); text values must appear as written."""
    numbers = [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", answer)]
    for row in reference_rows[:5]:
        for value in row:
            if isinstance(value, (int, float)):
                if not any(abs(n - value) <= max(0.5, 0.005 * abs(value)) for n in numbers):
                    return False
            elif str(value).lower() not in answer.lower():
                return False
    return True


def share_relevant(texts: list[str], keywords: list[str]) -> float:
    if not texts:
        return 0.0
    return sum(any(k in text.lower() for k in keywords) for text in texts) / len(texts)


def routed_descriptions(result: dict) -> list[str]:
    if "description" not in result["columns"]:
        return []
    i = result["columns"].index("description")
    return [str(row[i]) for row in result["rows"]]


if __name__ == "__main__":
    collection = naive_index()
    tests = json.loads((ROOT / "eval" / "excel.json").read_text(encoding="utf-8"))
    naive_score = routed_score = 0
    table = ["| Question | Naive RAG (top 20 rows) | Routed (SQL or vector search) |", "|---|---|---|"]

    for test in tests:
        question = test["question"]
        naive_text, naive_rows = naive_answer(question, collection)
        routed = excel.answer_question(question)

        if test["route"] == "sql":
            reference = excel.db.cursor().execute(test["reference_sql"]).fetchall()
            naive_ok = answer_is_correct(naive_text, reference)
            routed_ok = answer_is_correct(routed["answer"], reference)
            naive_detail = "correct" if naive_ok else "wrong"
            routed_detail = "correct" if routed_ok else "wrong"
        else:
            naive_share = share_relevant(naive_rows, test["keywords"])
            routed_share = share_relevant(routed_descriptions(routed), test["keywords"])
            naive_ok, routed_ok = naive_share >= 0.8, routed_share >= 0.8
            naive_detail, routed_detail = f"{naive_share:.0%} relevant", f"{routed_share:.0%} relevant"

        naive_score += naive_ok
        routed_score += routed_ok
        table.append(f"| {question} | {'✅' if naive_ok else '❌'} {naive_detail} | {'✅' if routed_ok else '❌'} {routed_detail} |")
        print(f"{question[:60]:60}  naive: {naive_detail:14}  routed: {routed_detail}")
        print(f"    naive answer: {naive_text[:150]}")

    report = [
        "# Baseline: naive row RAG vs the routed approach",
        "",
        f"**Naive RAG: {naive_score}/{len(tests)}. Routed: {routed_score}/{len(tests)}.**",
        "",
        "Number questions pass when the answer text contains the values of a hand-written reference SQL query.",
        "Similarity questions pass when at least 80 % of the returned claims are relevant.",
        "",
        *table,
    ]
    (ROOT / "eval" / "baseline_results.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"\nNaive RAG: {naive_score}/{len(tests)}   Routed: {routed_score}/{len(tests)}")
