<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useHead } from '@unhead/vue'
import { useStorage } from '@vueuse/core'
import { ChevronDown, Pin, Plus, Printer, Share2, ShieldAlert, Trash2, X } from 'lucide-vue-next'
import type { Paginado, Tarjeta } from '@/lib/tipos'
import { api, FalloApi } from '@/lib/api'
import { useAjustes } from '@/stores/ajustes'
import { useComparador, MAX_COMPARAR } from '@/stores/comparador'
import { useFormato } from '@/composables/useFormato'
import { T } from '@/lib/textos'
import BarraFinanciera from '@/components/BarraFinanciera.vue'
import SelectorCascada from '@/components/SelectorCascada.vue'
import HuellaComparador from '@/components/HuellaComparador.vue'
import PanelReview from '@/components/PanelReview.vue'
import ImagenVehiculo from '@/components/ImagenVehiculo.vue'
import GraficoLineas from '@/components/GraficoLineas.vue'

useHead({ title: 'Comparador' })
const route = useRoute()
const router = useRouter()
const aj = useAjustes()
const comp = useComparador()
const f = useFormato()

interface Fila { clave: string; etiqueta: string; regla: string; unidad: string; valores: unknown[]; ganadores: number[]; aviso: string | null; delta: (number | null)[] | null; diferente: boolean }
interface Resultado {
  vehiculos: any[]
  categorias: { categoria: string; filas: Fila[] }[]
  marcador: Record<string, { total: number; por_categoria: Record<string, number> }>
  puntajes: { id: number; puntaje: number; perfil: string; aportes: { dimension: string; peso: number; valor_normalizado: number; aporte: number }[]; penalizacion_alerta_roja: number }[]
  reventa: { id: number; puntos: { anio: number; valor_cop: number }[] }[]
  ciudad: string
}
const datos = ref<Resultado | null>(null)
const cargando = ref(false)
const error = ref<string | null>(null)
const soloDiferencias = ref(false)
const colapsadas = useStorage<string[]>('av-categorias-colapsadas', [])
const slots = ref(2)
const resena = ref<string | null>(null)
const explicar = ref<number | null>(null)
const PERFILES = [
  { v: 'ahorrador', t: 'Ahorrador' }, { v: 'familiar', t: 'Familiar' }, { v: 'ciudad', t: 'Ciudad' },
  { v: 'carretera', t: 'Carretera y viajes' }, { v: 'rendimiento', t: 'Rendimiento' }, { v: 'fiabilidad', t: 'Fiabilidad ante todo' },
]
const DIM: Record<string, string> = { costo: 'Costo', eficiencia: 'Eficiencia', espacio: 'Espacio', desempeno: 'Desempeño', fiabilidad: 'Fiabilidad', seguridad: 'Seguridad', urbano: 'Uso urbano', equipamiento: 'Equipamiento', reventa: 'Reventa' }

function idsDeUrl(): number[] {
  return String(route.query.ids || '').split(',').map(Number).filter((n) => Number.isInteger(n) && n > 0).slice(0, MAX_COMPARAR)
}
onMounted(() => {
  const ids = idsDeUrl()
  if (ids.length) comp.reemplazar(ids)
  if (route.query.moneda === 'USD' || route.query.moneda === 'COP') aj.moneda = route.query.moneda
  if (route.query.trm) aj.fijarTrm(Number(route.query.trm))
  if (route.query.perfil) aj.perfil = String(route.query.perfil)
  slots.value = Math.max(2, comp.ids.length)
})
watch(() => [comp.ids.slice(), aj.ciudad, aj.perfil, comp.referencia, aj.trm], cargar, { deep: true })

