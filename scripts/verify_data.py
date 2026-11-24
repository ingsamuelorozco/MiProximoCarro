"""Control de calidad de db/cars.db. Sale con código distinto de cero si algo falla.

Uso: python scripts/verify_data.py [--db ruta]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import yaml  # noqa: E402

from backend.app.schemas import (  # noqa: E402
    NO_APLICA_BEV, NO_APLICA_COMBUSTION, NO_APLICA_HIBRIDO_NO_ENCHUFABLE, OPCIONALES, VehiculoRegistro,
)
from backend.app.services.puntaje import puntaje_fiabilidad  # noqa: E402

MINIMOS = {"total": 300, "marcas": 18, "Sedán": 30, "Hatchback": 40, "SUV": 120, "Pickup": 30,
           "Deportivo": 15, "electrificados": 40, "actualizados": 20}
MARCAS_REQUERIDAS = {"Mazda", "Toyota", "Chevrolet", "Renault", "Kia", "Hyundai", "Volkswagen", "Ford", "Nissan",
                     "Honda", "Subaru", "BMW", "Mercedes-Benz", "Audi", "BYD", "Chery", "Suzuki", "Peugeot"}
ELECTRIFICADOS = ("Híbrido Completo HEV", "Híbrido Ligero MHEV", "Híbrido Enchufable PHEV", "100% Eléctrico BEV")
# Potencia específica plausible (hp por litro) según alimentación.
HP_POR_LITRO = {"Atmosférico": (35, 115), "Turbo": (55, 200)}


def campos_permitidos_nulos(v: dict) -> set[str]:
    tipo = v["tipo_combustible"]
    permitidos = set(OPCIONALES)
    if tipo == "100% Eléctrico BEV":
        permitidos |= NO_APLICA_BEV
    if tipo in ("Gasolina Corriente", "Gasolina Extra", "Diésel"):
        permitidos |= NO_APLICA_COMBUSTION
    if tipo in ("Híbrido Completo HEV", "Híbrido Ligero MHEV"):
        permitidos |= NO_APLICA_HIBRIDO_NO_ENCHUFABLE | {"garantia_bateria_anos", "garantia_bateria_km"}
    if tipo == "Diésel":
        permitidos |= {"octanaje_minimo_recomendado"}
    if tipo == "Híbrido Ligero MHEV":
        permitidos |= {"capacidad_bateria_kwh"}
    if tipo == "Híbrido Enchufable PHEV":
        permitidos |= {"potencia_carga_dc_kw"}
    if tipo != "100% Eléctrico BEV":
        permitidos |= {"autonomia_estimada_km"}
    if v["carroceria"] in ("Sedán", "Coupé", "Convertible", "Pickup"):
        permitidos |= {"capacidad_baul_abatido_litros"}
    if v["transmision_tipo"] and ("CVT" in v["transmision_tipo"] or "e-CVT" in v["transmision_tipo"]):
        permitidos |= {"numero_velocidades"}
    if v["tipo_combustible"] in ELECTRIFICADOS:
        permitidos |= {"rpm_torque_max"}
    return permitidos


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(RAIZ / "db" / "cars.db"))
    args = ap.parse_args()
    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    errores: list[str] = []
    avisos: list[str] = []

    vs = [dict(r) for r in con.execute("SELECT * FROM vehiculos")]
    fia = {r["vehiculo_id"]: dict(r) for r in con.execute("SELECT * FROM fiabilidad")}
    imagenes = {r["id"] for r in con.execute("SELECT id FROM imagenes")}
    yaml_imgs = {i["id"] for i in yaml.safe_load((RAIZ / "data" / "imagenes.yaml").read_text(encoding="utf-8"))["imagenes"]}
    fuentes = {r["id"] for r in con.execute("SELECT id FROM fuentes")}
    for v in vs:
        for k in ("adas_incluidas", "campos_estimados", "fuentes_ids"):
            v[k] = json.loads(v[k])

    # 1. Campos obligatorios y reglas por registro
    for v in vs:
        s = v["slug"]
        nulos = {k for k in VehiculoRegistro.model_fields if v.get(k) is None} - {"id", "puntaje_miproximocarro_base"}
        indebidos = nulos - campos_permitidos_nulos(v)
        if indebidos:
            errores.append(f"{s}: campos obligatorios en NULL: {sorted(indebidos)}")
        if v["ancho_con_espejos_mm"] <= v["ancho_sin_espejos_mm"]:
            errores.append(f"{s}: ancho con espejos ≤ sin espejos")
        if not 100 <= v["distancia_libre_suelo_mm"] <= 300:
            errores.append(f"{s}: despeje fuera de 100–300 mm")
        if v["precio_total_en_calle_cop"] != v["precio_base_cop"] + v["costo_soat_cop"] + v["costo_matricula_estimado_cop"]:
            errores.append(f"{s}: precio total en calle ≠ base + SOAT + matrícula")
        if v["cilindraje_cc"] and v["alimentacion"] in HP_POR_LITRO and v["tipo_combustible"] not in ELECTRIFICADOS:
            hpl = v["potencia_hp"] / (v["cilindraje_cc"] / 1000)
            # Los turbodiésel de trabajo rinden menos por litro que un turbo de gasolina (p. ej., 43 hp/L en un 3.0 TD).
            lo, hi = (30, 120) if v["tipo_combustible"] == "Diésel" else HP_POR_LITRO[v["alimentacion"]]
            if not lo <= hpl <= hi:
                errores.append(f"{s}: potencia implausible para el cilindraje ({hpl:.0f} hp/L, {v['alimentacion']})")
        if v["torque_nm"] < v["potencia_hp"] * 0.5:
            errores.append(f"{s}: torque implausible para la potencia")
        if v["imagen_id"] and (v["imagen_id"] not in imagenes or v["imagen_id"] not in yaml_imgs):
            errores.append(f"{s}: imagen {v['imagen_id']} no existe en imagenes.yaml")
        if (v["octanaje_minimo_recomendado"] or 0) >= 95 and v["tipo_combustible"] == "Gasolina Corriente":
            avisos.append(f"{s}: pide octanaje 95 pero figura como gasolina corriente")
        for fid in v["fuentes_ids"] + [v["fuente_precio_id"]]:
            if fid not in fuentes:
                errores.append(f"{s}: fuente {fid} inexistente")

    # 2. Fiabilidad
    for v in vs:
        f = fia.get(v["id"])
        if not f:
            errores.append(f"{v['slug']}: sin fila de fiabilidad")
            continue
        pros = json.loads(f["pros_reales"])
        fallas = json.loads(f["fallas_comunes_y_contras"])
        alertas = json.loads(f["alertas"])
        if len(pros) < 3:
            errores.append(f"{v['slug']}: menos de 3 pros")
        if len(fallas) < 2:
            errores.append(f"{v['slug']}: menos de 2 contras")
        for fa in fallas:
            if not fa.get("severidad") or not fa.get("fuente_id"):
                errores.append(f"{v['slug']}: falla sin severidad o fuente ({fa.get('componente')})")
            if fa.get("tipo") == "documentada" and len(fa.get("fuentes_ids", [])) < 2:
                errores.append(f"{v['slug']}: falla documentada con menos de 2 fuentes ({fa['componente']})")
        if abs(puntaje_fiabilidad(json.loads(f["desglose"]), alertas) - f["puntaje_fiabilidad"]) > 0.05:
            errores.append(f"{v['slug']}: el puntaje no coincide con la fórmula publicada")
        if not 350 <= len(f["veredicto_honesto"]) <= 700:
            errores.append(f"{v['slug']}: veredicto fuera de 350–700 caracteres")
        if "Captiva" in v["modelo"] and "1.5" in v["motor_descripcion"]:
            if f["puntaje_fiabilidad"] > 4.0 or not any(a["nivel"] == "ROJA" for a in alertas):
                errores.append(f"{v['slug']}: regla Captiva Turbo incumplida")

    # 3. Cobertura
    marcas = Counter(v["marca"] for v in vs)
    carr = Counter(v["carroceria"] for v in vs)
    act_ids = set()
    for r in con.execute("SELECT vehiculo_ids FROM actualizaciones"):
        act_ids |= set(json.loads(r[0]))
    cobertura = {
        "total": len(vs), "marcas": len(marcas), "Sedán": carr["Sedán"], "Hatchback": carr["Hatchback"],
        "SUV": carr["SUV"], "Pickup": carr["Pickup"],
        "Deportivo": sum(1 for v in vs if v["segmento"] == "Deportivo"),
        "electrificados": sum(1 for v in vs if v["tipo_combustible"] in ELECTRIFICADOS),
        "actualizados": len(act_ids),
    }
    for k, minimo in MINIMOS.items():
        if cobertura[k] < minimo:
            errores.append(f"Cobertura insuficiente: {k} = {cobertura[k]} (mínimo {minimo})")
    faltan = MARCAS_REQUERIDAS - set(marcas)
    if faltan:
        errores.append(f"Faltan marcas: {sorted(faltan)}")
    for m, n in marcas.items():
        # Con el catálogo histórico (2000–2026) una marca grande supera con creces las 30 versiones.
        if not 8 <= n <= 600:
            errores.append(f"{m}: {n} versiones (debe estar entre 8 y 600)")
    claves = Counter((v["marca"], v["modelo"], v["anio"], v["version"]) for v in vs)
    for k, n in claves.items():
        if n > 1:
            errores.append(f"Duplicado: {k}")

    # 4. Reporte
    print("=== Reporte de calidad MiProximoCarro ===")
    print("Cobertura: " + ", ".join(f"{k}={v}" for k, v in cobertura.items()))
    for titulo, clave in (("marca", "marca"), ("segmento", "segmento"), ("combustible", "tipo_combustible"), ("año", "anio")):
        c = Counter(v[clave] for v in vs)
        print(f"Por {titulo}: " + ", ".join(f"{k}={n}" for k, n in sorted(c.items(), key=lambda x: str(x[0]))))
    conteo_est: Counter[str] = Counter()
    conteo_pres: Counter[str] = Counter()
    for v in vs:
        for c in v["campos_estimados"]:
            conteo_est[c] += 1
        for c in VehiculoRegistro.model_fields:
            if v.get(c) is not None:
                conteo_pres[c] += 1
    print("\nPorcentaje estimado por campo (sobre valores presentes):")
    for c in sorted(conteo_est):
        print(f"  {c}: {conteo_est[c] / max(conteo_pres[c], 1):.0%}")
    total_est = sum(conteo_est.values())
    total_pres = sum(conteo_pres[c] for c in conteo_est)
    print(f"Global: {total_est / max(total_pres, 1):.1%} de los datos técnicos y de precio están marcados como estimados")
    for a in avisos:
        print("AVISO:", a)
    if errores:
        print(f"\n{len(errores)} ERRORES:")
        for e in errores[:100]:
            print("  -", e)
        return 1
    print("\nOK: sin errores.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
