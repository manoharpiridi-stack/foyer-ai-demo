import json
import os
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMS = 256  # smaller vectors: 6x less storage, small quality loss

# USD per million tokens for the default models; the cost in the logs is an estimate.
PRICE_PER_MILLION = {"input_tokens": 0.40, "output_tokens": 1.60, "embedding_tokens": 0.02}

client = OpenAI()


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    embedding_tokens: int = 0

    def summary(self) -> dict:
        cost = sum(count * PRICE_PER_MILLION[name] / 1_000_000 for name, count in asdict(self).items())
        return {**asdict(self), "cost_usd": round(cost, 6)}


_usage: ContextVar[Usage | None] = ContextVar("usage", default=None)


@contextmanager
def track_usage():
    """Counts the tokens of every OpenAI call made inside the `with` block."""
    usage = Usage()
    token = _usage.set(usage)
    try:
        yield usage
    finally:
        _usage.reset(token)


def chat_json(system: str, user: str) -> dict:
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
    )
    if usage := _usage.get():
        usage.input_tokens += response.usage.prompt_tokens
        usage.output_tokens += response.usage.completion_tokens
    return json.loads(response.choices[0].message.content)


def embed(texts: list[str], batch_size: int = 1000) -> list[list[float]]:
    vectors = []
    for i in range(0, len(texts), batch_size):
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts[i : i + batch_size],
            dimensions=EMBEDDING_DIMS,
        )
        if usage := _usage.get():
            usage.embedding_tokens += response.usage.total_tokens
        vectors.extend(item.embedding for item in response.data)
    return vectors
