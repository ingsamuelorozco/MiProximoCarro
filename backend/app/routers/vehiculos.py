"""Búsqueda, ficha por secciones y rivales."""
from __future__ import annotations

import math
import re
import sqlite3
import unicodedata
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query

from ..db import conexion, consultar, fiabilidad_por_id, fuentes_por_id, todos_los_vehiculos, vehiculo_completo, vehiculos_por_id
from ..errores import invalido, no_encontrado
from ..services import altura, financiero, indices, reventa, seguro, tco
from ..services.config import ciudad, ELECTRIFICADOS
from ..services.puntaje import etiqueta_fiabilidad

router = APIRouter(prefix="/api/vehiculos", tags=["Vehículos"])

ORDENES = {
    "precio_calle": ("precio_total_en_calle_cop", False), "precio_calle_desc": ("precio_total_en_calle_cop", True),
    "potencia": ("potencia_hp", True), "consumo": ("consumo_real_estimado_kml", True),
    "fiabilidad": ("puntaje_fiabilidad", True), "despeje": ("distancia_libre_suelo_mm", True),
    "recientes": ("anio", True), "puntaje": ("puntaje_miproximocarro_base", True),
}
CAMPOS_TARJETA = ("id", "slug", "marca", "modelo", "anio", "version", "segmento", "carroceria", "tipo_combustible",
                  "precio_base_cop", "precio_base_usd", "precio_total_en_calle_cop", "potencia_hp", "torque_nm",
                  "consumo_real_estimado_kml", "consumo_kwh_100km", "autonomia_estimada_km", "distancia_libre_suelo_mm",
                  "capacidad_baul_litros", "plazas", "transmision_tipo", "traccion", "puntaje_fiabilidad",
                  "tiene_alerta_roja", "imagen_id", "estado_comercial", "numero_airbags", "largo_mm", "alto_mm",
                  "distancia_entre_ejes_mm", "voladizo_delantero_mm", "voladizo_trasero_mm", "diametro_rueda_mm",
                  "indice_garaje_etiqueta", "indice_rompemuelle_etiqueta", "puntaje_miproximocarro_base", "pais_origen", "fecha_precio")


def tarjeta(v: dict) -> dict:
    return {k: v.get(k) for k in CAMPOS_TARJETA}


def _fts_query(q: str) -> str:
    t = unicodedata.normalize("NFKD", q).encode("ascii", "ignore").decode()
    tokens = [x for x in re.split(r"[^A-Za-z0-9]+", t) if x]
    return " ".join(f'"{x}"*' for x in tokens)


def buscar_ids_texto(q: str) -> list[int] | None:
    consulta = _fts_query(q)
    if not consulta:
        return None
    with conexion() as con:
        try:
            ids = [r[0] for r in con.execute("SELECT rowid FROM vehiculos_fts WHERE vehiculos_fts MATCH ? ORDER BY rank", (consulta,))]
        except sqlite3.OperationalError:
            ids = []
    if not ids:  # tolerancia a errores leves: prefijo de 3 letras por token
        tokens = consulta.replace('"', "").replace("*", "").split()
        corta = " ".join(f'"{x[:3]}"*' for x in tokens if len(x) >= 3)
        if corta:
            with conexion() as con:
                ids = [r[0] for r in con.execute("SELECT rowid FROM vehiculos_fts WHERE vehiculos_fts MATCH ? ORDER BY rank", (corta,))]
    return ids


