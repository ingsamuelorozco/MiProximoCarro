"""Siembra db/cars.db a partir de los YAML de data/ (fuente de verdad editable).

Uso: python scripts/seed.py [--db ruta]

- Valida cada versión con Pydantic (backend/app/schemas.py).
- Calcula derivados (peso/potencia, diámetro de rueda, puesta en calle, índices, fiabilidad).
- Recrea la base de forma idempotente (escribe en un temporal y reemplaza), crea índices y FTS5.
- Imprime un reporte de conteos y completitud.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import typing
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from backend.app.schemas import FiabilidadRegistro, VehiculoRegistro  # noqa: E402
from backend.app.services import financiero, indices, puntaje, reventa, tco  # noqa: E402
from backend.app.services.config import BEV, HEV, MHEV, PHEV, cfg  # noqa: E402

DATA = RAIZ / "data"
DB_DEFECTO = RAIZ / "db" / "cars.db"
SEVERIDAD_ORDEN = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}

# Campos de datos (los que pueden ser verificados o estimados).
CAMPOS_DATO = [
    "cilindraje_cc", "cilindros", "valvulas", "potencia_hp", "rpm_potencia_max", "torque_nm", "rpm_torque_max",
    "aceleracion_0_100_seg", "velocidad_maxima_kmh", "octanaje_minimo_recomendado", "emisiones_co2_g_km",
    "potencia_electrica_kw", "capacidad_bateria_kwh", "potencia_carga_ac_kw", "potencia_carga_dc_kw",
    "transmision_tipo", "numero_velocidades", "traccion", "suspension_delantera", "suspension_trasera",
    "frenos_delanteros", "frenos_traseros", "radio_giro_metros", "medida_llantas", "profundidad_vadeo_mm",
    "capacidad_remolque_kg", "largo_mm", "ancho_sin_espejos_mm", "ancho_con_espejos_mm", "alto_mm",
    "distancia_entre_ejes_mm", "distancia_libre_suelo_mm", "peso_vacio_kg", "capacidad_carga_kg",
    "capacidad_baul_litros", "capacidad_baul_abatido_litros", "voladizo_delantero_mm", "voladizo_trasero_mm",
    "angulo_ataque_deg", "angulo_ventral_deg", "angulo_salida_deg", "capacidad_tanque_galones",
    "autonomia_estimada_km", "consumo_ciudad_kml", "consumo_carretera_kml", "consumo_mixto_kml",
    "consumo_real_estimado_kml", "consumo_kwh_100km", "numero_airbags", "ncap_estrellas",
    "pantalla_multimedia_pulgadas", "garantia_anos", "garantia_km", "precio_base_cop", "avaluo_fasecolda_cop",
]
GRUPOS = ("motor", "chasis", "dim", "consumo", "ev", "seg", "equipo", "garantia")
CLAVES_MODELO = ("generacion", "segmento", "carroceria", "pais_origen", "estado_comercial",
                 "fecha_lanzamiento_colombia", "plazas", "puertas", "imagen_id", "confianza_dato")


def cargar(nombre: str) -> Any:
    with (DATA / nombre).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def slugify(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def aplanar(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if k in GRUPOS and isinstance(v, dict):
            out.update(v)
        else:
            out[k] = v
    return out


def a_fecha(v: Any) -> date | None:
    if v is None or isinstance(v, date):
        return v
    return date.fromisoformat(str(v))


class Sembrador:
    def __init__(self) -> None:
        self.defaults = cargar("defaults.yaml")
        self.fuentes = {f["id"]: f for f in cargar("fuentes.yaml")["fuentes"]}
        self.patrones = cargar("fallas_patrones.yaml")["patrones"]
        self.recalls = cargar("recalls.yaml")["recalls"]
        self.actualizaciones = cargar("actualizaciones.yaml")["actualizaciones"]
        self.imagenes = cargar("imagenes.yaml")["imagenes"]
        self.trm = cfg("trm")["respaldo_cop_por_usd"]
        self.vehiculos: list[dict[str, Any]] = []
        self.fiabilidad: list[dict[str, Any]] = []
        self.errores: list[str] = []
        self.estimados_por_regla: Counter[str] = Counter()

    # ------------------------------------------------------------ construcción
    def construir(self) -> None:
        archivos = sorted((DATA / "vehiculos").glob("*.yaml"))
        vid = 0
        for archivo in archivos:
            marca_doc = yaml.safe_load(archivo.read_text(encoding="utf-8"))
            for modelo in marca_doc["modelos"]:
                for version in modelo["versiones"]:
                    vid += 1
                    try:
                        reg, fia = self._registro(vid, marca_doc, modelo, version)
                        self.vehiculos.append(reg)
                        self.fiabilidad.append(fia)
                    except Exception as e:  # noqa: BLE001
                        self.errores.append(f"{archivo.name} · {modelo.get('modelo')} {version.get('anio')} {version.get('version')}: {e}")
        self._posprocesar()

    def _registro(self, vid: int, marca_doc: dict, modelo: dict, version: dict) -> tuple[dict, dict]:
        dfl = self.defaults
        r: dict[str, Any] = dict(dfl["valores_defecto"])
        r["adas_incluidas"] = list(r["adas_incluidas"])
        r["pais_origen"] = marca_doc.get("pais_origen")
        for k in CLAVES_MODELO:
            if k in modelo:
                r[k] = modelo[k]
        r.update(aplanar({k: v for k, v in modelo.items() if k in GRUPOS}))
        r.update(aplanar(version))
        r.setdefault("puertas", dfl["puertas_por_carroceria"][r["carroceria"]])
        r.setdefault("plazas", dfl["plazas_por_carroceria"][r["carroceria"]])
        r.setdefault("confianza_dato", dfl["confianza_por_defecto"])
        verificados = set(modelo.get("campos_verificados", [])) | set(version.get("campos_verificados", []))
        r.pop("campos_verificados", None)
        r["marca"] = marca_doc["marca"]
        r["modelo"] = str(modelo["modelo"])
        r["id"] = vid
        r["slug"] = slugify(f"{r['marca']}-{r['modelo']}-{r['anio']}-{r['version']}")
        r["fecha_precio"] = a_fecha(r.get("fecha_precio"))
        r["fecha_lanzamiento_colombia"] = a_fecha(r.get("fecha_lanzamiento_colombia"))
        tipo = r["tipo_combustible"]
        reglas = dfl["reglas_estimacion"]
        derivados: set[str] = set()

        def poner(campo: str, valor: Any) -> None:
            if r.get(campo) is None and valor is not None:
                r[campo] = valor
                derivados.add(campo)
                self.estimados_por_regla[campo] += 1

        if tipo == BEV:
            r.setdefault("alimentacion", "Eléctrico")
        poner("ancho_con_espejos_mm", (r.get("ancho_sin_espejos_mm") or 0) + reglas["espejos_extra_mm"])
        resto = r["largo_mm"] - r["distancia_entre_ejes_mm"]
        poner("voladizo_delantero_mm", round(resto * reglas["voladizo_delantero_fraccion"]))
        poner("voladizo_trasero_mm", r["largo_mm"] - r["distancia_entre_ejes_mm"] - r["voladizo_delantero_mm"])
        poner("capacidad_carga_kg", round(r["peso_vacio_kg"] * reglas["carga_util_fraccion_peso"]))
        if r["carroceria"] in ("Hatchback", "SUV"):
            poner("capacidad_baul_abatido_litros", round(r["capacidad_baul_litros"] * reglas["factor_baul_abatido"]))
        mixto = r.get("consumo_mixto_kml")
        if mixto:
            hib = tipo in (HEV, PHEV)
            poner("consumo_ciudad_kml", round(mixto * (reglas["factor_hibrido_ciudad"] if hib else reglas["factor_consumo_ciudad"]), 1))
            poner("consumo_carretera_kml", round(mixto * (reglas["factor_hibrido_carretera"] if hib else reglas["factor_consumo_carretera"]), 1))
            poner("consumo_real_estimado_kml", round(mixto * reglas["factor_consumo_real"], 1))
            if r.get("capacidad_tanque_galones") and r.get("autonomia_estimada_km") is None:
                poner("autonomia_estimada_km", round(r["capacidad_tanque_galones"] * cfg("combustibles")["litros_por_galon"] * mixto))
                r["autonomia_ciclo"] = "Estimada"
            g_l = reglas["co2_g_por_litro_diesel"] if tipo == "Diésel" else reglas["co2_g_por_litro_gasolina"]
            poner("emisiones_co2_g_km", round(g_l / mixto))
        if tipo == BEV:
            r.setdefault("emisiones_co2_g_km", 0)
        r.setdefault("autonomia_ciclo", "Estimada")
        r.setdefault("ciclo_homologacion", "Estimado")
        r["diametro_rueda_mm"] = indices.diametro_rueda_mm(r.get("medida_llantas"))
        r["relacion_peso_potencia"] = round(r["peso_vacio_kg"] / r["potencia_hp"], 2)
        # Precio y puesta en calle (Bogotá como ciudad de referencia, mes de la fecha del precio).
        r["fuente_precio_id"] = r.get("fuente_precio_id", "editorial-precio")
        r["trm_referencia"] = self.trm
        r["precio_base_usd"] = round(r["precio_base_cop"] / self.trm)
        r["avaluo_fasecolda_cop"] = financiero.avaluo_estimado(r["precio_base_cop"])
        derivados.add("avaluo_fasecolda_cop")
        ciudad_ref = cfg("ciudades")["ciudad_defecto"]
        edad = financiero.antiguedad_compra(r["anio"], r["fecha_precio"])
        r["costo_soat_cop"] = financiero.soat(r.get("cilindraje_cc"), r["carroceria"], tipo, edad)["total_cop"]
        r["costo_matricula_estimado_cop"] = financiero.matricula(r["precio_base_cop"], tipo, ciudad_ref, r["fecha_precio"].month,
                                                                  False if edad else None)["total_cop"]
        r["precio_total_en_calle_cop"] = r["precio_base_cop"] + r["costo_soat_cop"] + r["costo_matricula_estimado_cop"]
        # Índices dimensionales.
        rm = indices.rompemuelle(r["distancia_libre_suelo_mm"], r.get("voladizo_delantero_mm"), r.get("angulo_ventral_deg"))
        gj = indices.garaje(r["largo_mm"], r["ancho_con_espejos_mm"], r["ancho_sin_espejos_mm"])
        r["indice_rompemuelle_nivel"], r["indice_rompemuelle_etiqueta"] = rm["nivel"], rm["etiqueta"]
        r["indice_garaje_nivel"], r["indice_garaje_etiqueta"] = gj["nivel"], gj["etiqueta"]
        # Fuentes del registro.
        fuentes = list(dict.fromkeys(marca_doc.get("fuentes_ids", []) + modelo.get("fuentes_ids", []) + version.get("fuentes_ids", [])))
        if r.get("ncap_organismo") == "Latin NCAP":
            fuentes.append("latin-ncap")
        elif r.get("ncap_organismo") == "Euro NCAP":
            fuentes.append("euro-ncap")
        r["fuentes_ids"] = fuentes
        r["ultima_verificacion"] = a_fecha(version.get("ultima_verificacion") or modelo.get("ultima_verificacion") or "2026-11-13")
        # Fiabilidad.
        fia = self._fiabilidad(vid, r, modelo, version)
        r["puntaje_fiabilidad"] = fia["puntaje_fiabilidad"]
        r["tiene_alerta_roja"] = any(a["nivel"] == "ROJA" for a in fia["alertas"])
        r["riesgo_hurto"] = modelo["resena"].get("riesgo_hurto", "Medio")
        r["nivel_costo_mantenimiento"] = fia["nivel_costo_mantenimiento"]
        r["depreciacion_estimada"] = fia["depreciacion_estimada"]
        r["retencion_5_anios"] = fia["retencion_valor"]["5"]
        # Campos estimados: todo dato presente que no esté en campos_verificados, más los derivados por regla.
        r["campos_estimados"] = sorted({c for c in CAMPOS_DATO if r.get(c) is not None and c not in verificados} | (derivados - verificados))
        r["puntaje_miproximocarro_base"] = None
        for k in list(r):
            if k not in VehiculoRegistro.model_fields:
                raise ValueError(f"campo desconocido: {k}")
        VehiculoRegistro.model_validate(r)
        return r, fia

    def _fiabilidad(self, vid: int, r: dict, modelo: dict, version: dict) -> dict:
        rs = modelo["resena"]
        base = [] if version.get("patrones_excluir") else list(rs.get("patrones", []))
        patrones_ids = list(dict.fromkeys(base + list(version.get("patrones", []))))
        r.pop("patrones", None)
        r.pop("patrones_excluir", None)
        fallas: list[dict] = []
        alertas: list[dict] = list(rs.get("alertas", []))
        fuentes: list[str] = []
        for pid in patrones_ids:
            p = self.patrones[pid]
            for f in p["fallas"]:
                fallas.append({**{k: v for k, v in f.items() if k != "fuentes_ids"}, "fuente_id": f["fuentes_ids"][0], "fuentes_ids": f["fuentes_ids"]})
                fuentes += f["fuentes_ids"]
            if p.get("alerta") and p["alerta"]["texto"] not in [a["texto"] for a in alertas]:
                alertas.append(p["alerta"])
        for c in rs.get("contras", []):
            fallas.append({**c, "tipo": "editorial", "fuente_id": "editorial-mantenimiento", "fuentes_ids": ["editorial-mantenimiento"]})
        fuentes.append("editorial-mantenimiento")
        fallas.sort(key=lambda f: SEVERIDAD_ORDEN[f["severidad"]])
        nivel = rs["nivel_costo_mantenimiento"]
        tipo = r["tipo_combustible"]
        km_def = cfg("combustibles")["km_anuales_defecto"]
        retencion = reventa.retencion_completa(rs.get("retencion_valor"), rs["depreciacion_estimada"])
        return {
            "vehiculo_id": vid,
            "puntaje_fiabilidad": puntaje.puntaje_fiabilidad(rs["desglose"], alertas),
            "desglose": rs["desglose"],
            "nivel_costo_mantenimiento": nivel,
            "costo_mantenimiento_anual_cop": round(tco.mantenimiento_anual(nivel, km_def, tipo), -3),
            "costo_primeros_60000km_cop": round(tco.costo_mantenimiento_km(nivel, 60000, tipo), -3),
            "disponibilidad_repuestos": rs["disponibilidad_repuestos"],
            "depreciacion_estimada": rs["depreciacion_estimada"],
            "retencion_valor": {k: retencion[k] for k in ("1", "3", "5", "7")},
            "veredicto_honesto": " ".join(rs["veredicto"].split()),
            "para_quien_si": rs["para_quien_si"],
            "para_quien_no": rs["para_quien_no"],
            "pros_reales": rs["pros_reales"],
            "fallas_comunes_y_contras": fallas,
            "alertas": alertas,
            "alternativas_recomendadas": [],
            "fuentes_ids": list(dict.fromkeys(fuentes)),
        }

    def _posprocesar(self) -> None:
        if self.errores:
            return
        # Puntaje MiProximoCarro base (perfil por defecto, normalizado sobre todo el catálogo).
        for v, p in zip(self.vehiculos, puntaje.puntaje_miproximocarro(self.vehiculos)):
            v["puntaje_miproximocarro_base"] = p["puntaje"]
        # Alternativas recomendadas: mismo segmento, ±30% de precio, mejor fiabilidad, otro modelo.
        por_id = {v["id"]: v for v in self.vehiculos}
        for f in self.fiabilidad:
            v = por_id[f["vehiculo_id"]]
            def candidatos(misma: str) -> list[dict]:
                return [o for o in self.vehiculos
                        if o[misma] == v[misma] and (o["marca"], o["modelo"]) != (v["marca"], v["modelo"])
                        and abs(o["precio_base_cop"] - v["precio_base_cop"]) <= 0.3 * v["precio_base_cop"]
                        and o["puntaje_fiabilidad"] > v["puntaje_fiabilidad"] and o["estado_comercial"] == "Vigente"]
            c = candidatos("segmento") or candidatos("carroceria")
            c.sort(key=lambda o: (-o["puntaje_fiabilidad"], abs(o["precio_base_cop"] - v["precio_base_cop"])))
            vistos, alt = set(), []
            for o in c:
                if (o["marca"], o["modelo"]) in vistos:
                    continue
                vistos.add((o["marca"], o["modelo"]))
                alt.append(o["id"])
                if len(alt) == 3:
                    break
            f["alternativas_recomendadas"] = alt
            try:
                FiabilidadRegistro.model_validate(f)
            except Exception as e:  # noqa: BLE001
                self.errores.append(f"fiabilidad {v['slug']}: {e}")
        # Referencias de fuentes.
        for v in self.vehiculos:
            for fid in v["fuentes_ids"] + [v["fuente_precio_id"]]:
                if fid not in self.fuentes:
                    self.errores.append(f"{v['slug']}: fuente desconocida {fid}")
        for f in self.fiabilidad:
            for fa in f["fallas_comunes_y_contras"]:
                for fid in fa["fuentes_ids"]:
                    if fid not in self.fuentes:
                        self.errores.append(f"fiabilidad {f['vehiculo_id']}: fuente desconocida {fid}")

    # ------------------------------------------------------------ escritura
    def escribir(self, destino: Path) -> None:
        tmp = destino.with_suffix(".tmp")
        for p in (tmp, Path(str(tmp) + "-wal"), Path(str(tmp) + "-shm")):
            if p.exists():
                p.unlink()
        con = sqlite3.connect(tmp)
        con.execute("PRAGMA journal_mode=WAL")
        con.executescript(ddl())
        cols = list(VehiculoRegistro.model_fields)
        con.executemany(
            f"INSERT INTO vehiculos ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
            [[a_sql(v.get(c)) for c in cols] for v in self.vehiculos],
        )
        fcols = list(FiabilidadRegistro.model_fields)
        con.executemany(
            f"INSERT INTO fiabilidad ({','.join(fcols)}) VALUES ({','.join('?' * len(fcols))})",
            [[a_sql(f.get(c)) for c in fcols] for f in self.fiabilidad],
        )
        con.executemany("INSERT INTO fuentes (id, titulo, url, tipo, fecha_consulta) VALUES (?,?,?,?,?)",
                        [(f["id"], f["titulo"], f["url"], f["tipo"], str(f["fecha_consulta"])) for f in self.fuentes.values()])
        con.executemany(
            "INSERT INTO imagenes (id, url, proveedor, autor, licencia, url_origen, ancho, alto, contiene_logo, uso, verificada_en, descripcion) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [(i["id"], i["url"], i["proveedor"], i["autor"], i["licencia"], i["url_origen"], i["ancho"], i["alto"],
              int(i["contiene_logo"]), i["uso"], str(i["verificada_en"]), i.get("descripcion")) for i in self.imagenes])
        for rc in self.recalls:
            con.execute("INSERT INTO recalls (id, titulo, marcas, modelos, anio_desde, anio_hasta, descripcion, ente, fecha, estado, fuentes_ids) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (rc["id"], rc["titulo"], json.dumps(rc["marcas"], ensure_ascii=False),
                         json.dumps([str(m) for m in rc["modelos"]] if rc.get("modelos") else None, ensure_ascii=False),
                         rc["anios"][0], rc["anios"][1], rc["descripcion"], rc["ente"], str(rc["fecha"]), rc["estado"],
                         json.dumps(rc["fuentes_ids"])))
        por_slug = {v["slug"]: v for v in self.vehiculos}
        for i, a in enumerate(self.actualizaciones, start=1):
            ids = [por_slug[s]["id"] for s in a["vehiculos"]]
            antes = por_slug[a["antes"]] if a.get("antes") else None
            despues = por_slug[a["vehiculos"][0]]
            delta = a.get("delta_precio_cop")
            if delta is None and antes:
                delta = despues["precio_base_cop"] - antes["precio_base_cop"]
            con.execute(
                "INSERT INTO actualizaciones (id, marca, modelo, anio_modelo, vehiculo_ids, vehiculo_anterior_id, tipo, categorias, fecha_lanzamiento_colombia, titulo, resumen, cambios, delta_precio_cop, imagen_antes_id, imagen_despues_id, vale_la_pena, razon_veredicto, fuentes_ids, segmento, estado_dato) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (i, despues["marca"], despues["modelo"], despues["anio"], json.dumps(ids), antes["id"] if antes else None,
                 a["tipo"], json.dumps(a["categorias"], ensure_ascii=False), str(a["fecha_lanzamiento_colombia"]), a["titulo"],
                 a["resumen"], json.dumps(a["cambios"], ensure_ascii=False), delta, a.get("imagen_antes_id"),
                 a.get("imagen_despues_id"), a["vale_la_pena"], a["razon_veredicto"], json.dumps(a["fuentes_ids"]),
                 despues["segmento"], a.get("estado_dato", "estimado")))
        con.executemany("INSERT INTO vehiculos_fts (rowid, marca, modelo, version, segmento, carroceria, tipo_combustible) VALUES (?,?,?,?,?,?,?)",
                        [(v["id"], v["marca"], v["modelo"], v["version"], v["segmento"], v["carroceria"], v["tipo_combustible"]) for v in self.vehiculos])
        con.execute("INSERT INTO meta (clave, valor) VALUES ('generado', ?)", (date.today().isoformat(),))
        con.commit()
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        con.execute("PRAGMA optimize")
        con.close()
        for p in (Path(str(destino) + "-wal"), Path(str(destino) + "-shm")):
            if p.exists():
                p.unlink()
        os.replace(tmp, destino)
        for p in (Path(str(tmp) + "-wal"), Path(str(tmp) + "-shm")):
            if p.exists():
                p.unlink()

    # ------------------------------------------------------------ reporte
    def reporte(self) -> None:
        vs = self.vehiculos
        print(f"Vehículos sembrados: {len(vs)}")
        print(f"Reseñas: {len(self.fiabilidad)} · Actualizaciones: {len(self.actualizaciones)} · Recalls: {len(self.recalls)} · Fuentes: {len(self.fuentes)}")
        for titulo, clave in (("marca", "marca"), ("carrocería", "carroceria"), ("combustible", "tipo_combustible"), ("año", "anio")):
            c = Counter(v[clave] for v in vs)
            print(f"\nPor {titulo}: " + ", ".join(f"{k}={n}" for k, n in sorted(c.items(), key=lambda x: str(x[0]))))
        total_campos = len(CAMPOS_DATO)
        completos = sum(1 for v in vs for c in CAMPOS_DATO if v.get(c) is not None)
        print(f"\nCompletitud de campos de datos: {completos / (len(vs) * total_campos):.1%}")
        est = sum(len(v["campos_estimados"]) for v in vs)
        print(f"Datos marcados como estimados: {est / max(completos, 1):.1%} de los valores presentes")
        if self.estimados_por_regla:
            print("Rellenados por regla de estimación: " + ", ".join(f"{k}={n}" for k, n in self.estimados_por_regla.most_common()))


def a_sql(v: Any) -> Any:
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, date):
        return v.isoformat()
    return v


def tipo_sql(anotacion: Any) -> str:
    base = typing.get_args(anotacion)[0] if typing.get_origin(anotacion) is typing.Union else anotacion
    if base is bool or base is int:
        return "INTEGER"
    if base is float:
        return "REAL"
    return "TEXT"


def ddl() -> str:
    cols = []
    for nombre, campo in VehiculoRegistro.model_fields.items():
        if nombre == "id":
            cols.append("id INTEGER PRIMARY KEY")
        else:
            nulo = "" if campo.is_required() else ""
            cols.append(f"{nombre} {tipo_sql(campo.annotation)}{nulo}")
    checks = [
        "UNIQUE (marca, modelo, anio, version)",
        "UNIQUE (slug)",
        "CHECK (distancia_libre_suelo_mm BETWEEN 100 AND 300)",
        "CHECK (anio BETWEEN 2000 AND 2026)",
        "CHECK (puntaje_fiabilidad BETWEEN 1 AND 10)",
        "CHECK (precio_total_en_calle_cop = precio_base_cop + costo_soat_cop + costo_matricula_estimado_cop)",
        "CHECK (ancho_con_espejos_mm > ancho_sin_espejos_mm)",
    ]
    return f"""
