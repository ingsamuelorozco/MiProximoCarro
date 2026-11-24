"""Modelos Pydantic v2: registro de vehículo (validación del seeding) y esquemas de la API."""
from __future__ import annotations

from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

TipoCombustible = Literal[
    "Gasolina Corriente", "Gasolina Extra", "Diésel", "Híbrido Completo HEV",
    "Híbrido Ligero MHEV", "Híbrido Enchufable PHEV", "100% Eléctrico BEV",
]
Carroceria = Literal["Sedán", "Hatchback", "SUV", "Pickup", "Coupé", "Convertible"]
EstadoComercial = Literal["Vigente", "Descontinuado", "Próximamente"]
Nivel = Literal["Bajo", "Moderado", "Alto", "Muy Alto"]
Disponibilidad = Literal["Alta", "Media", "Baja"]
Depreciacion = Literal["Baja - Alta reventa", "Media", "Alta - Se desvaloriza rápido"]
Severidad = Literal["Baja", "Media", "Alta", "Crítica"]

# Campos que no aplican según el tipo de motor (verify_data.py los acepta en NULL).
NO_APLICA_BEV = {"cilindraje_cc", "cilindros", "valvulas", "octanaje_minimo_recomendado", "consumo_ciudad_kml",
                 "consumo_carretera_kml", "consumo_mixto_kml", "consumo_real_estimado_kml", "capacidad_tanque_galones",
                 "rpm_potencia_max", "rpm_torque_max", "numero_velocidades"}
NO_APLICA_COMBUSTION = {"potencia_electrica_kw", "capacidad_bateria_kwh", "potencia_carga_ac_kw", "potencia_carga_dc_kw",
                        "consumo_kwh_100km", "garantia_bateria_anos", "garantia_bateria_km"}
NO_APLICA_HIBRIDO_NO_ENCHUFABLE = {"potencia_carga_ac_kw", "potencia_carga_dc_kw", "consumo_kwh_100km"}
OPCIONALES = {"aceleracion_0_100_seg", "velocidad_maxima_kmh", "angulo_ataque_deg", "angulo_ventral_deg", "angulo_salida_deg",
              "profundidad_vadeo_mm", "capacidad_remolque_kg", "ncap_organismo", "ncap_estrellas", "ncap_anio", "ncap_protocolo",
              "emisiones_co2_g_km", "imagen_id", "fecha_lanzamiento_colombia", "garantia_km", "capacidad_baul_abatido_litros",
              "rpm_potencia_max", "rpm_torque_max", "pantalla_multimedia_pulgadas", "potencia_carga_dc_kw"}