class Filtros:
    """Filtros de búsqueda compartidos por la lista de versiones y la de modelos agrupados."""

    def __init__(
        self,
        q: str | None = Query(None, max_length=80, examples=["captiva"]),
        marca: list[str] = Query([]), modelo: list[str] = Query([], description="Nombre exacto del modelo, p. ej., «2 Sedán»"),
        segmento: list[str] = Query([]), carroceria: list[str] = Query([]),
        combustible: list[str] = Query([]), transmision: list[str] = Query([]), traccion: list[str] = Query([]),
        pais: list[str] = Query([]),
        precio_min: float | None = Query(None, ge=0), precio_max: float | None = Query(None, ge=0),
        anio_min: int | None = Query(None, ge=2000), anio_max: int | None = Query(None, le=2026),
        plazas: int | None = Query(None, ge=2, le=9), adas: list[str] = Query([]),
        despeje_min: int | None = Query(None, ge=100), baul_min: int | None = Query(None, ge=0),
        consumo_min: float | None = Query(None, ge=0), fiabilidad_min: float | None = Query(None, ge=1, le=10),
        estado: list[str] = Query([]), actualizado: bool | None = None, electrificado: bool | None = None,
        ids: list[int] = Query([], description="Restringe a estos ids (p. ej., favoritos)"),
        sort: str = Query("puntaje"),
    ) -> None:
        if sort not in ORDENES:
            raise invalido("Orden no válido", {"permitidos": list(ORDENES)})
        self.__dict__.update({k: v for k, v in locals().items() if k != "self"})

    def aplicar(self) -> list[dict]:
        """Versiones que cumplen los filtros, ya ordenadas."""
        vs = list(todos_los_vehiculos())
        if self.ids:
            permitidos = set(self.ids)
            vs = [v for v in vs if v["id"] in permitidos]
        if self.q:
            encontrados = buscar_ids_texto(self.q)
            if encontrados is not None:
                orden = {i: n for n, i in enumerate(encontrados)}
                vs = [v for v in vs if v["id"] in orden]
        actualizados_ids: set[int] = set()
        if self.actualizado is not None:
            for a in consultar("SELECT vehiculo_ids FROM actualizaciones"):
                actualizados_ids |= set(a["vehiculo_ids"])

        def en(lista: list[str], valor: Any) -> bool:
            return not lista or str(valor).lower() in {x.lower() for x in lista}

        def ok(v: dict) -> bool:
            return all([
                en(self.marca, v["marca"]), en(self.modelo, v["modelo"]), en(self.segmento, v["segmento"]),
                en(self.carroceria, v["carroceria"]), en(self.combustible, v["tipo_combustible"]),
                en(self.traccion, v["traccion"]), en(self.pais, v["pais_origen"]),
                not self.transmision or any(x.lower() in v["transmision_tipo"].lower() for x in self.transmision),
                en(self.estado, v["estado_comercial"]),
                self.precio_min is None or v["precio_base_cop"] >= self.precio_min,
                self.precio_max is None or v["precio_base_cop"] <= self.precio_max,
                self.anio_min is None or v["anio"] >= self.anio_min, self.anio_max is None or v["anio"] <= self.anio_max,
                self.plazas is None or v["plazas"] >= self.plazas,
                not self.adas or all(a in (v["adas_incluidas"] or []) for a in self.adas),
                self.despeje_min is None or v["distancia_libre_suelo_mm"] >= self.despeje_min,
                self.baul_min is None or v["capacidad_baul_litros"] >= self.baul_min,
                self.consumo_min is None or (v["consumo_real_estimado_kml"] or 0) >= self.consumo_min,
                self.fiabilidad_min is None or v["puntaje_fiabilidad"] >= self.fiabilidad_min,
                self.actualizado is None or ((v["id"] in actualizados_ids) == self.actualizado),
                self.electrificado is None or ((v["tipo_combustible"] in ELECTRIFICADOS) == self.electrificado),
            ])

        vs = [v for v in vs if ok(v)]
        if not (self.q and self.sort == "puntaje"):
            campo, desc = ORDENES[self.sort]
            vs.sort(key=lambda v: (v.get(campo) is None, -(v.get(campo) or 0) if desc else (v.get(campo) or 0)))
        return vs

    def sugerencia(self) -> str:
        activos = {k: x for k, x in {"precio_max": self.precio_max, "despeje_min": self.despeje_min, "baul_min": self.baul_min,
                                     "fiabilidad_min": self.fiabilidad_min, "adas": self.adas, "plazas": self.plazas}.items() if x}
        return ("Prueba relajar: " + ", ".join(activos)) if activos else "Prueba otra búsqueda o quita filtros."


