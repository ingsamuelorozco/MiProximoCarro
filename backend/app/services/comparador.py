"""Comparador de hasta 10 vehículos: filas por categoría, ganadores, marcador y puntaje."""
from __future__ import annotations

from typing import Any, Callable

from . import altura, financiero, puntaje, reventa, seguro, tco
from .config import cfg, ciudad

# Reglas: max, min, info, bool, cat:<ranking>, nivel (mayor nivel gana)
Fila = tuple[str, str, str, Callable[[dict], Any] | None, str]


def _campo(k: str) -> Callable[[dict], Any]:
    return lambda v: v.get(k)


def definicion_filas() -> list[tuple[str, list[Fila]]]:
    """(categoría, [(clave, etiqueta, regla, getter, unidad)])."""
    return [
        ("Precios, Matrícula y SOAT", [
            ("precio_base_cop", "Precio base", "min", None, "cop"),
            ("soat_cop", "SOAT", "min", None, "cop"),
            ("matricula_cop", "Matrícula, trámites e impuesto", "min", None, "cop"),
            ("total_calle_cop", "Precio total en calle", "min", None, "cop"),
            ("cuota_cop", "Cuota estimada de crédito", "min", None, "cop"),
            ("seguro_cop", "Seguro todo riesgo estimado (central)", "min", None, "cop"),
            ("tco5_cop", "Costo total a 5 años", "min", None, "cop"),
        ]),
        ("Garantía y fiabilidad", [
            ("garantia_anos", "Garantía (años)", "max", None, "años"),
            ("garantia_km", "Garantía (km)", "max", None, "km"),
            ("puntaje_fiabilidad", "Puntaje de fiabilidad", "max", None, "/10"),
            ("nivel_costo_mantenimiento", "Costo de mantenimiento", "cat:nivel_costo_mantenimiento", None, ""),
            ("disponibilidad_repuestos", "Disponibilidad de repuestos", "cat:disponibilidad_repuestos", None, ""),
            ("retencion_5_anios", "Retención de valor a 5 años", "max", None, "%"),
        ]),
        ("Motor y rendimiento", [
            ("motor_descripcion", "Motor", "info", None, ""),
            ("cilindraje_cc", "Cilindraje", "info", None, "cc"),
            ("potencia_hp", "Potencia", "max", None, "hp"),
            ("torque_nm", "Torque", "max", None, "Nm"),
            ("relacion_peso_potencia", "Peso/potencia", "min", None, "kg/hp"),
            ("aceleracion_0_100_seg", "0 a 100 km/h", "min", None, "s"),
            ("velocidad_maxima_kmh", "Velocidad máxima", "max", None, "km/h"),
            ("potencia_ciudad_hp", "Potencia efectiva en tu ciudad", "max", None, "hp"),
        ]),
        ("Dimensiones, despeje y usabilidad urbana", [
            ("largo_mm", "Largo", "info", None, "mm"),
            ("ancho_con_espejos_mm", "Ancho con espejos", "info", None, "mm"),
            ("alto_mm", "Alto", "info", None, "mm"),
            ("distancia_libre_suelo_mm", "Despeje", "max", None, "mm"),
            ("capacidad_baul_litros", "Baúl", "max", None, "L"),
            ("capacidad_baul_abatido_litros", "Baúl abatido", "max", None, "L"),
            ("distancia_entre_ejes_mm", "Distancia entre ejes", "max", None, "mm"),
            ("radio_giro_metros", "Radio de giro", "min", None, "m"),
            ("capacidad_carga_kg", "Capacidad de carga", "max", None, "kg"),
            ("profundidad_vadeo_mm", "Profundidad de vadeo", "max", None, "mm"),
            ("indice_garaje_nivel", "Índice de Garaje", "nivel", None, ""),
            ("indice_rompemuelle_nivel", "Índice Rompemuelle", "nivel", None, ""),
        ]),
        ("Transmisión, chasis y frenos", [
            ("transmision_tipo", "Transmisión", "info", None, ""),
            ("numero_velocidades", "Número de velocidades", "info", None, ""),
            ("traccion", "Tracción", "info", None, ""),
            ("frenos_traseros", "Frenos traseros", "cat:frenos_traseros", None, ""),
            ("suspension_trasera", "Suspensión trasera", "cat:suspension_trasera", None, ""),
            ("direccion", "Dirección", "info", None, ""),
        ]),
        ("Consumo y autonomía", [
            ("consumo_ciudad_kml", "Consumo ciudad", "max", None, "km/l"),
            ("consumo_carretera_kml", "Consumo carretera", "max", None, "km/l"),
            ("consumo_mixto_kml", "Consumo mixto", "max", None, "km/l"),
            ("consumo_real_estimado_kml", "Consumo real estimado", "max", None, "km/l"),
            ("consumo_kwh_100km", "Consumo eléctrico", "min", None, "kWh/100 km"),
            ("autonomia_estimada_km", "Autonomía", "autonomia", None, "km"),
            ("costo_1000km_cop", "Costo de energía por 1.000 km", "min", None, "cop"),
        ]),
        ("Seguridad y ADAS", [
            ("numero_airbags", "Airbags", "max", None, ""),
            ("ncap_estrellas", "Estrellas NCAP", "ncap", None, "★"),
            ("num_adas", "Número de ADAS", "max", None, ""),
            ("frenos_abs_ebd", "ABS + EBD", "bool", None, ""),
            ("control_estabilidad_esc", "Control de estabilidad", "bool", None, ""),
            ("asistente_arranque_pendiente", "Asistente de arranque en pendiente", "bool", None, ""),
            ("anclajes_isofix", "Anclajes ISOFIX", "bool", None, ""),
        ]),
        ("Equipamiento", [
            ("pantalla_multimedia_pulgadas", "Pantalla", "max", None, "\""),
            ("apple_carplay_android_auto", "CarPlay / Android Auto", "cat:apple_carplay_android_auto", None, ""),
            ("aire_acondicionado", "Aire acondicionado", "cat:aire_acondicionado", None, ""),
            ("tapiceria", "Tapicería", "cat:tapiceria", None, ""),
            ("techo_corredizo", "Techo corredizo", "bool", None, ""),
            ("camara_reversa", "Cámara de reversa", "bool", None, ""),
        ]),
    ]


