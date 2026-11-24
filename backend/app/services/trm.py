"""TRM vigente desde datos abiertos de Colombia, con caché y valor de respaldo."""
from __future__ import annotations

import os
import threading
import time
from typing import Any

import httpx

from .config import cfg

_lock = threading.Lock()
_cache: dict[str, Any] = {}


def obtener_trm() -> dict[str, Any]:
    c = cfg("trm")
    ttl = c["cache_horas"] * 3600
    with _lock:
        if _cache and time.time() - _cache["_t"] < ttl:
            return {k: v for k, v in _cache.items() if not k.startswith("_")}
    resultado = {"valor": c["respaldo_cop_por_usd"], "vigencia": c["respaldo_vigencia"], "origen": "respaldo",
                 "fuente_url": c["fuente_url"], "fecha_consulta": c["fecha_consulta"]}
    if os.getenv("MIPROXIMOCARRO_TRM_OFFLINE", "0") != "1":
        try:
            r = httpx.get(c["fuente_url"], params={"$limit": 1, "$order": "vigenciadesde DESC"}, timeout=c["timeout_seg"])
            r.raise_for_status()
            dato = r.json()[0]
            resultado = {"valor": float(dato["valor"]), "vigencia": f"{dato['vigenciadesde'][:10]}/{dato['vigenciahasta'][:10]}",
                         "origen": "datos.gov.co", "fuente_url": c["fuente_url"], "fecha_consulta": time.strftime("%Y-%m-%d")}
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            pass
    with _lock:
        _cache.clear()
        _cache.update(resultado, _t=time.time())
    return resultado
