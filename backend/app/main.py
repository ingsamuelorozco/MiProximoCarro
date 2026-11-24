"""MiProximoCarro API — FastAPI con CORS, GZip, ETag, rate limit y errores con formato único."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException

from .db import DB_PATH, uno
from .routers import actualizados, catalogo, comparar, config, financiero, fiabilidad, vehiculos

LIMITE = os.getenv("MIPROXIMOCARRO_RATE_LIMIT", "120/minute")
limiter = Limiter(key_func=get_remote_address, default_limits=[LIMITE])

app = FastAPI(
    title="MiProximoCarro API",
    version="1.0.0",
    description="La verdad completa sobre un carro antes de pagarlo: dimensiones reales, costo real en Colombia y fiabilidad.",
    docs_url="/docs",
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=800)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("MIPROXIMOCARRO_CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _error(status: int, codigo: str, mensaje: str, detalle=None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"codigo": codigo, "mensaje": mensaje, "detalle": detalle})


@app.exception_handler(StarletteHTTPException)
async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "codigo" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    codigo = {404: "no_encontrado", 405: "metodo_no_permitido"}.get(exc.status_code, "error_http")
    return _error(exc.status_code, codigo, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
    detalle = [{"campo": ".".join(str(x) for x in e["loc"]), "mensaje": e["msg"]} for e in exc.errors()]
    return _error(422, "validacion", "Datos de entrada no válidos", detalle)


@app.exception_handler(RateLimitExceeded)
async def _limite(_: Request, exc: RateLimitExceeded) -> JSONResponse:
    return _error(429, "limite_excedido", "Demasiadas solicitudes; intenta en un minuto", str(exc.detail))


@app.exception_handler(Exception)
async def _interno(_: Request, exc: Exception) -> JSONResponse:
    return _error(500, "error_interno", "Error interno del servidor", type(exc).__name__)


@app.middleware("http")
async def etag_y_cache(request: Request, call_next):
    respuesta = await call_next(request)
    if request.method != "GET" or not request.url.path.startswith("/api/") or respuesta.status_code != 200:
        return respuesta
    cuerpo = b"".join([trozo async for trozo in respuesta.body_iterator])
    etag = '"' + hashlib.sha1(cuerpo).hexdigest()[:20] + '"'
    max_age = 60 if request.url.path.startswith("/api/config/trm") else 300
    headers = {k: v for k, v in respuesta.headers.items() if k.lower() not in ("content-length", "etag")}
    headers.update({"ETag": etag, "Cache-Control": f"public, max-age={max_age}"})
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag, "Cache-Control": headers["Cache-Control"]})
    return Response(content=cuerpo, status_code=200, headers=headers, media_type=respuesta.media_type)


for r in (catalogo, vehiculos, comparar, fiabilidad, actualizados, financiero, config):
    app.include_router(r.router)


@app.get("/api/salud", tags=["Salud"], summary="Estado y número de registros")
def salud() -> dict:
    n = uno("SELECT COUNT(*) AS n FROM vehiculos")["n"]
    f = uno("SELECT COUNT(*) AS n FROM fiabilidad")["n"]
    gen = uno("SELECT valor FROM meta WHERE clave = 'generado'")
    return {"estado": "ok", "vehiculos": n, "resenas": f, "base": DB_PATH.name, "generada": gen["valor"] if gen else None}


# Sirve el build del frontend si existe (un solo contenedor).
DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{ruta:path}", include_in_schema=False)
    def spa(ruta: str):
        archivo = DIST / ruta
        if ruta and archivo.is_file() and DIST in archivo.resolve().parents:
            return FileResponse(archivo)
        return FileResponse(DIST / "index.html")