def _derivados(v: dict, ciudad_id: str | None) -> dict:
    cd = ciudad(ciudad_id)
    pec = financiero.puesta_en_calle(v["precio_base_cop"], v.get("cilindraje_cc"), v["carroceria"], v["tipo_combustible"], cd["id"],
                                     antiguedad_anios=financiero.antiguedad_compra(v["anio"], v.get("fecha_precio")))
    cred = financiero.credito(v["precio_base_cop"], incluir_tabla=False)
    seg = seguro.todo_riesgo(financiero.avaluo_estimado(v["precio_base_cop"]), v["segmento"], cd["id"],
                             riesgo_hurto=v.get("riesgo_hurto") or "Medio", tipo_combustible=v["tipo_combustible"])
    t = tco.tco(v, 5, ciudad_id=cd["id"])
    alt = altura.potencia_efectiva(v["potencia_hp"], v.get("alimentacion"), v["tipo_combustible"], cd["altitud_msnm"])
    energia = tco.costo_energia_por_km(v, cd["id"])
    return {
        "soat_cop": pec["soat"]["total_cop"], "matricula_cop": pec["matricula"]["total_cop"],
        "total_calle_cop": pec["total_cop"], "cuota_cop": cred["cuota_mensual_con_seguros_cop"],
        "seguro_cop": seg["prima_anual_central_cop"], "tco5_cop": t["costo_total_neto_cop"],
        "potencia_ciudad_hp": alt["potencia_efectiva_hp"] if alt else None,
        "costo_1000km_cop": energia["costo_1000km_cop"], "num_adas": len(v.get("adas_incluidas") or []),
        "retencion_5_anios": round(v["retencion_5_anios"] * 100, 1) if v.get("retencion_5_anios") is not None else None,
    }


