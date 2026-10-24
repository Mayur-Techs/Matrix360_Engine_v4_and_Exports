"""Matrix 360 & LeadScope AI Studio — Vercel / Cloud Gateway Entrypoint.

Provides immediate FastAPI entrypoint recognition for Vercel edge deployment,
serving the static client interface while routing data calls to the Render engine.
"""
from __future__ import annotations

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Matrix 360 Web Gateway", version="1.0.0")

_ROOT = Path(__file__).resolve().parent

if (_ROOT / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(_ROOT / "assets")), name="assets")


@app.get("/styles.css")
def get_styles():
    return FileResponse(_ROOT / "styles.css", media_type="text/css")


@app.get("/overrides.css")
def get_overrides():
    return FileResponse(_ROOT / "overrides.css", media_type="text/css")


@app.get("/app.js")
def get_script():
    return FileResponse(_ROOT / "app.js", media_type="application/javascript")


@app.get("/favicon.svg")
def get_favicon():
    return FileResponse(_ROOT / "favicon.svg", media_type="image/svg+xml")


@app.get("/healthz")
@app.get("/health")
def health():
    return {"status": "ok", "service": "matrix360-vercel-gateway"}


@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    file_path = _ROOT / full_path
    if full_path and file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    return FileResponse(_ROOT / "index.html", media_type="text/html")
