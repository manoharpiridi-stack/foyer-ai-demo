import os
import shutil
from functools import cache
from pathlib import Path

import duckdb

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CLAIMS_XLSX = DATA_DIR / "claims.xlsx"
CLAIMS_DB = DATA_DIR / "claims.duckdb"
DATA_QUALITY_JSON = DATA_DIR / "data_quality.json"
CHROMA_DIR = DATA_DIR / "chroma"
GUIDE_JSON = DATA_DIR / "guide.json"
GUIDE_EN_JSON = DATA_DIR / "guide_en.json"


def chroma_client():
    # Imported here, not at the top: chromadb is slow to load, and Lambda gives the server only 10 s to start.
    import chromadb
    from chromadb.config import Settings

    path = CHROMA_DIR
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        # Lambda's filesystem is read-only except /tmp, and Chroma needs to write next to its index.
        path = Path("/tmp/chroma")
        if not path.exists():
            shutil.copytree(CHROMA_DIR, path)
    return chromadb.PersistentClient(path=str(path), settings=Settings(anonymized_telemetry=False))


@cache
def chroma_collection(name: str):
    """Opened on first use, then kept in memory for the following requests."""
    return chroma_client().get_collection(name)


def duckdb_readonly():
    # Read-only and no file/network access: generated SQL can only read the claims table.
    return duckdb.connect(str(CLAIMS_DB), read_only=True, config={"enable_external_access": False})