def _ganadores(valores: list[Any], regla: str, vs: list[dict]) -> tuple[list[int], str | None]:
    """Devuelve índices ganadores y un aviso opcional."""
    idx = [i for i, x in enumerate(valores) if x is not None]
    if len(idx) < 2 or regla == "info":
        return [], None
    aviso = None
    if regla == "autonomia":
        ciclos = {vs[i].get("autonomia_ciclo") for i in idx}
        if len(ciclos) > 1:
            return [], "Autonomías de ciclos distintos (" + ", ".join(sorted(c for c in ciclos if c)) + "): no comparables"
        regla = "max"
    if regla == "ncap":
        protos = {(vs[i].get("ncap_organismo"), vs[i].get("ncap_protocolo")) for i in idx}
        if len(protos) > 1:
            aviso = "Protocolos NCAP distintos: la comparación es orientativa"
        regla = "max"
    if regla.startswith("cat:"):
        orden = cfg("rankings")[regla[4:]]
        puntos = {i: orden.index(valores[i]) if valores[i] in orden else -1 for i in idx}
    elif regla == "bool":
        puntos = {i: int(bool(valores[i])) for i in idx}
    else:
        puntos = {i: float(valores[i]) for i in idx}
    mejor = (min if regla == "min" else max)(puntos.values())
    ganadores = [i for i in idx if puntos[i] == mejor]
    if len(ganadores) == len(idx) and len(set(puntos.values())) == 1:
        return ganadores, aviso  # empate total: todos marcados
    return ganadores, aviso


def comparar(vehiculos: list[dict], ciudad_id: str | None = None, perfil: str | None = None,
             referencia_id: int | None = None, trm: float | None = None) -> dict[str, Any]:
    vs = [{**v, **_derivados(v, ciudad_id)} for v in vehiculos]
    categorias = []
    marcador = {v["id"]: {"total": 0, "por_categoria": {}} for v in vs}
    ref_idx = next((i for i, v in enumerate(vs) if v["id"] == referencia_id), None)
    for nombre, filas in definicion_filas():
        salida = []
        for clave, etiqueta, regla, getter, unidad in filas:
            valores = [(getter or _campo(clave))(v) for v in vs]
            gan, aviso = _ganadores(valores, regla, vs)
            delta = None
            if ref_idx is not None and regla not in ("info",) and all(isinstance(x, (int, float)) or x is None for x in valores) \
                    and not any(isinstance(x, bool) for x in valores) and valores[ref_idx] is not None:
                delta = [None if x is None else round(x - valores[ref_idx], 2) for x in valores]
            for i in gan:
                m = marcador[vs[i]["id"]]
                m["total"] += 1
                m["por_categoria"][nombre] = m["por_categoria"].get(nombre, 0) + 1
            salida.append({"clave": clave, "etiqueta": etiqueta, "regla": regla, "unidad": unidad, "valores": valores,
                           "ganadores": [vs[i]["id"] for i in gan], "aviso": aviso, "delta": delta,
                           "diferente": len({str(x) for x in valores}) > 1})
        categorias.append({"categoria": nombre, "filas": salida})
    puntajes = puntaje.puntaje_miproximocarro([{**v, "precio_total_en_calle_cop": v["total_calle_cop"]} for v in vs], perfil)
    curvas = [{"id": v["id"], **reventa.curva_reventa(v["precio_base_cop"], v.get("retencion_valor"), v.get("depreciacion_estimada"), trm)} for v in vs]
    return {
        "vehiculos": [{k: v.get(k) for k in ("id", "slug", "marca", "modelo", "anio", "version", "carroceria", "segmento",
                                            "tipo_combustible", "imagen_id", "tiene_alerta_roja", "puntaje_fiabilidad",
                                            "largo_mm", "alto_mm", "ancho_sin_espejos_mm", "ancho_con_espejos_mm",
                                            "distancia_entre_ejes_mm", "distancia_libre_suelo_mm", "voladizo_delantero_mm",
                                            "voladizo_trasero_mm", "diametro_rueda_mm", "indice_garaje_etiqueta",
                                            "indice_rompemuelle_etiqueta", "indice_garaje_nivel", "indice_rompemuelle_nivel",
                                            "precio_base_cop", "precio_base_usd")} for v in vs],
        "categorias": categorias, "marcador": marcador, "puntajes": puntajes, "reventa": curvas,
        "ciudad": ciudad(ciudad_id)["nombre"], "perfil": puntajes[0]["perfil"] if puntajes else None,
    }
