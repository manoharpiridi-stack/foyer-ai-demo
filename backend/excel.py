import json
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .llm import chat_json, embed
from .monitoring import log_question
from .stores import CLAIMS_XLSX, DATA_QUALITY_JSON, chroma_collection, duckdb_readonly

router = APIRouter(prefix="/api/excel")

db = duckdb_readonly()

MAX_ROWS = 50
SIMILAR_K = 20
CATEGORICAL = ["product", "peril", "canton", "channel", "status"]
FILTER_KEYS = ["product", "peril", "canton", "status", "year"]

EXAMPLES = [
    "How many claims were rejected in 2024, by product?",
    "Which canton has the highest average paid amount for home water damage?",
    "Show the 10 largest open motor claims.",
    "How many claims mention a washing machine?",
    "Find claims similar to: a bike stolen from a shared basement that wasn't locked",
    "What kind of situations lead to rejected liability claims?",
]


def describe_table() -> str:
    lines = []
    for name, column_type, *_ in db.execute("DESCRIBE claims").fetchall():
        line = f"- {name} {column_type}"
        if name in CATEGORICAL:
            values = [r[0] for r in db.execute(f"SELECT DISTINCT {name} FROM claims ORDER BY 1").fetchall()]
            line += f", values: {values}"
        lines.append(line)
    pairs = db.execute("SELECT product, list(DISTINCT peril ORDER BY peril) FROM claims GROUP BY product ORDER BY 1").fetchall()
    lines.append("Perils per product: " + "; ".join(f"{product}: {perils}" for product, perils in pairs))
    return "\n".join(lines)


SCHEMA = describe_table()
COLUMNS = [{"name": n, "type": t} for n, t, *_ in db.execute("DESCRIBE claims").fetchall()]
DATA_QUALITY = json.loads(DATA_QUALITY_JSON.read_text(encoding="utf-8"))
ROW_COUNT = db.execute("SELECT count(*) FROM claims").fetchone()[0]

PLANNER_PROMPT = f"""You help analysts query an insurance claims table (DuckDB) with {ROW_COUNT:,} rows, claims from 2022 to 2025 in Luxembourg.

Table `claims`:
{SCHEMA}

Notes: amounts are in EUR. paid_amount is 0 for rejected claims and NULL for open ones. settlement_days is NULL for open claims.
description is a short free-text note in English written by the claims handler.

Choose ONE route:
- "sql": counts, totals, averages, rankings, filters, specific claims, searches for an exact word the user gives
  ("mention X": use ILIKE on description), and questions about which situations or reasons are most common
  (GROUP BY peril or description over ALL matching rows).
  Write a single DuckDB SELECT query (DuckDB dialect: median(x), quantile_cont(x, 0.9), year(d), month(d)).
  When listing claims, select only useful columns and LIMIT {MAX_ROWS}.
- "semantic": the user describes a situation in their own words and wants to see matching claims
  ("claims like...", "examples of claims where...", "find claims where <situation>"). Do not guess keywords for these.
  Give a search text. Add a filter only when the user names its value explicitly ("rejected", "in 2024", "motor claims");
  never infer one from the situation (keys: {FILTER_KEYS}; year is an integer).

Reply with JSON, either {{"route": "sql", "sql": "..."}}
or {{"route": "semantic", "search": "...", "filters": {{"status": "Rejected"}}}}."""

ANSWER_PROMPT = """You are a claims data analyst. Answer the user's question using ONLY the result provided.
Write 2 to 4 plain sentences for a business reader, quoting the key numbers.
If the result is empty or does not answer the question, say so clearly. Never invent numbers.
For a similarity search you only see the closest matches: describe what they have in common and how they were handled,
and never state how many such claims exist in total.
Reply with JSON: {"answer": "..."}"""


class Question(BaseModel):
    question: str


def run_sql(sql: str):
    if not sql.lstrip().lower().startswith(("select", "with")):
        raise ValueError("Only SELECT queries are allowed.")
    cursor = db.cursor()
    cursor.execute(sql)
    columns = [d[0] for d in cursor.description]
    return columns, cursor.fetchmany(MAX_ROWS)


