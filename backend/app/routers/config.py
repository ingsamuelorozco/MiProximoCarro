"""TRM, ciudades, perfiles y metadatos de configuración."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ..db import consultar, fuentes_por_id
from ..services.config import cfg, meta
from ..services.trm import obtener_trm

router = APIRouter(prefix="/api/config", tags=["Configuración"])


@router.get("/trm", summary="TRM vigente (datos.gov.co con respaldo)")
def trm() -> dict[str, Any]:
    return obtener_trm()


@router.get("/ciudades", summary="Ciudades con parámetros de combustible, matrícula y pico y placa")
def ciudades() -> dict[str, Any]:
    c = cfg("ciudades")
    return {"vigencia": c["vigencia"], "fuente_url": c["fuente_url"], "fecha_consulta": c["fecha_consulta"],
            "defecto": c["ciudad_defecto"], "ciudades": [{"id": k, **v} for k, v in c["ciudades"].items()]}


@router.get("/perfiles", summary="Perfiles de uso del Puntaje MiProximoCarro")
def perfiles() -> dict[str, Any]:
    return cfg("perfiles")


@router.get("/metodologia", summary="Parámetros publicados para la página de metodología")
def metodologia() -> dict[str, Any]:
    return {
        "fiabilidad": cfg("fiabilidad"), "indices": cfg("indices"), "altura": cfg("altura"),
        "credito": cfg("credito"), "seguros": cfg("seguros"), "depreciacion": cfg("depreciacion"),
        "mantenimiento": cfg("mantenimiento"), "soat": cfg("tarifas_soat"), "matricula": cfg("matricula"),
        "vigencias": {n: meta(n) for n in ("tarifas_soat", "matricula", "ciudades", "credito", "seguros", "depreciacion")},
    }


@router.get("/fuentes", summary="Registro de fuentes")
def fuentes() -> list[dict[str, Any]]:
    return list(fuentes_por_id().values())


@router.get("/imagenes", summary="Imágenes con autor y licencia")
def imagenes() -> list[dict[str, Any]]:
    return consultar("SELECT * FROM imagenes")
