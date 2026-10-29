from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from . import excel, guide
from .stores import chroma_collection

app = FastAPI(title="Foyer AI demo")
app.add_middleware(GZipMiddleware, minimum_size=1000)  # the single-file website shrinks from 260 KB to 80 KB
app.include_router(excel.router)
app.include_router(guide.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/warmup")
def warmup():
    # On AWS, a schedule calls this every 5 minutes so one Lambda instance stays loaded and ready.
    chroma_collection("claims")
    chroma_collection("guide")
    return {"status": "warm"}


# In production the built React app is served by the same server.
frontend = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend.exists():
    app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