CREATE TABLE meta (clave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE fuentes (id TEXT PRIMARY KEY, titulo TEXT NOT NULL, url TEXT NOT NULL, tipo TEXT NOT NULL, fecha_consulta TEXT);
CREATE TABLE imagenes (id TEXT PRIMARY KEY, url TEXT NOT NULL, proveedor TEXT NOT NULL CHECK (proveedor IN ('Unsplash','Pexels','Wikimedia Commons')),
  autor TEXT NOT NULL, licencia TEXT NOT NULL, url_origen TEXT NOT NULL, ancho INTEGER, alto INTEGER, contiene_logo INTEGER NOT NULL,
  uso TEXT NOT NULL CHECK (uso IN ('hero','catalogo')), verificada_en TEXT, descripcion TEXT);
CREATE TABLE vehiculos (
  {(','+chr(10)+'  ').join(cols + checks)}
);
CREATE INDEX ix_veh_segmento ON vehiculos(segmento);
CREATE INDEX ix_veh_carroceria ON vehiculos(carroceria);
CREATE INDEX ix_veh_combustible ON vehiculos(tipo_combustible);
CREATE INDEX ix_veh_precio ON vehiculos(precio_base_cop);
CREATE INDEX ix_veh_estado ON vehiculos(estado_comercial);
CREATE INDEX ix_veh_anio ON vehiculos(anio);
CREATE INDEX ix_veh_marca_modelo ON vehiculos(marca, modelo, anio);
CREATE TABLE fiabilidad (
  vehiculo_id INTEGER PRIMARY KEY REFERENCES vehiculos(id),
  puntaje_fiabilidad REAL NOT NULL CHECK (puntaje_fiabilidad BETWEEN 1 AND 10),
  desglose TEXT NOT NULL, nivel_costo_mantenimiento TEXT NOT NULL, costo_mantenimiento_anual_cop INTEGER,
  costo_primeros_60000km_cop INTEGER, disponibilidad_repuestos TEXT, depreciacion_estimada TEXT, retencion_valor TEXT,
  veredicto_honesto TEXT NOT NULL CHECK (length(veredicto_honesto) BETWEEN 350 AND 700), para_quien_si TEXT, para_quien_no TEXT,
  pros_reales TEXT, fallas_comunes_y_contras TEXT, alertas TEXT, alternativas_recomendadas TEXT, fuentes_ids TEXT
);
CREATE TABLE recalls (id TEXT PRIMARY KEY, titulo TEXT, marcas TEXT, modelos TEXT, anio_desde INTEGER, anio_hasta INTEGER,
  descripcion TEXT, ente TEXT, fecha TEXT, estado TEXT, fuentes_ids TEXT);
CREATE TABLE actualizaciones (id INTEGER PRIMARY KEY, marca TEXT, modelo TEXT, anio_modelo INTEGER, vehiculo_ids TEXT,
  vehiculo_anterior_id INTEGER, tipo TEXT, categorias TEXT, fecha_lanzamiento_colombia TEXT, titulo TEXT, resumen TEXT,
  cambios TEXT, delta_precio_cop INTEGER, imagen_antes_id TEXT, imagen_despues_id TEXT, vale_la_pena TEXT,
  razon_veredicto TEXT, fuentes_ids TEXT, segmento TEXT, estado_dato TEXT);
CREATE INDEX ix_act_fecha ON actualizaciones(fecha_lanzamiento_colombia);
CREATE VIRTUAL TABLE vehiculos_fts USING fts5(marca, modelo, version, segmento, carroceria, tipo_combustible,
  tokenize = 'unicode61 remove_diacritics 2');
"""


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DB_DEFECTO))
    args = ap.parse_args()
    s = Sembrador()
    s.construir()
    if s.errores:
        print(f"Se encontraron {len(s.errores)} errores de validación:")
        for e in s.errores[:60]:
            print("  -", e)
        return 1
    destino = Path(args.db)
    destino.parent.mkdir(parents=True, exist_ok=True)
    s.escribir(destino)
    s.reporte()
    print(f"\nBase escrita en {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