class VehiculoRegistro(BaseModel):
    """Una versión comercial concreta, ya aplanada y con derivados calculados."""
    model_config = ConfigDict(extra="forbid")

    id: Optional[int] = None
    slug: str
    marca: str
    modelo: str
    anio: int = Field(ge=2000, le=2026)
    version: str
    generacion: Optional[str] = None
    segmento: str
    carroceria: Carroceria
    puertas: int = Field(ge=2, le=5)
    plazas: int = Field(ge=2, le=9)
    pais_origen: str
    imagen_id: Optional[str] = None
    estado_comercial: EstadoComercial
    fecha_lanzamiento_colombia: Optional[date] = None
    # Motor
    tipo_combustible: TipoCombustible
    motor_descripcion: str
    cilindraje_cc: Optional[int] = Field(default=None, ge=600, le=7000)
    cilindros: Optional[int] = Field(default=None, ge=2, le=12)
    valvulas: Optional[int] = None
    alimentacion: Literal["Atmosférico", "Turbo", "Eléctrico"]
    potencia_hp: float = Field(ge=40, le=1000)
    rpm_potencia_max: Optional[int] = None
    torque_nm: float = Field(ge=50, le=1500)
    rpm_torque_max: Optional[int] = None
    relacion_peso_potencia: float
    aceleracion_0_100_seg: Optional[float] = Field(default=None, ge=2, le=25)
    velocidad_maxima_kmh: Optional[int] = Field(default=None, ge=100, le=350)
    octanaje_minimo_recomendado: Optional[int] = None
    emisiones_co2_g_km: Optional[float] = None
    potencia_electrica_kw: Optional[float] = None
    capacidad_bateria_kwh: Optional[float] = None
    potencia_carga_ac_kw: Optional[float] = None
    potencia_carga_dc_kw: Optional[float] = None
    # Transmisión y chasis
    transmision_tipo: str
    numero_velocidades: Optional[int] = None
    traccion: str
    suspension_delantera: str
    suspension_trasera: str
    frenos_delanteros: str
    frenos_traseros: str
    direccion: str
    radio_giro_metros: Optional[float] = None
    medida_llantas: str
    diametro_rueda_mm: int
    profundidad_vadeo_mm: Optional[int] = None
    capacidad_remolque_kg: Optional[int] = None
    # Dimensiones
    largo_mm: int = Field(ge=2500, le=6500)
    ancho_sin_espejos_mm: int
    ancho_con_espejos_mm: int
    alto_mm: int
    distancia_entre_ejes_mm: int
    distancia_libre_suelo_mm: int = Field(ge=100, le=300)
    peso_vacio_kg: int
    capacidad_carga_kg: int
    capacidad_baul_litros: int
    capacidad_baul_abatido_litros: Optional[int] = None
    voladizo_delantero_mm: int
    voladizo_trasero_mm: int
    angulo_ataque_deg: Optional[float] = None
    angulo_ventral_deg: Optional[float] = None
    angulo_salida_deg: Optional[float] = None
    capacidad_tanque_galones: Optional[float] = None
    autonomia_estimada_km: Optional[int] = None
    autonomia_ciclo: Literal["WLTP", "NEDC", "EPA", "Estimada"]
    # Consumo
    consumo_ciudad_kml: Optional[float] = None
    consumo_carretera_kml: Optional[float] = None
    consumo_mixto_kml: Optional[float] = None
    consumo_real_estimado_kml: Optional[float] = None
    consumo_kwh_100km: Optional[float] = None
    ciclo_homologacion: str
    # Seguridad
    numero_airbags: int = Field(ge=0, le=12)
    ncap_organismo: Optional[str] = None
    ncap_estrellas: Optional[int] = Field(default=None, ge=0, le=5)
    ncap_anio: Optional[int] = None
    ncap_protocolo: Optional[str] = None
    frenos_abs_ebd: bool
    control_estabilidad_esc: bool
    asistente_arranque_pendiente: bool
    anclajes_isofix: bool
    adas_incluidas: list[str]
    # Equipamiento
    pantalla_multimedia_pulgadas: Optional[float] = None
    apple_carplay_android_auto: Literal["No", "Cable", "Inalámbrico"]
    aire_acondicionado: Literal["No", "Manual", "Automático", "Automático bizona"]
    tapiceria: Literal["Tela", "Cuero sintético", "Cuero"]
    techo_corredizo: bool
    camara_reversa: bool
    carga_inalambrica: bool
    llave_inteligente: bool
    sensores_parqueo: Literal["Ninguno", "Trasero", "Delantero y trasero"]
    luces_led: bool
    # Garantía y precios
    garantia_anos: int
    garantia_km: Optional[int] = None
    garantia_km_ilimitada: bool
    garantia_bateria_anos: Optional[int] = None
    garantia_bateria_km: Optional[int] = None
    precio_base_cop: int = Field(gt=10_000_000)
    fecha_precio: date
    fuente_precio_id: str
    trm_referencia: float
    precio_base_usd: int
    avaluo_fasecolda_cop: int
    costo_soat_cop: int
    costo_matricula_estimado_cop: int
    precio_total_en_calle_cop: int
    # Calidad del dato
    campos_estimados: list[str]
    confianza_dato: Literal["Alta", "Media", "Baja"]
    fuentes_ids: list[str]
    ultima_verificacion: date
    # Derivados para búsqueda y comparación
    indice_rompemuelle_nivel: int
    indice_rompemuelle_etiqueta: str
    indice_garaje_nivel: int
    indice_garaje_etiqueta: str
    puntaje_fiabilidad: float = Field(ge=1, le=10)
    tiene_alerta_roja: bool
    riesgo_hurto: Literal["Bajo", "Medio", "Alto"]
    nivel_costo_mantenimiento: Nivel
    depreciacion_estimada: Depreciacion
    retencion_5_anios: float
    puntaje_miproximocarro_base: Optional[int] = None

    @model_validator(mode="after")
    def _reglas(self) -> "VehiculoRegistro":
        if self.ancho_con_espejos_mm <= self.ancho_sin_espejos_mm:
            raise ValueError("ancho_con_espejos_mm debe ser mayor que ancho_sin_espejos_mm")
        if self.precio_total_en_calle_cop != self.precio_base_cop + self.costo_soat_cop + self.costo_matricula_estimado_cop:
            raise ValueError("precio_total_en_calle_cop ≠ base + SOAT + matrícula")
        if self.tipo_combustible == "100% Eléctrico BEV":
            for k in ("cilindraje_cc", "capacidad_tanque_galones", "consumo_mixto_kml"):
                if getattr(self, k) is not None:
                    raise ValueError(f"{k} debe ser NULL en un BEV")
            if not self.capacidad_bateria_kwh or not self.consumo_kwh_100km:
                raise ValueError("un BEV requiere capacidad_bateria_kwh y consumo_kwh_100km")
        else:
            if self.cilindraje_cc is None or self.consumo_mixto_kml is None:
                raise ValueError("un vehículo de combustión requiere cilindraje y consumo mixto")
        if self.tipo_combustible in ("Gasolina Corriente", "Gasolina Extra", "Diésel"):
            for k in NO_APLICA_COMBUSTION:
                if getattr(self, k) is not None:
                    raise ValueError(f"{k} debe ser NULL en un vehículo sin electrificación")
        return self


