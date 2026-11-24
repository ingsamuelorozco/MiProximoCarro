<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useHead } from '@unhead/vue'
import { useMediaQuery } from '@vueuse/core'
import { Check, GitCompare, Heart, Share2, X } from 'lucide-vue-next'
import { api } from '@/lib/api'
import { useCarga } from '@/composables/useCarga'
import { useFormato } from '@/composables/useFormato'
import { useAjustes } from '@/stores/ajustes'
import { useComparador } from '@/stores/comparador'
import { useFavoritos } from '@/stores/favoritos'
import { T } from '@/lib/textos'
import BarraFinanciera from '@/components/BarraFinanciera.vue'
import EstadoCarga from '@/components/EstadoCarga.vue'
import AlertaBanner from '@/components/AlertaBanner.vue'
import BadgeEstimado from '@/components/BadgeEstimado.vue'
import ImagenVehiculo from '@/components/ImagenVehiculo.vue'
import HuellaComparador from '@/components/HuellaComparador.vue'
import MedidorFiabilidad from '@/components/MedidorFiabilidad.vue'
import GraficoLineas from '@/components/GraficoLineas.vue'
import BarraApilada from '@/components/BarraApilada.vue'
import TarjetaVehiculo from '@/components/TarjetaVehiculo.vue'

const props = defineProps<{ slug: string }>()
const aj = useAjustes()
const comp = useComparador()
const fav = useFavoritos()
const f = useFormato()
const movil = useMediaQuery('(max-width: 767px)')
const { datos: d, cargando, error, ejecutar } = useCarga(() => api.get<any>(`/vehiculos/${props.slug}`, { ciudad: aj.ciudad, trm: aj.trm }))
onMounted(ejecutar)
watch(() => [props.slug, aj.ciudad], ejecutar)
watch(d, (v) => v && fav.visto(v.id))
useHead(() => ({
  title: d.value?.nombre || 'Vehículo',
  meta: [
    { property: 'og:title', content: d.value ? `${d.value.nombre} · MiProximoCarro` : 'MiProximoCarro' },
    { property: 'og:description', content: d.value ? `Precio en calle ${f.cop(d.value.precio.puesta_en_calle.total_cop)} · Fiabilidad ${d.value.fiabilidad.puntaje}/10` : '' },
  ],
}))

const SECCIONES = [
  { id: 'especificaciones', t: 'Especificaciones' }, { id: 'tamano', t: 'Tamaño y uso urbano' }, { id: 'precio', t: 'Precio y reventa' },
  { id: 'costo', t: 'Costo de tenerlo' }, { id: 'fiabilidad', t: 'Fiabilidad' }, { id: 'versiones', t: 'Versiones y rivales' },
]
const activa = ref('especificaciones')
const abiertas = ref(new Set(['especificaciones']))
let obs: IntersectionObserver | null = null
watch(d, () => setTimeout(() => {
  obs?.disconnect()
  obs = new IntersectionObserver((es) => es.forEach((e) => e.isIntersecting && (activa.value = e.target.id)), { rootMargin: '-40% 0px -55% 0px' })
  SECCIONES.forEach((s) => { const el = document.getElementById(s.id); if (el) obs!.observe(el) })
}, 50))
onUnmounted(() => obs?.disconnect())
const abierta = (id: string) => !movil.value || abiertas.value.has(id)
const alternarSec = (id: string) => (abiertas.value.has(id) ? abiertas.value.delete(id) : abiertas.value.add(id))

const est = (campo: string) => d.value?.calidad_dato.campos_estimados.includes(campo)
const sino = (b: boolean | null) => (b == null ? '—' : b ? 'Sí' : 'No')
const tope = ref(120)
const plaza = ref({ largo: 5000, ancho: 2400 })
const garajeUsuario = ref<any>(null)
async function recalcularGaraje() {
  if (!d.value) return
  const m = d.value.tamano.medidas
  const lat = (plaza.value.ancho - m.ancho_sin_espejos_mm) / 2
  const hol = plaza.value.largo - m.largo_mm
  garajeUsuario.value = { holgura: hol, lateral: lat }
}
watch([plaza, d], recalcularGaraje, { deep: true })
const kmMes = ref(1250)
const energiaMensual = computed(() => (d.value ? d.value.costo.energia.costo_por_km_cop * kmMes.value : 0))
const credito = ref({ inicialPct: 30, plazo: 60, tasa: 15.5 })
const sim = ref<any>(null)
async function simular() {
  if (!d.value) return
  sim.value = await api.post('/financiero/credito', { precio_cop: d.value.precio.puesta_en_calle.precio_base_cop, cuota_inicial_pct: credito.value.inicialPct / 100,
    plazo_meses: credito.value.plazo, tasa_ea: credito.value.tasa / 100, incluir_tabla: false })
}
watch([credito, d], simular, { deep: true })
const huella = computed(() => (d.value ? [{ id: d.value.id, nombre: d.value.nombre, ...d.value.tamano.medidas, indice_garaje_etiqueta: d.value.tamano.garaje.etiqueta,
  indice_rompemuelle_etiqueta: d.value.tamano.rompemuelle.etiqueta }] : []))