async function cargar() {
  router.replace({ query: { ...(comp.ids.length ? { ids: comp.ids.join(',') } : {}), moneda: aj.moneda, trm: String(Math.round(aj.trm)), perfil: aj.perfil } })
  if (comp.ids.length < 2) { datos.value = null; return }
  cargando.value = true
  error.value = null
  try {
    datos.value = await api.post<Resultado>('/comparar', { ids: comp.ids, moneda: aj.moneda, trm: aj.trm, ciudad: aj.ciudad, perfil: aj.perfil, referencia_id: comp.referencia })
  } catch (e) {
    error.value = e instanceof FalloApi ? e.cuerpo.mensaje : String(e)
  } finally {
    cargando.value = false
  }
}
onMounted(cargar)

function elegido(id: number) {
  comp.agregar(id)
  slots.value = Math.max(slots.value, comp.ids.length)
}
const vacios = computed(() => Math.max(0, slots.value - comp.ids.length))

/** Tarjetas de los autos ya elegidos, en el orden de la selección (se muestran arriba aunque haya uno solo). */
const elegidos = ref<Tarjeta[]>([])
watch(() => comp.ids.slice(), async (ids) => {
  if (!ids.length) { elegidos.value = []; return }
  try {
    const r = await api.get<Paginado<Tarjeta>>('/vehiculos', { ids, size: ids.length })
    elegidos.value = ids.map((id) => r.resultados.find((x) => x.id === id)).filter((x): x is Tarjeta => !!x)
  } catch { /* la tabla muestra el error */ }
}, { immediate: true })
const v = computed(() => datos.value?.vehiculos || [])
function formatear(fila: Fila, x: unknown): string {
  if (x === null || x === undefined) return '—'
  if (typeof x === 'boolean') return x ? 'Sí' : 'No'
  if (typeof x !== 'number') return String(x)
  if (fila.unidad === 'cop') return f.dinero(x)
  if (fila.unidad === '%') return `${f.numero(x, 1)} %`
  if (['km/l'].includes(fila.unidad)) return f.consumo(x)
  if (fila.clave === 'indice_garaje_nivel' || fila.clave === 'indice_rompemuelle_nivel') return ['', 'Nivel 1', 'Nivel 2', 'Nivel 3', 'Nivel 4'][x] || String(x)
  const dec = Number.isInteger(x) ? 0 : 1
  return `${f.numero(x, dec)}${fila.unidad ? ` ${fila.unidad}` : ''}`
}
function etiquetaNivel(fila: Fila, i: number): string | null {
  if (fila.clave === 'indice_garaje_nivel') return v.value[i]?.indice_garaje_etiqueta
  if (fila.clave === 'indice_rompemuelle_nivel') return v.value[i]?.indice_rompemuelle_etiqueta
  return null
}
const visible = (fila: Fila) => !soloDiferencias.value || fila.diferente
const alternarCat = (c: string) => (colapsadas.value = colapsadas.value.includes(c) ? colapsadas.value.filter((x) => x !== c) : [...colapsadas.value, c])
const autosHuella = computed(() => v.value.map((x) => ({ ...x, nombre: `${x.marca} ${x.modelo} ${x.anio}` })))
const seriesReventa = computed(() => (datos.value?.reventa || []).map((r) => ({
  nombre: (() => { const x = v.value.find((y) => y.id === r.id); return x ? `${x.marca} ${x.modelo}` : String(r.id) })(),
  puntos: [{ x: 0, y: v.value.find((y) => y.id === r.id)?.precio_base_cop || 0 }, ...r.puntos.map((p) => ({ x: p.anio, y: p.valor_cop }))],
})))
const copiado = ref(false)
async function compartir() { try { await navigator.clipboard.writeText(location.href); copiado.value = true; setTimeout(() => (copiado.value = false), 2000) } catch { /* */ } }
const imprimir = () => window.print()
const puntajeDe = (id: number) => datos.value?.puntajes.find((p) => p.id === id)
</script>