def _pagina(lista: list, page: int, size: int) -> tuple[list, int]:
    return lista[(page - 1) * size: page * size], (math.ceil(len(lista) / size) if lista else 0)


@router.get("", summary="Búsqueda con filtros, orden y paginación")
def buscar(f: Filtros = Depends(), page: int = Query(1, ge=1), size: int = Query(24, ge=1, le=100)) -> dict[str, Any]:
    vs = f.aplicar()
    pagina, paginas = _pagina(vs, page, size)
    return {"total": len(vs), "page": page, "size": size, "paginas": paginas,
            "resultados": [tarjeta(v) for v in pagina], "sugerencia": None if vs else f.sugerencia()}


@router.get("/modelos", summary="Búsqueda agrupada por modelo (una tarjeta por marca y modelo)")
def buscar_modelos(f: Filtros = Depends(), page: int = Query(1, ge=1), size: int = Query(24, ge=1, le=100)) -> dict[str, Any]:
    """Agrupa las versiones que cumplen los filtros por marca y modelo.

    «2 Sedán» y «2 Hatchback» son modelos distintos; sus versiones (Touring, Grand Touring…) y años van dentro.
    El orden de los modelos sigue al de su mejor versión según el orden pedido.
    """
    grupos: dict[tuple[str, str], list[dict]] = {}
    for v in f.aplicar():
        grupos.setdefault((v["marca"], v["modelo"]), []).append(v)
    modelos = []
    for (marca, modelo), vs in grupos.items():
        calle = [v["precio_total_en_calle_cop"] for v in vs if v["precio_total_en_calle_cop"]]
        anios = sorted({v["anio"] for v in vs}, reverse=True)
        recientes = [v for v in vs if v["anio"] == anios[0]]
        modelos.append({
            "marca": marca, "modelo": modelo, "carroceria": vs[0]["carroceria"], "segmento": vs[0]["segmento"],
            "anios": anios, "versiones": len(vs),
            "combustibles": sorted({v["tipo_combustible"] for v in vs}),
            "precio_calle_min": min(calle) if calle else None, "precio_calle_max": max(calle) if calle else None,
            "puntaje_fiabilidad": max(v["puntaje_fiabilidad"] for v in recientes),
            "tiene_alerta_roja": any(v["tiene_alerta_roja"] for v in vs),
            "representante": tarjeta(vs[0]),
        })
    pagina, paginas = _pagina(modelos, page, size)
    return {"total": len(modelos), "total_versiones": sum(m["versiones"] for m in modelos), "page": page, "size": size,
            "paginas": paginas, "resultados": pagina, "sugerencia": None if modelos else f.sugerencia()}


def _rivales(v: dict, n: int = 6) -> list[dict]:
    cand = [o for o in todos_los_vehiculos() if o["segmento"] == v["segmento"]
            and (o["marca"], o["modelo"]) != (v["marca"], v["modelo"]) and o["estado_comercial"] == "Vigente"]
    cand.sort(key=lambda o: abs(o["precio_base_cop"] - v["precio_base_cop"]))
    vistos, out = set(), []
    for o in cand:
        if (o["marca"], o["modelo"]) in vistos:
            continue
        vistos.add((o["marca"], o["modelo"]))
        out.append(tarjeta(o))
        if len(out) == n:
            break
    return out


def _recalls(v: dict) -> list[dict]:
    out = []
    for r in consultar("SELECT * FROM recalls"):
        if v["marca"] not in r["marcas"] or not (r["anio_desde"] <= v["anio"] <= r["anio_hasta"]):
            continue
        if r["modelos"] and v["modelo"] not in r["modelos"]:
            continue
        r["fuentes"] = [fuentes_por_id().get(f) for f in r["fuentes_ids"]]
        out.append(r)
    return out


def _resolver(id_o_slug: str) -> dict:
    if id_o_slug.isdigit():
        v = vehiculos_por_id().get(int(id_o_slug))
    else:
        v = next((x for x in todos_los_vehiculos() if x["slug"] == id_o_slug), None)
    if not v:
        raise no_encontrado("Vehículo", id_o_slug)
    return v