const serieReventa = computed(() => (d.value ? [{ nombre: d.value.nombre, puntos: [{ x: 0, y: d.value.precio.puesta_en_calle.precio_base_cop }, ...d.value.precio.reventa.puntos.map((p: any) => ({ x: p.anio, y: p.valor_cop }))] }] : []))
const tcoComp = computed(() => (d.value ? { ...d.value.costo.tco5.componentes_cop, tramites: d.value.costo.tco5.tramites_iniciales_cop, depreciacion: d.value.costo.tco5.depreciacion_cop } : {}))
const copiado = ref(false)
async function compartir() {
  try {
    if (navigator.share) await navigator.share({ title: d.value?.nombre, url: location.href })
    else { await navigator.clipboard.writeText(location.href); copiado.value = true; setTimeout(() => (copiado.value = false), 2000) }
  } catch { /* cancelado */ }
}
</script>

<template>
  <BarraFinanciera />
  <div class="contenedor pagina">
    <EstadoCarga :cargando="cargando && !d" :error="error" :filas="4" @reintentar="ejecutar">
      <template v-if="d">
        <!-- Encabezado -->
        <header class="grid items-start gap-8 lg:grid-cols-[1.3fr_1fr] lg:gap-12">
          <ImagenVehiculo :medidas="d.tamano.medidas" :nombre="d.nombre" :imagen-id="d.cabecera.imagen_id" credito />
          <div class="flex flex-col gap-5">
            <div class="flex flex-wrap gap-1.5">
              <span class="insignia border border-linea text-tenue">{{ d.cabecera.segmento }}</span>
              <span class="insignia border border-linea text-tenue">{{ d.cabecera.tipo_combustible }}</span>
              <span class="insignia border border-linea text-tenue">{{ d.cabecera.estado_comercial }}</span>
              <span v-if="d.cabecera.tiene_alerta_roja" class="insignia bg-roja text-white">Alerta roja</span>
            </div>
            <h1 class="titulo-pagina">{{ d.marca }} {{ d.modelo }} <span class="text-tenue">{{ d.anio }}</span></h1>
            <p class="-mt-2 text-xl text-tenue">{{ d.version }}</p>
            <dl class="grid gap-px border border-linea bg-linea sm:grid-cols-2">
              <div class="celda-dato"><dt class="etiqueta">{{ d.precio.puesta_en_calle.usado ? 'Valor usado estimado (hoy)' : 'Precio base' }}</dt><dd class="mt-2 text-2xl num">{{ f.dinero(d.cabecera.precio_base_cop) }}<BadgeEstimado /></dd><dd class="text-xs text-tenue num">{{ f.dineroSecundario(d.cabecera.precio_base_cop) }} · {{ f.fecha(d.cabecera.fecha_precio) }}</dd></div>
              <div class="celda-dato"><dt class="etiqueta">Total puesto en calle ({{ d.ciudad.nombre }})</dt><dd class="cifra mt-2">{{ f.dinero(d.precio.puesta_en_calle.total_cop) }}</dd></div>
            </dl>
            <div class="flex flex-wrap gap-3">
              <button class="boton-solido" :disabled="comp.lleno && !comp.tiene(d.id)" @click="comp.alternar(d.id)">
                <component :is="comp.tiene(d.id) ? Check : GitCompare" class="h-4 w-4" aria-hidden="true" /> {{ comp.tiene(d.id) ? 'En el comparador' : 'Añadir a comparar' }}
              </button>
              <button class="boton-secundario px-5" :aria-pressed="fav.es(d.id)" @click="fav.alternar(d.id)"><Heart :class="['h-4 w-4', fav.es(d.id) ? 'fill-tinta' : '']" aria-hidden="true" /> Favorito</button>
              <button class="boton-secundario px-5" @click="compartir"><Share2 class="h-4 w-4" aria-hidden="true" /> {{ copiado ? 'Enlace copiado' : 'Compartir' }}</button>
            </div>
            <AlertaBanner :alertas="d.alertas" compacta />
            <p class="text-xs text-tenue">Confianza del dato: {{ d.calidad_dato.confianza_dato }} · Última verificación {{ f.fecha(d.calidad_dato.ultima_verificacion) }} · <RouterLink to="/metodologia" class="underline">¿Qué significa «Estimado»?</RouterLink></p>
          </div>
        </header>

        <nav class="sticky top-[7.5rem] z-20 -mx-4 mt-12 flex gap-8 overflow-x-auto border-b border-linea bg-papel px-4 no-imprimir" aria-label="Secciones de la ficha">
          <a v-for="s in SECCIONES" :key="s.id" :href="`#${s.id}`" :class="['pestana -mb-px shrink-0 whitespace-nowrap', activa === s.id ? 'pestana-activa' : '']" :aria-current="activa === s.id ? 'true' : undefined" @click="abiertas.add(s.id)">{{ s.t }}</a>
        </nav>

        <!-- 1. Especificaciones -->
        <section id="especificaciones" class="scroll-mt-44 pt-20 lg:pt-24">
          <button class="flex w-full items-center justify-between text-left md:pointer-events-none" :aria-expanded="abierta('especificaciones')" @click="alternarSec('especificaciones')"><h2 class="titulo-seccion">Especificaciones</h2></button>
          <div v-show="abierta('especificaciones')" class="mt-8 grid gap-6 lg:grid-cols-2">
            <div class="tarjeta p-6">
              <h3 class="text-xl">Motor y rendimiento</h3>
              <dl class="lista-datos mt-4">
                <template v-for="[k, et, u] in ([['motor_descripcion', 'Motor', ''], ['cilindraje_cc', 'Cilindraje', 'cc'], ['cilindros', 'Cilindros', ''], ['valvulas', 'Válvulas', ''], ['alimentacion', 'Alimentación', ''], ['potencia_hp', 'Potencia', 'hp'], ['rpm_potencia_max', 'a (rpm)', ''], ['torque_nm', 'Torque', 'Nm'], ['rpm_torque_max', 'a (rpm)', ''], ['relacion_peso_potencia', 'Peso/potencia', 'kg/hp'], ['aceleracion_0_100_seg', '0 a 100 km/h', 's'], ['velocidad_maxima_kmh', 'Velocidad máxima', 'km/h'], ['octanaje_minimo_recomendado', 'Octanaje recomendado', 'RON'], ['emisiones_co2_g_km', 'CO₂', 'g/km'], ['capacidad_bateria_kwh', 'Batería', 'kWh'], ['potencia_electrica_kw', 'Potencia eléctrica', 'kW'], ['potencia_carga_ac_kw', 'Carga AC', 'kW'], ['potencia_carga_dc_kw', 'Carga DC', 'kW']] as const)" :key="k">
                  <template v-if="d.especificaciones.motor[k] != null">
                    <dt class="text-tenue">{{ et }}</dt>
                    <dd class="text-right num">{{ typeof d.especificaciones.motor[k] === 'number' ? f.numero(d.especificaciones.motor[k], Number.isInteger(d.especificaciones.motor[k]) ? 0 : 1) : d.especificaciones.motor[k] }} {{ u }}<BadgeEstimado v-if="est(k)" /></dd>
                  </template>
                </template>
              </dl>
              <p v-if="(d.especificaciones.motor.octanaje_minimo_recomendado || 0) >= 95" class="mt-4 border-l-4 border-ambar bg-suave p-3 text-xs">Exige gasolina extra: mayor costo por kilómetro que con corriente.</p>
              <div class="mt-6 bg-suave p-4">
                <p class="etiqueta !text-tinta">Efecto de la altura <BadgeEstimado texto="Regla práctica configurable: cerca de 10% por cada 1.000 m en atmosféricos, mucho menos en turbo y casi nada en eléctricos." /></p>
                <ul class="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
                  <li v-for="a in d.especificaciones.altura" :key="a.ciudad_id" :class="['border bg-superficie p-3', a.ciudad_id === d.ciudad.id ? 'border-tinta' : 'border-linea']">
                    <span class="block text-xs text-tenue">{{ a.ciudad }}</span>
                    <span class="font-semibold num">{{ a.potencia_efectiva_hp }} hp</span> <span class="text-xs text-tenue num">−{{ f.pct(a.perdida_pct) }}</span>
                  </li>
                </ul>
              </div>
            </div>
            <div class="tarjeta p-6">
              <h3 class="text-xl">Transmisión, chasis y frenos</h3>
              <dl class="lista-datos mt-4">
                <template v-for="[k, et, u] in ([['transmision_tipo', 'Transmisión', ''], ['numero_velocidades', 'Velocidades', ''], ['traccion', 'Tracción', ''], ['suspension_delantera', 'Suspensión delantera', ''], ['suspension_trasera', 'Suspensión trasera', ''], ['frenos_delanteros', 'Frenos delanteros', ''], ['frenos_traseros', 'Frenos traseros', ''], ['direccion', 'Dirección', ''], ['radio_giro_metros', 'Radio de giro', 'm'], ['medida_llantas', 'Llantas', ''], ['profundidad_vadeo_mm', 'Vadeo', 'mm'], ['capacidad_remolque_kg', 'Remolque', 'kg']] as const)" :key="k">
                  <template v-if="d.especificaciones.chasis[k] != null"><dt class="text-tenue">{{ et }}</dt><dd class="text-right num">{{ typeof d.especificaciones.chasis[k] === 'number' ? f.numero(d.especificaciones.chasis[k], Number.isInteger(d.especificaciones.chasis[k]) ? 0 : 1) : d.especificaciones.chasis[k] }} {{ u }}<BadgeEstimado v-if="est(k)" /></dd></template>
                </template>
              </dl>
              <h3 class="mt-6 text-xl">Seguridad y ADAS</h3>
              <dl class="lista-datos mt-4">
                <dt class="text-tenue">Airbags</dt><dd class="text-right num">{{ d.especificaciones.seguridad.numero_airbags }}</dd>
                <dt class="text-tenue">Calificación NCAP</dt>
                <dd class="text-right">{{ d.especificaciones.seguridad.ncap_estrellas != null ? `${d.especificaciones.seguridad.ncap_estrellas} ★ ${d.especificaciones.seguridad.ncap_organismo} (${d.especificaciones.seguridad.ncap_protocolo})` : 'Sin calificación registrada' }}<BadgeEstimado v-if="d.especificaciones.seguridad.ncap_estrellas != null && est('ncap_estrellas')" /></dd>
                <template v-for="[k, et] in ([['frenos_abs_ebd', 'ABS + EBD'], ['control_estabilidad_esc', 'Control de estabilidad'], ['asistente_arranque_pendiente', 'Asistente en pendiente'], ['anclajes_isofix', 'ISOFIX']] as const)" :key="k">
                  <dt class="text-tenue">{{ et }}</dt><dd class="text-right">{{ sino(d.especificaciones.seguridad[k]) }}</dd>
                </template>
              </dl>
              <p v-if="d.especificaciones.seguridad.ncap_anio && d.especificaciones.seguridad.ncap_anio < 2020" class="mt-2 text-xs text-ambar">Protocolo NCAP anterior a 2020: las exigencias actuales son mayores.</p>
              <ul class="mt-4 flex flex-wrap gap-1.5 text-xs">
                <li v-for="a in d.especificaciones.seguridad.adas_incluidas" :key="a" class="flex items-center gap-1.5 border border-linea px-2 py-1"><Check class="h-3 w-3 text-mejor" aria-hidden="true" />{{ a }}</li>
                <li v-if="!d.especificaciones.seguridad.adas_incluidas.length" class="flex items-center gap-1 text-tenue"><X class="h-3 w-3" aria-hidden="true" />Sin ayudas avanzadas de conducción</li>
              </ul>
              <h3 class="mt-6 text-xl">Equipamiento y confort</h3>
              <dl class="lista-datos mt-4">
                <dt class="text-tenue">Pantalla</dt><dd class="text-right">{{ d.especificaciones.equipamiento.pantalla_multimedia_pulgadas ? `${f.numero(d.especificaciones.equipamiento.pantalla_multimedia_pulgadas, 1)}"` : 'No' }}</dd>
                <dt class="text-tenue">CarPlay / Android Auto</dt><dd class="text-right">{{ d.especificaciones.equipamiento.apple_carplay_android_auto }}</dd>
                <dt class="text-tenue">Aire acondicionado</dt><dd class="text-right">{{ d.especificaciones.equipamiento.aire_acondicionado }}</dd>
                <dt class="text-tenue">Tapicería</dt><dd class="text-right">{{ d.especificaciones.equipamiento.tapiceria }}</dd>
                <dt class="text-tenue">Sensores de parqueo</dt><dd class="text-right">{{ d.especificaciones.equipamiento.sensores_parqueo }}</dd>
                <template v-for="[k, et] in ([['techo_corredizo', 'Techo corredizo'], ['camara_reversa', 'Cámara de reversa'], ['carga_inalambrica', 'Carga inalámbrica'], ['llave_inteligente', 'Llave inteligente'], ['luces_led', 'Luces LED']] as const)" :key="k">
                  <dt class="text-tenue">{{ et }}</dt><dd class="text-right">{{ sino(d.especificaciones.equipamiento[k]) }}</dd>
                </template>
              </dl>
            </div>
          </div>
        </section>

        <!-- 2. Tamaño -->
        <section id="tamano" class="scroll-mt-44 pt-20 lg:pt-24">
          <button class="flex w-full items-center justify-between text-left md:pointer-events-none" :aria-expanded="abierta('tamano')" @click="alternarSec('tamano')"><h2 class="titulo-seccion">Tamaño y usabilidad urbana</h2></button>
          <div v-show="abierta('tamano')" class="mt-8 grid gap-6">
            <HuellaComparador :autos="huella" />
            <div class="grid gap-6 lg:grid-cols-3">
              <div class="tarjeta p-6">
                <h3 class="text-xl">Índice Rompemuelle</h3>
                <p class="mt-3 text-2xl font-bold uppercase text-tinta">{{ d.tamano.rompemuelle.etiqueta }}</p>
                <p class="text-sm text-tenue num">Despeje {{ d.tamano.rompemuelle.despeje_mm }} mm · con carga ≈ {{ d.tamano.rompemuelle.despeje_con_carga_mm }} mm <BadgeEstimado /></p>
                <label class="mt-4 block text-sm">Simular tope: <strong class="num">{{ tope }} mm</strong><input v-model.number="tope" type="range" min="100" max="150" step="10" class="w-full" /></label>
                <p class="mt-2 text-sm">
                  {{ d.tamano.rompemuelle.despeje_con_carga_mm - tope >= 30 ? 'Pasa con holgura.' : d.tamano.rompemuelle.despeje_con_carga_mm - tope >= 0 ? 'Pasa justo: entra en diagonal y despacio.' : 'Probablemente raspa con carga.' }}
                  <span class="text-tenue num">(margen {{ d.tamano.rompemuelle.despeje_con_carga_mm - tope }} mm)</span>
                </p>
              </div>
              <div class="tarjeta p-6">
                <h3 class="text-xl">Índice de Garaje</h3>
                <p class="mt-3 text-2xl font-bold uppercase text-tinta">{{ d.tamano.garaje.etiqueta }}</p>
                <div class="mt-3 grid grid-cols-2 gap-2 text-sm">
                  <label>Largo plaza (mm)<input v-model.number="plaza.largo" class="campo mt-1 num" inputmode="numeric" /></label>
                  <label>Ancho plaza (mm)<input v-model.number="plaza.ancho" class="campo mt-1 num" inputmode="numeric" /></label>
                </div>
                <p v-if="garajeUsuario" class="mt-3 text-sm num">Holgura longitudinal: <strong>{{ f.numero(garajeUsuario.holgura) }} mm</strong> · Espacio para abrir puertas: <strong>{{ f.numero(garajeUsuario.lateral) }} mm por lado</strong></p>
                <p class="mt-2 text-sm">Radio de giro: <strong class="num">{{ f.numero(d.tamano.radio_giro_metros, 1) }} m</strong> — {{ d.tamano.radio_giro_metros <= 5.2 ? 'gira con facilidad en rampas de parqueadero' : d.tamano.radio_giro_metros <= 5.7 ? 'requiere una maniobra en rampas cerradas' : 'exige varias maniobras en rampas estrechas' }}.</p>
              </div>
              <div class="tarjeta p-6">
                <h3 class="text-xl">Baúl en objetos <BadgeEstimado texto="Equivalencia aproximada por volumen." /></h3>
                <p class="mt-2 text-sm text-tenue num">{{ f.numero(d.tamano.medidas.capacidad_baul_litros) }} L · abatido {{ f.numero(d.tamano.medidas.capacidad_baul_abatido_litros) }} L</p>
                <ul class="mt-4 grid text-sm"><li v-for="o in d.tamano.baul_objetos" :key="o.objeto" class="flex justify-between border-b border-linea py-2.5"><span>{{ o.objeto }}</span><strong class="num">{{ o.cantidad }}</strong></li></ul>
                <p v-if="d.tamano.comodidad_trasera" class="mt-3 text-sm">Plazas traseras: <strong>{{ d.tamano.comodidad_trasera.etiqueta }}</strong> <BadgeEstimado /></p>
              </div>
            </div>
            <div class="tarjeta overflow-x-auto p-6">
              <h3 class="text-xl">Medidas</h3>
              <dl class="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-4">
                <template v-for="[k, et, u] in ([['largo_mm', 'Largo', 'mm'], ['ancho_sin_espejos_mm', 'Ancho sin espejos', 'mm'], ['ancho_con_espejos_mm', 'Ancho con espejos', 'mm'], ['alto_mm', 'Alto', 'mm'], ['distancia_entre_ejes_mm', 'Entre ejes', 'mm'], ['voladizo_delantero_mm', 'Voladizo delantero', 'mm'], ['voladizo_trasero_mm', 'Voladizo trasero', 'mm'], ['distancia_libre_suelo_mm', 'Despeje', 'mm'], ['peso_vacio_kg', 'Peso vacío', 'kg'], ['capacidad_carga_kg', 'Carga útil', 'kg'], ['angulo_ataque_deg', 'Ángulo de ataque', '°'], ['angulo_ventral_deg', 'Ángulo ventral', '°'], ['angulo_salida_deg', 'Ángulo de salida', '°']] as const)" :key="k">
                  <template v-if="d.tamano.medidas[k] != null"><dt class="text-tenue">{{ et }}</dt><dd class="num">{{ f.numero(d.tamano.medidas[k]) }} {{ u }}<BadgeEstimado v-if="est(k)" /></dd></template>
                </template>
              </dl>
            </div>
          </div>
        </section>

        <!-- 3. Precio -->
        <section id="precio" class="scroll-mt-44 pt-20 lg:pt-24">
          <button class="flex w-full items-center justify-between text-left md:pointer-events-none" :aria-expanded="abierta('precio')" @click="alternarSec('precio')"><h2 class="titulo-seccion">Precio, financiación y reventa</h2></button>
          <div v-show="abierta('precio')" class="mt-8 grid gap-6 lg:grid-cols-2">
            <div class="tarjeta p-6">
              <h3 class="text-xl">Puesta en calle en {{ d.ciudad.nombre }}</h3>
              <table class="mt-3 w-full text-sm num">
                <tbody>
                  <tr><td class="py-1 text-tenue">Precio base (vitrina)</td><td class="text-right">{{ f.dinero(d.precio.puesta_en_calle.precio_base_cop) }}</td></tr>
                  <tr><td class="py-1 text-tenue">SOAT ({{ d.precio.puesta_en_calle.soat.clase }}, {{ d.precio.puesta_en_calle.soat.rango_cc }})</td><td class="text-right">{{ f.dinero(d.precio.puesta_en_calle.soat.total_cop) }}</td></tr>
                  <tr><td class="py-1 pl-4 text-xs text-tenue">Prima + contribución ADRES + RUNT</td><td class="text-right text-xs text-tenue">{{ f.cop(d.precio.puesta_en_calle.soat.prima_cop) }} + {{ f.cop(d.precio.puesta_en_calle.soat.contribucion_adres_cop) }} + {{ f.cop(d.precio.puesta_en_calle.soat.tasa_runt_cop) }}</td></tr>
                  <tr><td class="py-1 text-tenue">Matrícula, placas y RUNT<BadgeEstimado v-if="d.precio.puesta_en_calle.matricula.estado_derechos === 'estimado'" /></td><td class="text-right">{{ f.dinero(d.precio.puesta_en_calle.matricula.derechos_matricula_placas_runt_cop) }}</td></tr>
                  <tr><td class="py-1 text-tenue">Impuesto vehicular proporcional ({{ d.precio.puesta_en_calle.matricula.meses_restantes }} meses, {{ f.pct(d.precio.puesta_en_calle.matricula.impuesto_tarifa) }})</td><td class="text-right">{{ f.dinero(d.precio.puesta_en_calle.matricula.impuesto_proporcional_cop) }}</td></tr>
                  <tr class="border-t border-tinta text-base text-tinta"><td class="pt-3 font-bold">{{ d.precio.puesta_en_calle.etiqueta_total }}</td><td class="pt-3 text-right font-bold">{{ f.dinero(d.precio.puesta_en_calle.total_cop) }}</td></tr>
                </tbody>
              </table>
              <p class="mt-2 text-xs text-tenue">SOAT: tarifas {{ d.precio.puesta_en_calle.soat.vigencia }} (Superfinanciera). {{ d.precio.puesta_en_calle.usado ? `Valor de usado estimado a ${f.fecha(d.cabecera.fecha_precio)}: no incluye alistamiento de concesionario y el SOAT usa la tarifa por antigüedad` : `Precio de vitrina ${f.fecha(d.cabecera.fecha_precio)}` }}; TRM de referencia {{ f.numero(d.cabecera.trm_referencia, 2) }}.</p>
            </div>
            <div class="tarjeta p-6">
              <h3 class="text-xl">Simulador de crédito</h3>
              <div class="mt-4 grid grid-cols-3 gap-3 text-sm">
                <label>Cuota inicial %<input v-model.number="credito.inicialPct" type="number" min="0" max="90" class="campo mt-1 num" /></label>
                <label>Plazo (meses)<input v-model.number="credito.plazo" type="number" min="12" max="84" step="12" class="campo mt-1 num" /></label>
                <label>Tasa E.A. %<input v-model.number="credito.tasa" type="number" min="0" max="40" step="0.1" class="campo mt-1 num" /></label>
              </div>
              <dl v-if="sim" class="lista-datos mt-4 items-end num">
                <dt class="text-tenue">Cuota mensual (con seguro de vida)</dt><dd class="text-right text-xl font-bold">{{ f.dinero(sim.cuota_mensual_con_seguros_cop) }}</dd>
                <dt class="text-tenue">Total intereses</dt><dd class="text-right">{{ f.dinero(sim.total_intereses_cop) }}</dd>
                <dt class="text-tenue">Ingreso mínimo recomendado</dt><dd class="text-right">{{ f.dinero(sim.ingreso_minimo_recomendado_cop) }}</dd>
              </dl>
              <p v-if="sim?.supera_usura" class="mt-2 text-xs text-roja">La tasa supera la usura vigente ({{ f.pct(sim.tasa_usura_ea) }}).</p>
              <p class="mt-2 text-xs text-tenue">Estimado, no es una oferta de crédito. <RouterLink to="/herramientas/credito" class="underline">Tres escenarios y tabla de amortización</RouterLink></p>
              <h3 class="mt-6 text-xl">Seguro estimado</h3>
              <p class="mt-1 text-sm num">SOAT anual {{ f.dinero(d.precio.soat_anual_cop) }} · Todo riesgo {{ f.dinero(d.precio.seguro.prima_anual_min_cop) }} – {{ f.dinero(d.precio.seguro.prima_anual_max_cop) }} al año</p>
              <p class="text-xs text-tenue">{{ d.precio.seguro.aviso }}</p>
            </div>
            <div class="tarjeta p-5 lg:col-span-2">
              <h3 class="text-xl">Depreciación y valor de reventa <BadgeEstimado /></h3>
              <p class="mt-1 text-sm">Pierdes aproximadamente <strong class="num">{{ f.dinero(d.precio.reventa.perdida_anual_aprox_cop) }}</strong> al año durante los primeros 5 años · {{ d.precio.reventa.etiqueta }}</p>
              <GraficoLineas class="mt-4" :titulo="`Valor estimado del ${d.nombre}`" :series="serieReventa" etiqueta-x="años" :formato-y="(y: number) => f.millones(y)" />
              <ul class="mt-6 grid gap-px border border-linea bg-linea text-sm num sm:grid-cols-2 lg:grid-cols-4">
                <li v-for="p in d.precio.reventa.puntos" :key="p.anio" class="bg-suave px-4 py-3">{{ p.anio }} año{{ p.anio > 1 ? 's' : '' }}: <strong>{{ f.dinero(p.valor_cop) }}</strong> <span class="text-tenue">({{ Math.round(p.retencion * 100) }}%)</span></li>
              </ul>
            </div>
          </div>
        </section>

        <!-- 4. Costo -->
        <section id="costo" class="scroll-mt-44 pt-20 lg:pt-24">
          <button class="flex w-full items-center justify-between text-left md:pointer-events-none" :aria-expanded="abierta('costo')" @click="alternarSec('costo')"><h2 class="titulo-seccion">Costo de tenerlo</h2></button>
          <div v-show="abierta('costo')" class="mt-8 grid gap-6 lg:grid-cols-2">
            <div class="tarjeta p-6">
              <h3 class="text-xl">Consumo</h3>
              <div class="mt-3 flex gap-1.5" role="group" aria-label="Unidad de consumo">
                <button :class="['chip min-h-[32px] text-xs', aj.unidadConsumo === 'kml' ? 'chip-activo' : '']" @click="aj.unidadConsumo = 'kml'; aj.guardar()">km/l</button>
                <button :class="['chip min-h-[32px] text-xs', aj.unidadConsumo === 'kmgal' ? 'chip-activo' : '']" @click="aj.unidadConsumo = 'kmgal'; aj.guardar()">km/gal</button>
              </div>
              <dl class="lista-datos mt-4 num">
                <template v-if="d.costo.consumo.consumo_mixto_kml">
                  <dt class="text-tenue">Ciudad</dt><dd class="text-right">{{ f.consumo(d.costo.consumo.consumo_ciudad_kml) }}<BadgeEstimado /></dd>
                  <dt class="text-tenue">Carretera</dt><dd class="text-right">{{ f.consumo(d.costo.consumo.consumo_carretera_kml) }}<BadgeEstimado /></dd>
                  <dt class="text-tenue">Mixto ({{ d.costo.consumo.ciclo_homologacion }})</dt><dd class="text-right">{{ f.consumo(d.costo.consumo.consumo_mixto_kml) }}<BadgeEstimado v-if="est('consumo_mixto_kml')" /></dd>
                  <dt class="!text-tinta">Real estimado</dt><dd class="text-right font-semibold">{{ f.consumo(d.costo.consumo.consumo_real_estimado_kml) }}<BadgeEstimado /></dd>
                </template>
                <template v-if="d.costo.consumo.consumo_kwh_100km"><dt class="text-tenue">Eléctrico</dt><dd class="text-right">{{ f.numero(d.costo.consumo.consumo_kwh_100km, 1) }} kWh/100 km</dd></template>
                <dt class="text-tenue">Autonomía ({{ d.costo.consumo.autonomia_ciclo }})</dt><dd class="text-right">{{ f.numero(d.costo.consumo.autonomia_estimada_km) }} km</dd>
              </dl>
              <label class="mt-4 block text-sm">Kilómetros al mes: <strong class="num">{{ f.numero(kmMes) }}</strong><input v-model.number="kmMes" type="range" min="200" max="5000" step="50" class="w-full" /></label>
              <p class="mt-1 text-sm">Gasto mensual en {{ d.costo.energia.fuente_energia === 'electricidad' ? 'electricidad' : `gasolina ${d.costo.energia.fuente_energia}` }} en {{ d.ciudad.nombre }}: <strong class="num">{{ f.dinero(energiaMensual) }}</strong></p>
              <h3 class="mt-6 text-xl">Mantenimiento <BadgeEstimado /></h3>
              <dl class="lista-datos mt-3 num">
                <dt class="text-tenue">Nivel de costo</dt><dd class="text-right">{{ d.costo.mantenimiento.nivel_costo_mantenimiento }}</dd>
                <dt class="text-tenue">Primeros 60.000 km</dt><dd class="text-right">{{ f.dinero(d.costo.mantenimiento.costo_primeros_60000km_cop) }}</dd>
                <dt class="text-tenue">Estimado anual (15.000 km)</dt><dd class="text-right">{{ f.dinero(d.costo.mantenimiento.costo_mantenimiento_anual_cop) }}</dd>
              </dl>
              <h3 class="mt-6 text-xl">Pico y placa en {{ d.ciudad.nombre }}</h3>
              <p class="mt-1 text-sm">{{ d.costo.pico_y_placa.exento ? 'Exento según la norma registrada.' : 'Sin exención: aplica la restricción.' }} {{ d.costo.pico_y_placa.regla }}</p>
              <p class="text-xs text-tenue">{{ d.costo.pico_y_placa.nota_exencion }} {{ d.costo.pico_y_placa.aviso }}</p>
            </div>
            <div class="tarjeta p-6">
              <h3 class="text-xl">Costo total a 5 años <BadgeEstimado /></h3>
              <p class="cifra mt-3 lg:text-display-md">{{ f.dinero(d.costo.tco5.costo_total_neto_cop) }}</p>
              <p class="text-sm text-tenue num">{{ f.dinero(d.costo.tco5.costo_por_mes_cop) }} al mes · {{ f.dinero(d.costo.tco5.costo_por_km_cop) }} por km · ya descontada la reventa ({{ f.dinero(d.costo.tco5.valor_reventa_cop) }})</p>
              <BarraApilada class="mt-6" :componentes="tcoComp" :formato="f.dinero" titulo="Componentes del costo total a 5 años" />
              <RouterLink :to="`/herramientas/costo-total?id=${d.id}`" class="enlace-texto mt-6">Ajustar kilómetros, horizonte y financiación</RouterLink>
            </div>
          </div>
        </section>

        <!-- 5. Fiabilidad -->
        <section id="fiabilidad" class="scroll-mt-44 pt-20 lg:pt-24">
          <button class="flex w-full items-center justify-between text-left md:pointer-events-none" :aria-expanded="abierta('fiabilidad')" @click="alternarSec('fiabilidad')"><h2 class="titulo-seccion">Fiabilidad y review honesta</h2></button>
          <div v-show="abierta('fiabilidad')" class="tarjeta mt-8 grid gap-8 p-6 md:grid-cols-[auto_1fr] lg:p-10">
            <MedidorFiabilidad :puntaje="d.fiabilidad.puntaje" :etiqueta="d.fiabilidad.etiqueta" />
            <div>
              <AlertaBanner :alertas="d.alertas" />
              <p class="mt-3 leading-relaxed">{{ d.fiabilidad.veredicto }}</p>
              <h3 class="etiqueta mt-8 !text-tinta">Las fallas más graves</h3>
              <ul class="mt-3 grid text-sm">
                <li v-for="fa in d.fiabilidad.fallas_graves" :key="fa.componente" class="border-b border-linea py-3"><strong>{{ fa.componente }}</strong> ({{ fa.severidad }}): {{ fa.descripcion }}</li>
              </ul>
              <p v-if="d.fiabilidad.recalls.length" class="mt-3 text-sm"><strong>Recalls y campañas:</strong> {{ d.fiabilidad.recalls.map((r: any) => r.titulo).join(' · ') }}</p>
              <RouterLink :to="`/reviews/${d.slug}`" class="boton-primario mt-8">Ver review completa</RouterLink>
            </div>
          </div>
        </section>

        <!-- 6. Versiones -->
        <section id="versiones" class="scroll-mt-44 pt-20 lg:pt-24">
          <button class="flex w-full items-center justify-between text-left md:pointer-events-none" :aria-expanded="abierta('versiones')" @click="alternarSec('versiones')"><h2 class="titulo-seccion">Versiones, historial y rivales</h2></button>
          <div v-show="abierta('versiones')" class="mt-8 grid gap-12">
            <div v-if="d.versiones.length">
              <h3 class="text-xl">Otras versiones y años</h3>
              <table class="mt-3 w-full text-sm">
                <thead><tr class="text-left text-tenue"><th class="py-2 font-normal">Versión</th><th class="font-normal">Año</th><th class="text-right font-normal">Precio base</th><th class="text-right font-normal">Diferencia</th></tr></thead>
                <tbody class="num">
                  <tr v-for="o in d.versiones" :key="o.id" class="border-t border-linea">
                    <td class="py-2"><RouterLink :to="`/vehiculo/${o.slug}`" class="hover:underline">{{ o.version }}</RouterLink></td><td>{{ o.anio }}</td>
                    <td class="text-right">{{ f.dinero(o.precio_base_cop) }}</td>
                    <td :class="['text-right', o.precio_base_cop > d.cabecera.precio_base_cop ? 'text-tinta' : 'text-mejor']">{{ o.precio_base_cop > d.cabecera.precio_base_cop ? '+' : '' }}{{ f.dinero(o.precio_base_cop - d.cabecera.precio_base_cop) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="d.actualizaciones.length">
              <h3 class="text-xl">Historial de actualizaciones</h3>
              <ul class="mt-2 grid gap-1 text-sm"><li v-for="a in d.actualizaciones" :key="a.id"><RouterLink :to="`/actualizados#act-${a.id}`" class="hover:underline">{{ a.titulo }}</RouterLink> · <span class="text-tenue">{{ a.vale_la_pena }}</span></li></ul>
            </div>
            <div>
              <h3 class="text-xl">Rivales directos</h3>
              <div class="mt-4 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                <div v-for="r in d.rivales.slice(0, 3)" :key="r.id" class="grid grid-rows-[1fr_auto] gap-3">
                  <TarjetaVehiculo :v="r" />
                  <button class="boton-secundario" @click="comp.agregar(d.id); comp.agregar(r.id); $router.push({ path: '/comparador', query: { ids: comp.ids.join(',') } })">Comparar contra este</button>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="mt-24 border-t border-linea pt-10 text-xs text-tenue">
          <h2 class="etiqueta !text-tinta">Fuentes de esta ficha</h2>
          <ul class="mt-2 grid gap-1"><li v-for="s in d.calidad_dato.fuentes.filter(Boolean)" :key="s.id"><a :href="s.url" class="underline" target="_blank" rel="noopener">{{ s.titulo }}</a> ({{ s.tipo }}, {{ f.fecha(s.fecha_consulta) }})</li></ul>
          <p class="mt-2">{{ T.avisoLegal }}</p>
        </section>
      </template>
    </EstadoCarga>
  </div>
</template>