def run_similarity(search: str, filters: dict):
    if filters.get("year"):
        filters["year"] = int(filters["year"])
    conditions = [{k: v} for k, v in filters.items() if k in FILTER_KEYS and v not in (None, "")]
    where = conditions[0] if len(conditions) == 1 else {"$and": conditions} if conditions else None
    hits = chroma_collection("claims").query(query_embeddings=embed([search]), n_results=SIMILAR_K, where=where)
    ids, distances = hits["ids"][0], hits["distances"][0]
    if not ids:
        return ["claim_id"], []
    cursor = db.cursor()
    cursor.execute(
        "SELECT claim_id, claim_date, product, peril, canton, claimed_amount, status, description "
        "FROM claims WHERE claim_id IN (SELECT unnest(?))",
        [ids],
    )
    columns = [d[0] for d in cursor.description] + ["similarity"]
    by_id = {row[0]: row for row in cursor.fetchall()}
    rows = [(*by_id[i], round(1 - d, 3)) for i, d in zip(ids, distances)]
    return columns, rows


def timed(steps: list, name: str, started: float, detail: str = ""):
    steps.append({"name": name, "ms": round((time.perf_counter() - started) * 1000), "detail": detail})


@router.get("/info")
def info():
    return {"rows": ROW_COUNT, "columns": COLUMNS, "examples": EXAMPLES, "quality": DATA_QUALITY}


@router.get("/download")
def download():
    return FileResponse(CLAIMS_XLSX, filename="claims.xlsx")


@router.post("/ask")
def ask(body: Question):
    with log_question("excel", body.question) as record:
        result = answer_question(body.question)
        record.update(
            route=result["route"],
            sql=result["sql"],
            search=result["search"],
            filters=result["filters"],
            rows=len(result["rows"]),
            steps_ms={s["name"]: s["ms"] for s in result["steps"]},
        )
    return result


def answer_question(question: str) -> dict:
    steps = []

    started = time.perf_counter()
    plan = chat_json(PLANNER_PROMPT, question)
    route = plan.get("route")
    timed(steps, "Plan", started, f"LLM chose the {route} route")

    started = time.perf_counter()
    try:
        if route == "sql":
            try:
                columns, rows = run_sql(plan["sql"])
            except Exception as error:
                # One retry: show the model its error and let it fix the query.
                timed(steps, "SQL failed", started, str(error))
                started = time.perf_counter()
                plan = chat_json(PLANNER_PROMPT, f"{question}\n\nYour previous SQL:\n{plan['sql']}\nfailed with: {error}\nFix it.")
                columns, rows = run_sql(plan["sql"])
            timed(steps, "Run SQL in DuckDB", started, f"{len(rows)} rows returned")
        elif route == "semantic":
            search, filters = plan.get("search", question), plan.get("filters") or {}
            columns, rows = run_similarity(search, filters)
            if not rows and filters:
                timed(steps, "Vector search in Chroma", started, f"no claim matches the filters {filters}")
                started = time.perf_counter()
                plan["filters"] = {}
                columns, rows = run_similarity(search, {})
            timed(steps, "Vector search in Chroma", started, f"{len(rows)} most similar claims")
        else:
            raise ValueError(f"Unknown route: {route}")
    except Exception as error:
        raise HTTPException(status_code=422, detail=f"Could not run the query: {error}")

    started = time.perf_counter()
    method = plan["sql"] if route == "sql" else json.dumps({"search": plan.get("search"), "filters": plan.get("filters")})
    result = json.dumps({"columns": columns, "rows": rows}, default=str)
    answer = chat_json(ANSWER_PROMPT, f"Question: {question}\n\nMethod ({route}): {method}\n\nResult: {result}")
    timed(steps, "Explain result", started)

    return {
        "answer": answer.get("answer", ""),
        "route": route,
        "sql": plan.get("sql"),
        "search": plan.get("search"),
        "filters": plan.get("filters"),
        "columns": columns,
        "rows": rows,
        "steps": steps,
    }
