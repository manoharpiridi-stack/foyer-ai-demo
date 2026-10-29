"""Clean data/claims.xlsx, then load it into DuckDB (for SQL) and Chroma (one vector per row, for similarity search)."""

import json
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.llm import embed
from backend.stores import CLAIMS_DB, CLAIMS_XLSX, DATA_QUALITY_JSON, chroma_client
from scripts.cleaning import clean_claims

BATCH = 5000

df, report = clean_claims(pd.read_excel(CLAIMS_XLSX))
DATA_QUALITY_JSON.write_text(json.dumps(report, indent=1), encoding="utf-8")
print(f"Read {report['rows_read']:,} rows, kept {report['rows_kept']:,}")
for fix in report["fixes"]:
    print(f"  {fix['rows']:>6,}  {fix['issue']} -> {fix['fix']}")

CLAIMS_DB.unlink(missing_ok=True)
with duckdb.connect(str(CLAIMS_DB)) as con:
    con.execute("CREATE TABLE claims AS SELECT * FROM df")
    print("DuckDB rows:", con.execute("SELECT count(*) FROM claims").fetchone()[0])

# Many rows share the same description, so embed each distinct text only once.
unique_texts = df["description"].unique().tolist()
vector_by_text = dict(zip(unique_texts, embed(unique_texts)))
print(f"Embedded {len(unique_texts):,} distinct descriptions")

chroma = chroma_client()
if "claims" in [c.name for c in chroma.list_collections()]:
    chroma.delete_collection("claims")
collection = chroma.create_collection("claims", metadata={"hnsw:space": "cosine"})

for start in range(0, len(df), BATCH):
    part = df.iloc[start : start + BATCH]
    collection.add(
        ids=part["claim_id"].tolist(),
        embeddings=[vector_by_text[t] for t in part["description"]],
        documents=part["description"].tolist(),
        metadatas=[
            {"product": r.product, "peril": r.peril, "canton": r.canton, "status": r.status, "year": r.claim_date.year}
            for r in part.itertuples()
        ],
    )
    print(f"Chroma: {start + len(part):,} rows")
