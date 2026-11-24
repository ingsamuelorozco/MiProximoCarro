"""Acceso a SQLite (solo lectura en runtime) y utilidades de consulta."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

RAIZ = Path(__file__).resolve().parent.parent.parent
DB_PATH = Path(os.getenv("MIPROXIMOCARRO_DB_PATH", RAIZ / "db" / "cars.db"))
if not DB_PATH.is_absolute():
    DB_PATH = RAIZ / DB_PATH

COLUMNAS_JSON = {
    "adas_incluidas", "campos_estimados", "fuentes_ids", "desglose", "retencion_valor", "pros_reales",
    "fallas_comunes_y_contras", "alertas", "alternativas_recomendadas", "vehiculo_ids", "categorias", "cambios",
    "marcas", "modelos",
}
COLUMNAS_BOOL = {
    "frenos_abs_ebd", "control_estabilidad_esc", "asistente_arranque_pendiente", "anclajes_isofix", "techo_corredizo",
    "camara_reversa", "carga_inalambrica", "llave_inteligente", "luces_led", "garantia_km_ilimitada",
    "tiene_alerta_roja", "contiene_logo",
}


def _conectar() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base {DB_PATH}. Ejecuta: python scripts/seed.py")
    try:
        con = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True, check_same_thread=False)
        con.execute("SELECT 1 FROM meta LIMIT 1")
    except sqlite3.OperationalError:
        con = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro&immutable=1", uri=True, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


@contextmanager
def conexion() -> Iterator[sqlite3.Connection]:
    con = _conectar()
    try:
        yield con
    finally:
        con.close()


def fila(r: sqlite3.Row | None) -> dict[str, Any] | None:
    if r is None:
        return None
    d = dict(r)
    for k, v in d.items():
        if k in COLUMNAS_JSON and isinstance(v, str):
            d[k] = json.loads(v)
        elif k in COLUMNAS_BOOL and v is not None:
            d[k] = bool(v)
    return d


def consultar(sql: str, params: tuple | list = ()) -> list[dict[str, Any]]:
    with conexion() as con:
        return [fila(r) for r in con.execute(sql, params)]  # type: ignore[misc]


def uno(sql: str, params: tuple | list = ()) -> dict[str, Any] | None:
    with conexion() as con:
        return fila(con.execute(sql, params).fetchone())


@lru_cache(maxsize=1)
def todos_los_vehiculos() -> tuple[dict[str, Any], ...]:
    """Catálogo completo en memoria (cientos de filas: cabe sin problema)."""
    vs = consultar("SELECT * FROM vehiculos ORDER BY marca, modelo, anio DESC, precio_base_cop")
    return tuple(vs)


@lru_cache(maxsize=1)
def vehiculos_por_id() -> dict[int, dict[str, Any]]:
    return {v["id"]: v for v in todos_los_vehiculos()}


@lru_cache(maxsize=1)
def fiabilidad_por_id() -> dict[int, dict[str, Any]]:
    return {f["vehiculo_id"]: f for f in consultar("SELECT * FROM fiabilidad")}


@lru_cache(maxsize=1)
def fuentes_por_id() -> dict[str, dict[str, Any]]:
    return {f["id"]: f for f in consultar("SELECT * FROM fuentes")}


def vehiculo_completo(vid: int) -> dict[str, Any] | None:
    """Vehículo con los campos de fiabilidad necesarios para cálculos financieros."""
    v = vehiculos_por_id().get(vid)
    if not v:
        return None
    f = fiabilidad_por_id().get(vid, {})
    return {**v, "retencion_valor": f.get("retencion_valor"), "puntaje_fiabilidad": v["puntaje_fiabilidad"],
            "disponibilidad_repuestos": f.get("disponibilidad_repuestos")}


def limpiar_cache() -> None:
    for fn in (todos_los_vehiculos, vehiculos_por_id, fiabilidad_por_id, fuentes_por_id):
        fn.cache_clear()
