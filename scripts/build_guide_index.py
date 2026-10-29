"""Download the lux-guide.github.io knowledge base, save it as data/guide.json and index each passage in Chroma."""

import json
import sys
import urllib.request
from pathlib import Path

import json5

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.llm import embed
from backend.stores import GUIDE_JSON, chroma_client

SITE = "https://lux-guide.github.io"


def download(path: str) -> str:
    with urllib.request.urlopen(f"{SITE}/{path}") as response:
        return response.read().decode("utf-8")


def js_object(source: str, marker: str) -> dict:
    """The site's data files are `marker = { ... };` JavaScript literals, which json5 can parse."""
    return json5.loads(source.split(marker, 1)[1].strip().rstrip(";"))


def strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [s for v in value for s in strings(v)]
    if isinstance(value, dict):
        return [s for k, v in value.items() if k not in {"u", "id", "cocher", "actif"} for s in strings(v)]
    return []


def vehicle_body(fiche: dict) -> list:
    """The vehicle page uses custom blocks (steps, checklists, tabs) instead of paragraphs; flatten them to text."""
    guide = fiche["guide"]
    body = [" — ".join(strings(r)) for r in guide["reperes"]]
    body += [" — ".join(strings(case)) for case in guide["cas"]["items"]]
    for tab in guide["onglets"]:
        body.append({"h": tab["titre"]})
        for block in tab["blocs"]:
            items = next((v for v in block.values() if isinstance(v, list) and isinstance(v[0], dict)), None) if isinstance(block, dict) else None
            body += [" — ".join(strings(item)) for item in items] if items else [" — ".join(strings(block))]
    return body


def to_page(fiche: dict, faq: list) -> dict:
    page_id = fiche["id"]
    blocks, n = [], 0

    def passage(kind: str, **fields):
        nonlocal n
        n += 1
        blocks.append({"type": kind, "id": f"{page_id}-{n}", **fields})

    for item in fiche.get("corps") or vehicle_body(fiche):
        if isinstance(item, dict):
            blocks.append({"type": "h", "text": item["h"]})
        else:
            passage("p", text=item)
    for table in fiche.get("tableaux", []):
        passage("table", title=table["titre"], columns=table["colonnes"], rows=table["lignes"])
    if fiche.get("aRetenir"):
        blocks.append({"type": "h", "text": "À retenir"})
        passage("p", text=" ".join(fiche["aRetenir"]))
    questions = [q for q in faq if q.get("fiche") == page_id]
    if questions:
        blocks.append({"type": "h", "text": "Questions fréquentes"})
        for q in questions:
            passage("faq", q=q["q"], a=q["a"])

    return {
        "id": page_id,
        "title": fiche["titre"],
        "category": fiche["cat"],
        "summary": fiche["resume"],
        "url": f"{SITE}/#fiche/{page_id}",
        "sources": [{"title": s["t"], "url": s["u"]} for s in fiche.get("sources", [])],
        "blocks": blocks,
    }


def passage_text(block: dict) -> str:
    if block["type"] == "table":
        rows = "; ".join(", ".join(f"{c} : {v}" for c, v in zip(block["columns"], row)) for row in block["rows"])
        return f"{block['title']}. {rows}"
    if block["type"] == "faq":
        return f"{block['q']} {block['a']}"
    return block["text"]


if __name__ == "__main__":
    vehicle = js_object(download("app/fiches/vehicule.js"), "window.FICHES.vehicule =")
    kb = js_object(download("app/kb.js").replace("window.FICHES.vehicule,", "null,"), "window.KB =")
    fiches = [f or vehicle for f in kb["fiches"]]
    pages = [to_page(f, kb["faq"]) for f in fiches]
    GUIDE_JSON.parent.mkdir(exist_ok=True)
    GUIDE_JSON.write_text(json.dumps(pages, ensure_ascii=False, indent=1), encoding="utf-8")

    # Each passage is embedded with its page title and heading, so a paragraph keeps its context.
    ids, texts, metadatas = [], [], []
    for page in pages:
        heading = ""
        for block in page["blocks"]:
            if block["type"] == "h":
                heading = block["text"]
                continue
            text = passage_text(block)
            ids.append(block["id"])
            texts.append(f"{page['title']} — {heading}\n{text}" if heading else f"{page['title']}\n{text}")
            metadatas.append({"page_id": page["id"], "page_title": page["title"]})

    chroma = chroma_client()
    if "guide" in [c.name for c in chroma.list_collections()]:
        chroma.delete_collection("guide")
    collection = chroma.create_collection("guide", metadata={"hnsw:space": "cosine"})
    collection.add(ids=ids, embeddings=embed(texts), documents=texts, metadatas=metadatas)
    print(f"Saved {len(pages)} pages and indexed {len(ids)} passages")