class Falla(BaseModel):
    componente: str
    descripcion: str
    km_tipico: str
    costo_reparacion_cop_aprox: int
    severidad: Severidad
    tipo: Literal["documentada", "editorial"] = "editorial"
    fuente_id: str
    fuentes_ids: list[str]


class Alerta(BaseModel):
    nivel: Literal["ROJA", "AMARILLA"]
    texto: str


class FiabilidadRegistro(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vehiculo_id: int
    puntaje_fiabilidad: float = Field(ge=1, le=10)
    desglose: dict[str, float]
    nivel_costo_mantenimiento: Nivel
    costo_mantenimiento_anual_cop: int
    costo_primeros_60000km_cop: int
    disponibilidad_repuestos: Disponibilidad
    depreciacion_estimada: Depreciacion
    retencion_valor: dict[str, float]
    veredicto_honesto: str = Field(min_length=350, max_length=700)
    para_quien_si: str
    para_quien_no: str
    pros_reales: list[str] = Field(min_length=3)
    fallas_comunes_y_contras: list[Falla] = Field(min_length=2)
    alertas: list[Alerta]
    alternativas_recomendadas: list[int]
    fuentes_ids: list[str]


# ------------------------------------------------------------------ API
class Error(BaseModel):
    codigo: str
    mensaje: str
    detalle: Any = None
    model_config = ConfigDict(json_schema_extra={"example": {"codigo": "no_encontrado", "mensaje": "Vehículo no encontrado", "detalle": {"id": 9999}}})


class CompararIn(BaseModel):
    ids: list[int] = Field(min_length=2, max_length=10)
    moneda: Literal["COP", "USD"] = "COP"
    trm: Optional[float] = Field(default=None, gt=1000, lt=10000)
    ciudad: Optional[str] = None
    perfil: Optional[str] = None
    referencia_id: Optional[int] = None
    model_config = ConfigDict(json_schema_extra={"example": {"ids": [1, 2, 3], "moneda": "COP", "trm": 3316.7, "ciudad": "bogota", "perfil": "familiar"}})


class PuestaEnCalleIn(BaseModel):
    vehiculo_id: Optional[int] = None
    precio_base_cop: Optional[float] = Field(default=None, gt=0)
    cilindraje_cc: Optional[int] = None
    carroceria: Carroceria = "Sedán"
    tipo_combustible: TipoCombustible = "Gasolina Corriente"
    ciudad: Optional[str] = None
    mes_compra: Optional[int] = Field(default=None, ge=1, le=12)
    incluir_alistamiento: Optional[bool] = None
    model_config = ConfigDict(json_schema_extra={"example": {"vehiculo_id": 1, "ciudad": "bogota", "mes_compra": 11}})


class Abono(BaseModel):
    mes: int = Field(ge=1, le=84)
    valor: float = Field(gt=0)


class CreditoIn(BaseModel):
    precio_cop: float = Field(gt=0)
    tramites_cop: float = 0
    financiar_tramites: bool = False
    cuota_inicial_pct: Optional[float] = Field(default=None, ge=0, le=0.95)
    cuota_inicial_cop: Optional[float] = Field(default=None, ge=0)
    plazo_meses: Optional[int] = Field(default=None, ge=12, le=84)
    tasa_ea: Optional[float] = Field(default=None, ge=0, le=1)
    seguro_vida_mensual_pct: Optional[float] = Field(default=None, ge=0, le=0.01)
    seguro_vehiculo_mensual_cop: float = 0
    comision_cop: Optional[float] = None
    tipo_cuota: Literal["fija", "balon"] = "fija"
    valor_final_pct: float = Field(default=0, ge=0, le=0.6)
    abonos: list[Abono] = []
    modo_abono: Literal["plazo", "cuota"] = "plazo"
    max_pct_ingreso: Optional[float] = Field(default=None, gt=0, le=1)
    incluir_tabla: bool = True
    model_config = ConfigDict(json_schema_extra={"example": {"precio_cop": 100000000, "cuota_inicial_pct": 0.3, "plazo_meses": 60, "tasa_ea": 0.155}})


class SeguroIn(BaseModel):
    vehiculo_id: Optional[int] = None
    valor_asegurado_cop: Optional[float] = None
    segmento: Optional[str] = None
    ciudad: Optional[str] = None
    edad_conductor: Literal["18-25", "26-35", "36-55", "56+"] = "36-55"
    uso: Literal["particular", "trabajo"] = "particular"
    antiguedad_anios: int = Field(default=0, ge=0, le=30)
    deducible: Literal["0", "1", "3", "10"] = "1"
    model_config = ConfigDict(json_schema_extra={"example": {"vehiculo_id": 1, "ciudad": "bogota", "edad_conductor": "26-35"}})


class TcoIn(BaseModel):
    vehiculo_id: int
    anios: int = Field(default=5, ge=1, le=10)
    km_anio: Optional[float] = Field(default=None, gt=0, le=100000)
    mezcla_ciudad: Optional[float] = Field(default=None, ge=0, le=1)
    ciudad: Optional[str] = None
    carga_casa_pct: Optional[float] = Field(default=None, ge=0, le=1)
    financiar: bool = False
    comparar_con_id: Optional[int] = None
    model_config = ConfigDict(json_schema_extra={"example": {"vehiculo_id": 1, "anios": 5, "km_anio": 15000, "ciudad": "bogota"}})


class ReventaIn(BaseModel):
    vehiculo_ids: list[int] = Field(min_length=1, max_length=10)
    trm: Optional[float] = None
    model_config = ConfigDict(json_schema_extra={"example": {"vehiculo_ids": [1, 2]}})


class AsequibilidadIn(BaseModel):
    ingreso_mensual_cop: float = Field(gt=0)
    cuota_inicial_cop: float = Field(ge=0)
    plazo_meses: int = Field(default=60, ge=12, le=84)
    max_pct_ingreso: float = Field(default=0.30, gt=0, le=0.8)
    ciudad: Optional[str] = None
    km_anio: Optional[float] = None
    limite: int = Field(default=30, ge=1, le=100)
    model_config = ConfigDict(json_schema_extra={"example": {"ingreso_mensual_cop": 9000000, "cuota_inicial_cop": 30000000, "plazo_meses": 60, "max_pct_ingreso": 0.3}})