@router.get("/{id_o_slug}", summary="Ficha completa agrupada por secciones")
def ficha(id_o_slug: str, ciudad_id: str | None = Query(None, alias="ciudad"), trm: float | None = Query(None, gt=1000, lt=10000),
          km_anio: float | None = Query(None, gt=0)) -> dict[str, Any]:
    base = _resolver(id_o_slug)
    try:
        cd = ciudad(ciudad_id)
    except KeyError:
        raise invalido("Ciudad no válida", {"ciudad": ciudad_id}) from None
    v = vehiculo_completo(base["id"])
    f = fiabilidad_por_id()[v["id"]]
    g = lambda *ks: {k: v.get(k) for k in ks}  # noqa: E731
    pec = financiero.puesta_en_calle(v["precio_base_cop"], v.get("cilindraje_cc"), v["carroceria"], v["tipo_combustible"], cd["id"],
                                     antiguedad_anios=financiero.antiguedad_compra(v["anio"], v.get("fecha_precio")))
    seg = seguro.todo_riesgo(financiero.avaluo_estimado(v["precio_base_cop"]), v["segmento"], cd["id"],
                             riesgo_hurto=v["riesgo_hurto"], tipo_combustible=v["tipo_combustible"])
    cred = financiero.credito(pec["total_cop"] - pec["soat"]["total_cop"] - pec["matricula"]["total_cop"], incluir_tabla=False)
    hermanos = [tarjeta(o) for o in todos_los_vehiculos() if o["marca"] == v["marca"] and o["modelo"] == v["modelo"] and o["id"] != v["id"]]
    actualizaciones = [a for a in consultar("SELECT id, titulo, tipo, anio_modelo, fecha_lanzamiento_colombia, vale_la_pena FROM actualizaciones WHERE marca = ? AND modelo = ? ORDER BY fecha_lanzamiento_colombia DESC", (v["marca"], v["modelo"]))]
    graves = [x for x in f["fallas_comunes_y_contras"] if x["severidad"] in ("Crítica", "Alta")][:3] or f["fallas_comunes_y_contras"][:3]
    return {
        "id": v["id"], "slug": v["slug"], "marca": v["marca"], "modelo": v["modelo"], "anio": v["anio"], "version": v["version"],
        "nombre": f"{v['marca']} {v['modelo']} {v['anio']} {v['version']}",
        "cabecera": g("segmento", "carroceria", "tipo_combustible", "estado_comercial", "imagen_id", "tiene_alerta_roja",
                      "precio_base_cop", "precio_base_usd", "fecha_precio", "trm_referencia", "pais_origen", "generacion",
                      "puertas", "plazas", "fecha_lanzamiento_colombia", "puntaje_miproximocarro_base"),
        "alertas": f["alertas"],
        "calidad_dato": {**g("campos_estimados", "confianza_dato", "ultima_verificacion"),
                         "fuentes": [fuentes_por_id().get(x) for x in v["fuentes_ids"] + [v["fuente_precio_id"]]]},
        "especificaciones": {
            "motor": g("motor_descripcion", "tipo_combustible", "cilindraje_cc", "cilindros", "valvulas", "alimentacion",
                       "potencia_hp", "rpm_potencia_max", "torque_nm", "rpm_torque_max", "relacion_peso_potencia",
                       "aceleracion_0_100_seg", "velocidad_maxima_kmh", "octanaje_minimo_recomendado", "emisiones_co2_g_km",
                       "potencia_electrica_kw", "capacidad_bateria_kwh", "potencia_carga_ac_kw", "potencia_carga_dc_kw"),
            "altura": altura.tabla_ciudades(v["potencia_hp"], v.get("alimentacion"), v["tipo_combustible"], cd["id"]),
            "chasis": g("transmision_tipo", "numero_velocidades", "traccion", "suspension_delantera", "suspension_trasera",
                        "frenos_delanteros", "frenos_traseros", "direccion", "radio_giro_metros", "medida_llantas",
                        "diametro_rueda_mm", "profundidad_vadeo_mm", "capacidad_remolque_kg"),
            "seguridad": g("numero_airbags", "ncap_organismo", "ncap_estrellas", "ncap_anio", "ncap_protocolo", "frenos_abs_ebd",
                           "control_estabilidad_esc", "asistente_arranque_pendiente", "anclajes_isofix", "adas_incluidas"),
            "equipamiento": g("pantalla_multimedia_pulgadas", "apple_carplay_android_auto", "aire_acondicionado", "tapiceria",
                              "techo_corredizo", "camara_reversa", "carga_inalambrica", "llave_inteligente",
                              "sensores_parqueo", "luces_led"),
        },
        "tamano": {
            "medidas": g("largo_mm", "ancho_sin_espejos_mm", "ancho_con_espejos_mm", "alto_mm", "distancia_entre_ejes_mm",
                         "voladizo_delantero_mm", "voladizo_trasero_mm", "distancia_libre_suelo_mm", "peso_vacio_kg",
                         "capacidad_carga_kg", "capacidad_baul_litros", "capacidad_baul_abatido_litros",
                         "angulo_ataque_deg", "angulo_ventral_deg", "angulo_salida_deg", "diametro_rueda_mm", "carroceria"),
            "rompemuelle": indices.rompemuelle(v["distancia_libre_suelo_mm"], v["voladizo_delantero_mm"], v.get("angulo_ventral_deg")),
            "garaje": indices.garaje(v["largo_mm"], v["ancho_con_espejos_mm"], v["ancho_sin_espejos_mm"]),
            "baul_objetos": indices.baul_objetos(v["capacidad_baul_litros"]),
            "comodidad_trasera": indices.comodidad_trasera(v["distancia_entre_ejes_mm"], v["ancho_sin_espejos_mm"]),
            "radio_giro_metros": v["radio_giro_metros"],
        },
        "precio": {
            "puesta_en_calle": pec, "seguro": seg, "credito": cred,
            "soat_anual_cop": pec["soat"]["total_cop"],
            "reventa": reventa.curva_reventa(v["precio_base_cop"], f["retencion_valor"], f["depreciacion_estimada"], trm),
        },
        "costo": {
            "consumo": g("consumo_ciudad_kml", "consumo_carretera_kml", "consumo_mixto_kml", "consumo_real_estimado_kml",
                         "consumo_kwh_100km", "ciclo_homologacion", "capacidad_tanque_galones", "autonomia_estimada_km", "autonomia_ciclo"),
            "energia": tco.costo_energia_por_km(v, cd["id"]),
            "mantenimiento": {k: f[k] for k in ("nivel_costo_mantenimiento", "costo_mantenimiento_anual_cop", "costo_primeros_60000km_cop", "disponibilidad_repuestos")},
            "tco5": tco.tco(v, 5, km_anio=km_anio, ciudad_id=cd["id"]),
            "pico_y_placa": tco.pico_y_placa(v["tipo_combustible"], cd["id"]),
        },
        "fiabilidad": {"puntaje": f["puntaje_fiabilidad"], "etiqueta": etiqueta_fiabilidad(f["puntaje_fiabilidad"]),
                       "veredicto": f["veredicto_honesto"], "fallas_graves": graves, "recalls": _recalls(v)},
        "versiones": hermanos, "actualizaciones": actualizaciones, "rivales": _rivales(v),
        "ciudad": {"id": cd["id"], "nombre": cd["nombre"], "altitud_msnm": cd["altitud_msnm"]},
    }


@router.get("/{id_o_slug}/rivales", summary="Alternativas por segmento y precio")
def rivales(id_o_slug: str, n: int = Query(6, ge=1, le=20)) -> list[dict]:
    return _rivales(_resolver(id_o_slug), n)


def ordenar(campo: str, lista: list[dict], desc: bool = True) -> list[dict]:
    return sorted(lista, key=lambda v: (v.get(campo) is None, -(v.get(campo) or 0) if desc else (v.get(campo) or 0)))


Sort = Literal["precio_calle", "precio_calle_desc", "potencia", "consumo", "fiabilidad", "despeje", "recientes", "puntaje"]
