"""Herramientas financieras: puesta en calle, crédito, seguro, TCO, reventa y asequibilidad."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ..db import todos_los_vehiculos, vehiculo_completo
from ..errores import invalido, no_encontrado
from ..schemas import AsequibilidadIn, CreditoIn, PuestaEnCalleIn, ReventaIn, SeguroIn, TcoIn
from ..services import financiero, reventa, seguro, tco
from ..services.config import cfg
from ..services.trm import obtener_trm
from .vehiculos import tarjeta

router = APIRouter(prefix="/api/financiero", tags=["Financiero"])


def _vehiculo(vid: int) -> dict:
    v = vehiculo_completo(vid)
    if not v:
        raise no_encontrado("Vehículo", vid)
    return v


def _ciudad_ok(c: str | None) -> None:
    if c and c not in cfg("ciudades")["ciudades"]:
        raise invalido("Ciudad no válida", {"ciudad": c})


@router.post("/puesta-en-calle", summary="Precio base, SOAT, matrícula y total")
def puesta_en_calle(d: PuestaEnCalleIn) -> dict[str, Any]:
    _ciudad_ok(d.ciudad)
    if d.vehiculo_id:
        v = _vehiculo(d.vehiculo_id)
        precio, cc, carr, tipo = d.precio_base_cop or v["precio_base_cop"], v["cilindraje_cc"], v["carroceria"], v["tipo_combustible"]
    elif d.precio_base_cop:
        precio, cc, carr, tipo = d.precio_base_cop, d.cilindraje_cc, d.carroceria, d.tipo_combustible
    else:
        raise invalido("Envía vehiculo_id o precio_base_cop")
    return financiero.puesta_en_calle(precio, cc, carr, tipo, d.ciudad, d.mes_compra, d.incluir_alistamiento)


@router.post("/credito", summary="Cuota, intereses, tabla de amortización y tres escenarios")
def credito(d: CreditoIn) -> dict[str, Any]:
    kw = d.model_dump(exclude={"precio_cop", "abonos", "incluir_tabla"})
    kw["abonos"] = [a.model_dump() for a in d.abonos]
    res = financiero.credito(d.precio_cop, incluir_tabla=d.incluir_tabla, **kw)
    res["escenarios"] = financiero.escenarios_credito(d.precio_cop, **{k: v for k, v in kw.items() if k != "abonos"})
    return res


@router.post("/seguro", summary="Rango estimado del seguro todo riesgo y SOAT")
def seguro_est(d: SeguroIn) -> dict[str, Any]:
    _ciudad_ok(d.ciudad)
    if d.vehiculo_id:
        v = _vehiculo(d.vehiculo_id)
        valor = d.valor_asegurado_cop or financiero.avaluo_estimado(v["precio_base_cop"])
        res = seguro.todo_riesgo(valor, v["segmento"], d.ciudad, d.edad_conductor, d.uso, d.antiguedad_anios,
                                 v["riesgo_hurto"], d.deducible, v["tipo_combustible"])
        res["soat"] = financiero.soat(v["cilindraje_cc"], v["carroceria"], v["tipo_combustible"], d.antiguedad_anios)
        return res
    if not d.valor_asegurado_cop:
        raise invalido("Envía vehiculo_id o valor_asegurado_cop")
    return seguro.todo_riesgo(d.valor_asegurado_cop, d.segmento or "", d.ciudad, d.edad_conductor, d.uso,
                              d.antiguedad_anios, "Medio", d.deducible)


@router.post("/tco", summary="Costo total de propiedad a N años")
def costo_total(d: TcoIn) -> dict[str, Any]:
    _ciudad_ok(d.ciudad)
    v = _vehiculo(d.vehiculo_id)
    res = tco.tco(v, d.anios, d.km_anio, d.mezcla_ciudad, d.ciudad, d.carga_casa_pct, d.financiar)
    if d.comparar_con_id:
        otro = _vehiculo(d.comparar_con_id)
        res["punto_equilibrio"] = tco.punto_equilibrio(v, otro, d.ciudad, d.km_anio, d.carga_casa_pct)
    return res


@router.post("/reventa", summary="Curva de valor residual")
def curva_reventa(d: ReventaIn) -> list[dict[str, Any]]:
    trm = d.trm or obtener_trm()["valor"]
    out = []
    for i in d.vehiculo_ids:
        v = _vehiculo(i)
        out.append({"id": i, "nombre": f"{v['marca']} {v['modelo']} {v['anio']} {v['version']}",
                    **reventa.curva_reventa(v["precio_base_cop"], v["retencion_valor"], v["depreciacion_estimada"], trm)})
    return out


@router.post("/asequibilidad", summary="Qué carros alcanzan según ingresos")
def asequibilidad(d: AsequibilidadIn) -> dict[str, Any]:
    _ciudad_ok(d.ciudad)
    presupuesto = d.ingreso_mensual_cop * d.max_pct_ingreso
    out = []
    for base in todos_los_vehiculos():
        if base["estado_comercial"] != "Vigente":
            continue
        v = vehiculo_completo(base["id"])
        cr = financiero.credito(v["precio_base_cop"], cuota_inicial_cop=min(d.cuota_inicial_cop, v["precio_base_cop"]),
                                plazo_meses=d.plazo_meses, incluir_tabla=False)
        seg = seguro.todo_riesgo(financiero.avaluo_estimado(v["precio_base_cop"]), v["segmento"], d.ciudad,
                                 riesgo_hurto=v["riesgo_hurto"], tipo_combustible=v["tipo_combustible"])["prima_anual_central_cop"] / 12
        km = d.km_anio or cfg("combustibles")["km_anuales_defecto"]
        energia = tco.costo_energia_por_km(v, d.ciudad)["costo_por_km_cop"] * km / 12
        mant = tco.mantenimiento_anual(v["nivel_costo_mantenimiento"], km, v["tipo_combustible"]) / 12
        mensual = cr["cuota_mensual_con_seguros_cop"] + seg + energia + mant
        if mensual <= presupuesto:
            out.append({**tarjeta(v), "costo_mensual_cop": round(mensual, -3), "holgura_cop": round(presupuesto - mensual, -3),
                        "desglose_mensual": {"cuota": cr["cuota_mensual_con_seguros_cop"], "seguro": round(seg),
                                             "energia": round(energia), "mantenimiento": round(mant)}})
    out.sort(key=lambda x: (-x["puntaje_miproximocarro_base"], -x["holgura_cop"]))
    return {"presupuesto_mensual_cop": round(presupuesto), "total": len(out), "resultados": out[:d.limite],
            "aviso": "Estimación orientativa; no es una oferta de crédito ni una cotización."}
