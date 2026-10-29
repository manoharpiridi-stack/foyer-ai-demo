import json
import time
from contextlib import contextmanager

from .llm import track_usage


@contextmanager
def log_question(event: str, question: str):
    """Writes one JSON line per question to the logs (CloudWatch on AWS): what was asked, how it went, time and cost.

    The caller adds details to the yielded dict (route, SQL, citations...). CloudWatch reads the JSON fields
    for its metrics, saved queries and the error alarm (terraform/monitoring.tf).
    """
    record = {"event": event, "question": question}
    started = time.perf_counter()
    with track_usage() as usage:
        try:
            yield record
            record["status"] = "ok"
        except Exception as error:
            record.update(status="error", error=str(getattr(error, "detail", error)))
            raise
        finally:
            record.update(total_ms=round((time.perf_counter() - started) * 1000), **usage.summary())
            print(json.dumps(record, ensure_ascii=False, default=str), flush=True)
