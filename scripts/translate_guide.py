"""Translate data/guide.json into English once, keeping every passage id: data/guide_en.json."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.llm import chat_json
from backend.stores import GUIDE_EN_JSON, GUIDE_JSON

PROMPT = """You translate pages of a French information guide about living in Luxembourg into clear English.
You receive one page as JSON. Return the same JSON with every French text value translated into English.
Keep all keys, ids, "type" values, numbers, amounts, dates and URLs exactly as they are.
Keep official names in French when they have no English equivalent (e.g. "Guichet.lu", "chèque-service accueil"),
adding a short English explanation in brackets the first time if useful. Return only the JSON."""

TRANSLATED = ("title", "summary", "blocks")


def translate_page(page: dict) -> dict:
    source = {k: page[k] for k in TRANSLATED}
    for attempt in range(2):
        result = chat_json(PROMPT, json.dumps(source, ensure_ascii=False))
        same_blocks = [(b["type"], b.get("id")) for b in result.get("blocks", [])] == [(b["type"], b.get("id")) for b in page["blocks"]]
        if same_blocks:
            return {**page, **{k: result[k] for k in TRANSLATED}}
        print(f"  {page['id']}: block structure changed, retrying")
    raise RuntimeError(f"Could not translate {page['id']} without changing its structure")


if __name__ == "__main__":
    pages = json.loads(GUIDE_JSON.read_text(encoding="utf-8"))
    translated = []
    for page in pages:
        translated.append(translate_page(page))
        print(f"Translated {page['id']}")
    GUIDE_EN_JSON.write_text(json.dumps(translated, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Saved {len(translated)} pages to {GUIDE_EN_JSON}")