<template>
  <BarraFinanciera />
  <div class="contenedor pagina">
    <div class="flex flex-wrap items-end gap-x-6 gap-y-4">
      <h1 class="titulo-pagina">Comparador</h1>
      <div class="grid w-full grid-cols-2 items-center gap-3 no-imprimir sm:ml-auto sm:flex sm:w-auto sm:flex-wrap">
        <label class="col-span-2 flex items-center gap-2 text-sm sm:col-span-1">Perfil
          <select v-model="aj.perfil" class="campo-mini min-h-[44px] flex-1 px-3" @change="aj.guardar()"><option v-for="p in PERFILES" :key="p.v" :value="p.v">{{ p.t }}</option></select>
        </label>
        <label class="col-span-2 flex min-h-[44px] items-center gap-2 text-sm sm:col-span-1"><input v-model="soloDiferencias" type="checkbox" class="h-4 w-4" /> Mostrar solo diferencias</label>
        <button class="boton-secundario px-4 sm:px-5" @click="compartir"><Share2 class="h-4 w-4" aria-hidden="true" /> {{ copiado ? 'Copiado' : 'Compartir' }}</button>
        <button class="boton-secundario px-4 sm:px-5" @click="imprimir"><Printer class="h-4 w-4" aria-hidden="true" /> PDF</button>
      </div>
    </div>

    <!-- Selección -->
    <div class="mt-10 grid grid-cols-2 gap-3 pb-2 no-imprimir sm:flex sm:snap-x sm:gap-4 sm:overflow-x-auto" aria-label="Vehículos elegidos">
      <article v-for="(x, i) in elegidos" :key="x.id" class="tarjeta relative min-w-0 shrink-0 snap-start sm:w-64">
        <ImagenVehiculo :medidas="x" :nombre="`${x.marca} ${x.modelo}`" :imagen-id="x.imagen_id" />
        <div class="p-3 sm:p-4">
          <p class="etiqueta truncate">Vehículo {{ i + 1 }} · {{ x.anio }}</p>
          <RouterLink :to="`/vehiculo/${x.slug}`" class="mt-1 block truncate text-base font-bold text-tinta hover:underline">{{ x.marca }} {{ x.modelo }}</RouterLink>
          <p class="truncate text-xs text-tenue">{{ x.version }}</p>
        </div>
        <button class="absolute right-2 top-2 grid h-9 w-9 place-items-center rounded-full bg-black/60 text-white transition-colors hover:bg-black/80" :aria-label="`Quitar ${x.marca} ${x.modelo} ${x.version}`" @click="comp.quitar(x.id)"><X class="h-4 w-4" aria-hidden="true" /></button>
      </article>
      <div v-for="n in vacios" :key="`s${n}`" class="tarjeta col-span-2 shrink-0 snap-start p-5 sm:w-64">
        <p class="etiqueta mb-4 !text-tinta">Vehículo {{ comp.ids.length + n }}</p>
        <SelectorCascada @elegido="elegido" />
      </div>
      <button
        class="grid min-h-[160px] shrink-0 snap-start place-items-center border border-dashed sm:min-h-[200px] sm:w-48 border-linea p-6 text-xs font-bold uppercase tracking-maquinado text-tenue transition-colors hover:border-tinta hover:text-tinta disabled:pointer-events-none disabled:opacity-40"
        :disabled="comp.ids.length + vacios >= MAX_COMPARAR"
        :title="comp.ids.length + vacios >= MAX_COMPARAR ? T.maximo10 : ''"
        @click="slots++"
      ><span class="flex flex-col items-center gap-4 text-center leading-relaxed"><Plus class="h-6 w-6" aria-hidden="true" /> Añadir vehículo para comparar</span></button>
    </div>

    <p v-if="comp.ids.length < 2" class="mt-10 border-l-4 border-linea pl-4 text-tenue">Elige al menos dos vehículos para ver la comparación.</p>
    <div v-if="cargando && !datos" class="esqueleto mt-8 h-96" aria-busy="true" />
    <p v-if="error" class="mt-8 text-roja" role="alert">{{ error }}</p>

    <template v-if="datos && v.length >= 2">
      <!-- Marcador -->
      <section class="mt-20" aria-labelledby="marcador">
        <h2 id="marcador" class="text-display-sm">Marcador y Puntaje MiProximoCarro</h2>
        <div class="mt-8 flex snap-x gap-6 overflow-x-auto pb-2">
          <div v-for="(x, i) in v" :key="x.id" class="celda-dato w-64 shrink-0 snap-start border border-linea">
            <p class="etiqueta truncate">{{ x.marca }} {{ x.modelo }}</p>
            <p class="mt-3 text-display-md text-tinta num">{{ puntajeDe(x.id)?.puntaje }}<span class="text-base font-light tracking-normal text-tenue">/100</span></p>
            <p class="text-sm text-tenue num">{{ datos.marcador[x.id]?.total || 0 }} filas ganadas</p>
            <button class="mt-4 text-left text-xs underline hover:text-tinta" :aria-expanded="explicar === i" @click="explicar = explicar === i ? null : i">Ver qué sumó y qué restó</button>
            <ul v-if="explicar === i" class="mt-3 grid gap-1.5 border-t border-linea pt-3 text-xs">
              <li v-for="a in puntajeDe(x.id)?.aportes" :key="a.dimension" class="flex justify-between"><span>{{ DIM[a.dimension] }} ({{ Math.round(a.peso * 100) }}%)</span><span class="num">+{{ f.numero(a.aporte, 1) }}</span></li>
              <li v-if="puntajeDe(x.id)?.penalizacion_alerta_roja" class="flex justify-between text-roja"><span>Alerta roja</span><span class="num">−{{ f.numero(puntajeDe(x.id)!.penalizacion_alerta_roja, 1) }}</span></li>
            </ul>
          </div>
        </div>
      </section>

      <HuellaComparador class="mt-20" :autos="autosHuella" />

      <!-- Tabla -->
      <section class="mt-20" aria-labelledby="tabla-titulo">
        <h2 id="tabla-titulo" class="sr-only">Tabla comparativa</h2>
        <div class="max-h-[80vh] snap-x overflow-auto border border-linea">
          <table class="min-w-full border-separate border-spacing-0 text-sm" :aria-busy="cargando">
            <thead class="sticky top-0 z-20 bg-superficie">
              <tr>
                <th scope="col" class="sticky left-0 z-30 w-28 min-w-[7rem] border-b sm:w-48 sm:min-w-[11rem] border-linea bg-superficie p-3 text-left align-bottom normal-case">
                  <span class="etiqueta">{{ datos.ciudad }} · {{ aj.moneda }}</span>
                </th>
                <th v-for="x in v" :key="x.id" scope="col" class="min-w-[136px] snap-start border-b border-l sm:min-w-[220px] border-linea p-3 text-left align-top text-sm font-light normal-case tracking-normal text-cuerpo">
                  <ImagenVehiculo :medidas="x" :nombre="`${x.marca} ${x.modelo}`" :imagen-id="x.imagen_id" class="!aspect-[3/1]" />
                  <RouterLink :to="`/vehiculo/${x.slug}`" class="mt-3 block text-base font-bold text-tinta hover:underline">{{ x.marca }} {{ x.modelo }} {{ x.anio }}</RouterLink>
                  <p class="text-xs text-tenue">{{ x.version }}</p>
                  <p v-if="x.tiene_alerta_roja" class="insignia mt-2 flex bg-roja text-white"><ShieldAlert class="h-3.5 w-3.5" aria-hidden="true" /> Alerta roja de fiabilidad</p>
                  <div class="mt-3 flex flex-wrap gap-1.5 no-imprimir">
                    <button class="chip min-h-[32px] text-xs" @click="resena = x.slug">Ver Review Honesta</button>
                    <button :class="['chip min-h-[32px] text-xs', comp.referencia === x.id ? 'chip-activo' : '']" :aria-pressed="comp.referencia === x.id" @click="comp.referencia = comp.referencia === x.id ? null : x.id"><Pin class="h-3 w-3" aria-hidden="true" /> Referencia</button>
                    <button class="chip min-h-[32px] text-xs" :aria-label="`Quitar ${x.marca} ${x.modelo}`" @click="comp.quitar(x.id)"><Trash2 class="h-3 w-3" aria-hidden="true" /></button>
                  </div>
                </th>
              </tr>
            </thead>
            <tbody v-for="cat in datos.categorias" :key="cat.categoria">
              <tr>
                <th :colspan="v.length + 1" scope="colgroup" class="sticky left-0 border-b border-linea bg-papel p-0 text-left">
                  <button class="flex min-h-[48px] w-full items-center gap-2 px-3 text-sm font-bold uppercase tracking-maquinado text-tinta" :aria-expanded="!colapsadas.includes(cat.categoria)" @click="alternarCat(cat.categoria)">
                    <ChevronDown :class="['h-4 w-4 transition', colapsadas.includes(cat.categoria) ? '-rotate-90' : '']" aria-hidden="true" /> {{ cat.categoria }}
                    <span class="ml-2 hidden text-xs font-light normal-case tracking-normal text-tenue sm:inline">({{ v.map((x) => `${x.modelo}: ${datos!.marcador[x.id]?.por_categoria[cat.categoria] || 0}`).join(' · ') }})</span>
                  </button>
                </th>
              </tr>
              <template v-if="!colapsadas.includes(cat.categoria)">
                <tr v-for="fila in cat.filas.filter(visible)" :key="fila.clave" class="hover:bg-superficie">
                  <th scope="row" class="sticky left-0 z-10 border-b border-linea bg-suave p-2 text-left text-xs font-light text-tenue sm:p-3 sm:text-sm">
                    {{ fila.etiqueta }}
                    <span v-if="fila.aviso" class="mt-1 block text-xs text-ambar">{{ fila.aviso }}</span>
                  </th>
                  <td v-for="(x, i) in fila.valores" :key="i" :class="['border-b border-l border-linea p-3 text-right num', fila.ganadores.includes(v[i].id) ? 'font-bold text-tinta' : '']">
                    <span v-if="fila.ganadores.includes(v[i].id) && fila.ganadores.length < fila.valores.length" class="mr-2 inline-flex items-center gap-1 text-[10px] font-bold tracking-[1px] text-mejor">
                      <span class="h-2 w-2 rounded-full bg-mejor" aria-hidden="true" />{{ T.mejor }}
                    </span>
                    {{ etiquetaNivel(fila, i) || formatear(fila, x) }}
                    <span v-if="fila.delta && comp.referencia && v[i].id !== comp.referencia && fila.delta[i] !== null" :class="['block text-xs font-normal', (fila.delta[i] || 0) > 0 ? 'text-tinta' : 'text-tenue']">Δ {{ (fila.delta[i] || 0) > 0 ? '+' : '' }}{{ fila.unidad === 'cop' ? f.dinero(fila.delta[i]) : f.numero(fila.delta[i], 1) }}</span>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
        <p class="mt-3 text-xs tracking-[0.5px] text-apagado">MEJOR marca el mejor valor de cada fila (todos los empatados). Las filas informativas no tienen ganador. Costos con tarifas de {{ datos.ciudad }}; seguro, crédito y TCO son estimaciones.</p>
      </section>

      <section class="tarjeta mt-20 p-6 lg:p-8" aria-labelledby="reventa-titulo">
        <h2 id="reventa-titulo" class="text-2xl">Curva de valor residual</h2>
        <GraficoLineas class="mt-4" titulo="Valor estimado del vehículo por año" :series="seriesReventa" etiqueta-x="años" :formato-y="(y: number) => f.millones(y)" :formato-x="(x: number) => `${x}`" />
      </section>
    </template>
  </div>
  <PanelReview :slug="resena" @cerrar="resena = null" />
</template>
