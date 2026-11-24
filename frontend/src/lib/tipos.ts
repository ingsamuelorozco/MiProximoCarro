export interface Tarjeta {
  id: number
  slug: string
  marca: string
  modelo: string
  anio: number
  version: string
  segmento: string
  carroceria: string
  tipo_combustible: string
  precio_base_cop: number
  precio_base_usd: number
  precio_total_en_calle_cop: number
  potencia_hp: number
  torque_nm: number
  consumo_real_estimado_kml: number | null
  consumo_kwh_100km: number | null
  autonomia_estimada_km: number | null
  distancia_libre_suelo_mm: number
  capacidad_baul_litros: number
  plazas: number
  transmision_tipo: string
  traccion: string
  puntaje_fiabilidad: number
  tiene_alerta_roja: boolean
  imagen_id: string | null
  estado_comercial: string
  numero_airbags: number
  largo_mm: number
  alto_mm: number
  distancia_entre_ejes_mm: number
  voladizo_delantero_mm: number
  voladizo_trasero_mm: number
  diametro_rueda_mm: number
  indice_garaje_etiqueta: string
  indice_rompemuelle_etiqueta: string
  puntaje_miproximocarro_base: number | null
  pais_origen: string
  fecha_precio: string
}

export interface Alerta {
  nivel: 'ROJA' | 'AMARILLA'
  texto: string
}

export interface Fuente {
  id: string
  titulo: string
  url: string
  tipo: string
  fecha_consulta: string
}

export interface Falla {
  componente: string
  descripcion: string
  km_tipico: string
  costo_reparacion_cop_aprox: number
  severidad: 'Baja' | 'Media' | 'Alta' | 'Crítica'
  tipo: 'documentada' | 'editorial'
  fuente_id: string
  fuentes_ids: string[]
  fuentes?: Fuente[]
}

export interface Paginado<T> {
  total: number
  page: number
  size: number
  paginas: number
  resultados: T[]
  sugerencia: string | null
}

export interface Ciudad {
  id: string
  nombre: string
  altitud_msnm: number
}

/** Medidas mínimas para dibujar una silueta. */
export interface Medidas {
  id?: number
  carroceria: string
  largo_mm: number
  alto_mm: number
  distancia_entre_ejes_mm: number
  distancia_libre_suelo_mm: number
  voladizo_delantero_mm: number
  voladizo_trasero_mm: number
  diametro_rueda_mm: number
  ancho_sin_espejos_mm?: number
  ancho_con_espejos_mm?: number
}

/** Un modelo con sus versiones agrupadas (GET /api/vehiculos/modelos). */
export interface Modelo {
  marca: string
  modelo: string
  carroceria: string
  segmento: string
  anios: number[]
  versiones: number
  combustibles: string[]
  precio_calle_min: number | null
  precio_calle_max: number | null
  puntaje_fiabilidad: number
  tiene_alerta_roja: boolean
  /** Mejor versión del grupo según el orden pedido: aporta foto, medidas y datos de muestra. */
  representante: Tarjeta
}

export type PaginadoModelos = Paginado<Modelo> & { total_versiones: number }
