"""Puntaje de fiabilidad (fórmula pública) y Puntaje MiProximoCarro por perfil."""
from __future__ import annotations

from typing import Any

from .config import cfg


def puntaje_fiabilidad(desglose: dict[str, float], alertas: list[dict[str, Any]] | None = None) -> float:
    c = cfg("fiabilidad")
    total = sum(c["pesos"][k] * float(desglose[k]) for k in c["pesos"])
    if alertas and any(a.get("nivel") == "ROJA" for a in alertas):
        total = min(total, c["tope_con_alerta_roja"])
    return round(max(1.0, min(10.0, total)), 1)


def etiqueta_fiabilidad(puntaje: float | None) -> str | None:
    if puntaje is None:
        return None
    return next(r["etiqueta"] for r in cfg("fiabilidad")["rangos"] if puntaje >= r["min"])


def _norm(valores: list[float | None], mayor_mejor: bool) -> list[float | None]:
    validos = [v for v in valores if v is not None]
    if not validos:
        return [None] * len(valores)
    lo, hi = min(validos), max(validos)
    out: list[float | None] = []
    for v in valores:
        if v is None:
            out.append(None)
        elif hi == lo:
            out.append(1.0)
        else:
            x = (v - lo) / (hi - lo)
            out.append(x if mayor_mejor else 1 - x)
    return out


def _promedio(*xs: float | None) -> float | None:
    v = [x for x in xs if x is not None]
    return sum(v) / len(v) if v else None


def dimensiones(vehiculos: list[dict[str, Any]]) -> list[dict[str, float | None]]:
    """Calcula cada dimensión del puntaje normalizada 0–1 dentro del conjunto."""
    def col(k):
        return [v.get(k) for v in vehiculos]

    eficiencia_kml = [v.get("consumo_mixto_kml") for v in vehiculos]
    # Para eléctricos, equivalencia aproximada en km/l (factor configurable, documentado en metodología).
    factor = cfg("combustibles")["equivalencia_kml_bev_factor"]
    for i, v in enumerate(vehiculos):
        if eficiencia_kml[i] is None and v.get("consumo_kwh_100km"):
            eficiencia_kml[i] = factor / v["consumo_kwh_100km"]
    adas = [len(v.get("adas_incluidas") or []) for v in vehiculos]
    n = {
        "costo": _norm(col("precio_total_en_calle_cop"), False),
        "eficiencia": _norm(eficiencia_kml, True),
        "baul": _norm(col("capacidad_baul_litros"), True),
        "eje": _norm(col("distancia_entre_ejes_mm"), True),
        "plazas": _norm(col("plazas"), True),
        "hp": _norm(col("potencia_hp"), True),
        "pp": _norm(col("relacion_peso_potencia"), False),
        "acel": _norm(col("aceleracion_0_100_seg"), False),
        "fiab": _norm(col("puntaje_fiabilidad"), True),
        "airbags": _norm(col("numero_airbags"), True),
        "ncap": _norm(col("ncap_estrellas"), True),
        "adas": _norm(adas, True),
        "garaje": _norm(col("indice_garaje_nivel"), True),
        "rompe": _norm(col("indice_rompemuelle_nivel"), True),
        "giro": _norm(col("radio_giro_metros"), False),
        "pantalla": _norm(col("pantalla_multimedia_pulgadas"), True),
        "reventa": _norm(col("retencion_5_anios"), True),
    }
    res = []
    for i in range(len(vehiculos)):
        g = lambda k: n[k][i]  # noqa: E731
        res.append({
            "costo": g("costo"),
            "eficiencia": g("eficiencia"),
            "espacio": _promedio(g("baul"), g("eje"), g("plazas")),
            "desempeno": _promedio(g("hp"), g("pp"), g("acel")),
            "fiabilidad": g("fiab"),
            "seguridad": _promedio(g("airbags"), g("ncap"), g("adas")),
            "urbano": _promedio(g("garaje"), g("rompe"), g("giro")),
            "equipamiento": _promedio(g("pantalla"), g("adas")),
            "reventa": g("reventa"),
        })
    return res


def puntaje_miproximocarro(vehiculos: list[dict[str, Any]], perfil: str | None = None) -> list[dict[str, Any]]:
    p = cfg("perfiles")
    perfil_id = perfil if perfil in p["perfiles"] else p["perfil_defecto"]
    pesos = p["perfiles"][perfil_id]["pesos"]
    dims = dimensiones(vehiculos)
    salida = []
    for v, d in zip(vehiculos, dims):
        aportes = []
        total = 0.0
        peso_usado = 0.0
        for dim, w in pesos.items():
            val = d.get(dim)
            if val is None:
                continue
            aporte = val * w * 100
            total += aporte
            peso_usado += w
            aportes.append({"dimension": dim, "peso": w, "valor_normalizado": round(val, 3), "aporte": round(aporte, 1)})
        puntaje = total / peso_usado if peso_usado else 0.0
        penalizacion = 0.0
        if v.get("tiene_alerta_roja"):
            penalizacion = puntaje * p["penalizacion_alerta_roja"]
            puntaje -= penalizacion
        salida.append({
            "id": v.get("id"), "perfil": perfil_id, "puntaje": round(puntaje),
            "aportes": aportes, "penalizacion_alerta_roja": round(penalizacion, 1),
        })
    return salida
