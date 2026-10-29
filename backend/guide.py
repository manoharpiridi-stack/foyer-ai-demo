import json
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .llm import chat_json, embed
from .monitoring import log_question
from .stores import GUIDE_EN_JSON, GUIDE_JSON, chroma_collection

router = APIRouter(prefix="/api/guide")


def load_pages(path) -> dict:
    return {page["id"]: page for page in json.loads(path.read_text(encoding="utf-8"))}


# French is the original and is what search runs on; English is a translated copy for reading only.
PAGES = load_pages(GUIDE_JSON)
PAGES_BY_LANG = {"fr": PAGES, "en": load_pages(GUIDE_EN_JSON)}

CURRENT_PAGE_K = 3
GLOBAL_K = 6

ANSWER_PROMPT = """You are the assistant of an information guide for people settling in Luxembourg.
The reader is currently viewing the page "{title}".
The reader's situation: {situation}.
Answer ONLY from the numbered passages below; each starts with its id in square brackets.
The passages are in French, but always reply in the language of the question (an English question gets an English answer), in 2 to 5 sentences.
Reply with JSON: {{"language": "...", "answer": "...", "passage_ids": ["..."]}}
- language: the language the question is written in; the answer must be written in that language.
- passage_ids: the passages that support your answer, most important first.
- Short or vague questions ("is it free?") usually refer to the page being read: answer them from that page's passages.
- When the passages give different rules for different situations (for example EU and non-EU citizens), give the rule
  that applies to the reader's situation and say which situation it is. If the situation is unknown, give each rule.
- If the passages answer only part of the question, answer that part and say what the guide does not cover.
- If the passages do not answer the question, say briefly that the guide does not cover it and return an empty passage_ids list.

Passages:
{passages}"""


class Message(BaseModel):
    role: str
    content: str


class Profile(BaseModel):
    citizenship: str | None = None  # "EU" or "non-EU"
    car: bool = False
    family: bool = False

    def describe(self) -> str:
        parts = []
        if self.citizenship == "EU":
            parts.append("EU citizen")
        if self.citizenship == "non-EU":
            parts.append("non-EU citizen (ressortissant de pays tiers)")
        if self.car:
            parts.append("bringing a car")
        if self.family:
            parts.append("moving with family and children")
        return ", ".join(parts)


class Question(BaseModel):
    question: str
    page_id: str | None = None
    history: list[Message] = []
    profile: Profile = Profile()


def retrieve(question: str, page_id: str | None) -> list[dict]:
    vector = embed([question])
    queries = [(GLOBAL_K, None)]
    if page_id in PAGES:
        # Passages from the page being read are searched first, so "this page" questions stay on it.
        queries.insert(0, (CURRENT_PAGE_K, {"page_id": page_id}))
    hits, seen = [], set()
    for k, where in queries:
        result = chroma_collection("guide").query(query_embeddings=vector, n_results=k, where=where)
        for pid, text, meta in zip(result["ids"][0], result["documents"][0], result["metadatas"][0]):
            if pid not in seen:
                seen.add(pid)
                hits.append({"id": pid, "page_id": meta["page_id"], "page_title": meta["page_title"], "text": text})
    return hits


def timed(steps: list, name: str, started: float, detail: str = ""):
    steps.append({"name": name, "ms": round((time.perf_counter() - started) * 1000), "detail": detail})


@router.get("/pages")
def pages(lang: str = "fr"):
    return [{k: p[k] for k in ("id", "title", "category", "summary")} for p in PAGES_BY_LANG.get(lang, PAGES).values()]


@router.get("/pages/{page_id}")
def page(page_id: str, lang: str = "fr"):
    if page_id not in PAGES:
        raise HTTPException(status_code=404, detail="Unknown page")
    return PAGES_BY_LANG.get(lang, PAGES)[page_id]


@router.post("/ask")
def ask(body: Question):
    with log_question("guide", body.question) as record:
        result = answer_question(body)
        record.update(
            page_id=body.page_id,
            profile=body.profile.describe(),
            found=result["found"],
            answer_page=result["page_id"],
            cited=[s["id"] for s in result["sources"]],
            steps_ms={s["name"]: s["ms"] for s in result["steps"]},
        )
    return result


def answer_question(body: Question) -> dict:
    steps = []
    current = PAGES.get(body.page_id)

    started = time.perf_counter()
    # The situation is added to the search text too, so passages about the reader's case rank higher.
    situation = body.profile.describe()
    hits = retrieve(f"{body.question} ({situation})" if situation else body.question, body.page_id)
    on_page = sum(h["page_id"] == body.page_id for h in hits)
    timed(steps, "Retrieve passages", started, f"{len(hits)} passages, {on_page} from the current page")

    started = time.perf_counter()
    passages = "\n\n".join(f"[{h['id']}] {h['text']}" for h in hits)
    history = "\n".join(f"{m.role}: {m.content}" for m in body.history[-4:])
    prompt = ANSWER_PROMPT.format(
        title=current["title"] if current else "home page",
        situation=situation or "not given",
        passages=passages,
    )
    reply = chat_json(prompt, f"Conversation so far:\n{history}\n\nQuestion: {body.question}" if history else body.question)
    timed(steps, "Generate answer", started)

    # Keep only citations that point to passages we actually retrieved.
    started = time.perf_counter()
    by_id = {h["id"]: h for h in hits}
    cited = [pid for pid in reply.get("passage_ids", []) if pid in by_id]
    answer = reply.get("answer", "")
    if reply.get("passage_ids") and not cited:
        answer = "I could not find a passage in the guide that supports an answer to this question."
    timed(steps, "Check citations", started, f"{len(cited)} of {len(reply.get('passage_ids', []))} citations verified")

    target = by_id[cited[0]]["page_id"] if cited else body.page_id
    return {
        "answer": answer,
        "found": bool(cited),
        "page_id": target,
        "opened_other_page": bool(cited) and target != body.page_id,
        "passage_ids": [pid for pid in cited if by_id[pid]["page_id"] == target],
        "sources": [by_id[pid] for pid in cited],
        "retrieved": hits,
        "steps": steps,
    }
