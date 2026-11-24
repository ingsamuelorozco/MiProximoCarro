<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useHead } from '@unhead/vue'
import { useDebounceFn } from '@vueuse/core'
import { LayoutGrid, List, Search, SlidersHorizontal, Share2 } from 'lucide-vue-next'
import { api } from '@/lib/api'
import { useCarga } from '@/composables/useCarga'
import { useAjustes } from '@/stores/ajustes'
import { useFavoritos } from '@/stores/favoritos'
import EstadoCarga from '@/components/EstadoCarga.vue'
import TarjetaVehiculo from '@/components/TarjetaVehiculo.vue'
import TarjetaModelo from '@/components/TarjetaModelo.vue'
import SelectorMultiple from '@/components/SelectorMultiple.vue'
import type { Modelo, Paginado, PaginadoModelos, Tarjeta } from '@/lib/tipos'
import { formatoNumero } from '@/composables/useFormato'
import { OPC } from '@/lib/opciones'
import { useCatalogo } from '@/stores/catalogo'

useHead({ title: 'Buscar vehículo' })
const route = useRoute()
const router = useRouter()
const aj = useAjustes()
const fav = useFavoritos()
const catalogo = useCatalogo()
onMounted(() => catalogo.cargar())

const MULTI = ['marca', 'segmento', 'carroceria', 'combustible', 'transmision', 'traccion', 'adas', 'pais'] as const
const SIMPLE = ['q', 'precio_min', 'precio_max', 'anio_min', 'anio_max', 'plazas', 'despeje_min', 'baul_min', 'consumo_min', 'fiabilidad_min', 'sort', 'page'] as const
const ETIQUETAS: Record<(typeof MULTI)[number], string> = { marca: 'Marca', carroceria: 'Carrocería', segmento: 'Segmento', combustible: 'Combustible', transmision: 'Transmisión', traccion: 'Tracción', adas: 'ADAS incluidas', pais: 'País de origen' }
const ANIOS = Array.from({ length: 2026 - 2000 + 1 }, (_, i) => 2000 + i)
const PLAZAS = [2, 4, 5, 7, 8]
const DESPEJES = [150, 170, 190, 210, 230]
const BAULES = [300, 400, 500, 600, 800]
const CONSUMOS = [10, 12, 14, 16, 18, 20, 25]
const FIABILIDADES = [5, 6, 7, 8, 9]
type Filtros = Record<(typeof MULTI)[number], string[]> & Record<(typeof SIMPLE)[number], string>
function desdeUrl(): Filtros {
  const q = route.query
  const f = {} as Filtros
  MULTI.forEach((k) => (f[k] = ([] as string[]).concat((q[k] as string | string[]) || [])))
  SIMPLE.forEach((k) => (f[k] = (q[k] as string) || ''))
  if (!f.sort) f.sort = 'puntaje'
  return f
}
const filtros = ref<Filtros>(desdeUrl())
const vista = ref<'grid' | 'lista'>('grid')
const panel = ref(false)
const soloFavoritos = computed(() => route.query.favoritos === '1')

const ORDENES = [
  { v: 'puntaje', t: 'Puntaje MiProximoCarro' }, { v: 'precio_calle', t: 'Precio en calle: menor' }, { v: 'precio_calle_desc', t: 'Precio en calle: mayor' },
  { v: 'potencia', t: 'Potencia' }, { v: 'consumo', t: 'Consumo' }, { v: 'fiabilidad', t: 'Fiabilidad' }, { v: 'despeje', t: 'Despeje' }, { v: 'recientes', t: 'Más recientes' },
]
const factorMoneda = computed(() => (aj.moneda === 'USD' ? aj.trm : 1))
/** Escalones de precio en la moneda elegida: millones de pesos o miles de dólares redondeados. */
const PRECIOS = computed(() => [40, 60, 80, 100, 130, 160, 200, 250, 300, 400, 500].map((m) => (aj.moneda === 'USD' ? Math.round((m * 1_000_000) / aj.trm / 1000) * 1000 : m * 1_000_000)))
const fmtPrecio = (v: number) => (aj.moneda === 'USD' ? `US$ ${formatoNumero(v / 1000)} mil` : `$${formatoNumero(v / 1_000_000)} M`)
/** Si la URL trae un valor que no está en los escalones (p. ej., desde la portada), se agrega para que el desplegable lo muestre. */
const conActual = (lista: number[], v: string) => (v && !lista.includes(Number(v)) ? [...lista, Number(v)].sort((a, b) => a - b) : lista)

const { datos, cargando, error, ejecutar } = useCarga(async () => {
  const p: Record<string, unknown> = { ...filtros.value, size: 24, page: Number(filtros.value.page) || 1 }
  for (const k of ['precio_min', 'precio_max'] as const) if (filtros.value[k]) p[k] = Number(filtros.value[k]) * factorMoneda.value
  // Favoritos son versiones concretas: se listan una a una. La búsqueda normal agrupa por modelo.
  if (soloFavoritos.value) {
    if (!fav.ids.length) return { total: 0, page: 1, size: 24, paginas: 0, resultados: [], sugerencia: 'Aún no tienes favoritos: marca el corazón en cualquier tarjeta.' } as Paginado<Tarjeta>
    p.ids = fav.ids
    return api.get<Paginado<Tarjeta>>('/vehiculos', p as never)
  }
  return api.get<PaginadoModelos>('/vehiculos/modelos', p as never)
})
const versiones = computed(() => (soloFavoritos.value ? (datos.value?.resultados as Tarjeta[] | undefined) ?? [] : []))
const modelos = computed(() => (soloFavoritos.value ? [] : (datos.value?.resultados as Modelo[] | undefined) ?? []))
const resumen = computed(() => {
  const d = datos.value
  if (!d) return ''
  if (soloFavoritos.value) return `${d.total} ${d.total === 1 ? 'versión' : 'versiones'}`
  const v = (d as PaginadoModelos).total_versiones ?? 0
  return `${d.total} ${d.total === 1 ? 'modelo' : 'modelos'} · ${v} ${v === 1 ? 'versión' : 'versiones'}`
})

function aUrl() {
  const q: Record<string, string | string[]> = {}
  for (const [k, v] of Object.entries(filtros.value)) if ((Array.isArray(v) && v.length) || (!Array.isArray(v) && v && !(k === 'sort' && v === 'puntaje'))) q[k] = v
  router.replace({ query: q })
}
const recargar = useDebounceFn(() => { filtros.value.page = ''; aUrl() }, 300)
watch(() => route.query, () => { filtros.value = desdeUrl(); ejecutar() })
onMounted(ejecutar)
const pagina = (n: number) => { filtros.value.page = String(n); aUrl() }
const copiado = ref(false)
async function compartir() { try { await navigator.clipboard.writeText(location.href); copiado.value = true; setTimeout(() => (copiado.value = false), 2000) } catch { /* sin portapapeles */ } }
const nFiltros = computed(() => MULTI.reduce((a, k) => a + filtros.value[k].length, 0) + SIMPLE.filter((k) => !['q', 'sort', 'page'].includes(k) && filtros.value[k]).length)
</script>

<template>
  <div class="contenedor pagina">
    <h1 class="titulo-pagina">{{ soloFavoritos ? 'Tus favoritos' : 'Buscar vehículo' }}</h1>
    <div class="mt-10 flex flex-wrap items-center gap-3">
      <label class="relative min-w-[16rem] flex-1">
        <span class="sr-only">Buscar por marca, modelo o versión</span>
        <Search class="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-tenue" aria-hidden="true" />
        <input v-model="filtros.q" type="search" class="campo pl-11" placeholder="Ej.: corolla cross, captiva, eléctrico…" @input="recargar" />
      </label>
      <button class="boton-secundario lg:hidden" :aria-expanded="panel" @click="panel = !panel"><SlidersHorizontal class="h-4 w-4" aria-hidden="true" /> Filtros ({{ nFiltros }})</button>
      <select v-model="filtros.sort" class="campo w-auto" aria-label="Ordenar por" @change="recargar"><option v-for="o in ORDENES" :key="o.v" :value="o.v">{{ o.t }}</option></select>
      <div class="flex" role="group" aria-label="Vista">
        <button :class="['grid h-12 w-12 place-items-center border border-linea transition-colors', vista === 'grid' ? 'border-tinta bg-tinta text-papel' : 'text-tenue hover:text-tinta']" aria-label="Cuadrícula" @click="vista = 'grid'"><LayoutGrid class="h-4 w-4" aria-hidden="true" /></button>
        <button :class="['-ml-px grid h-12 w-12 place-items-center border border-linea transition-colors', vista === 'lista' ? 'border-tinta bg-tinta text-papel' : 'text-tenue hover:text-tinta']" aria-label="Lista" @click="vista = 'lista'"><List class="h-4 w-4" aria-hidden="true" /></button>
      </div>
      <button class="boton-secundario" @click="compartir"><Share2 class="h-4 w-4" aria-hidden="true" /> {{ copiado ? 'Enlace copiado' : 'Compartir' }}</button>
    </div>

    <div class="mt-10 grid gap-10 lg:grid-cols-[18rem_1fr]">
      <aside :class="['grid content-start gap-5 text-sm lg:border-r lg:border-linea lg:pr-8', panel ? '' : 'hidden lg:grid']" aria-label="Filtros">
        <SelectorMultiple v-for="k in MULTI" :key="k" v-model="filtros[k]" :etiqueta="ETIQUETAS[k]" :opciones="k === 'marca' ? catalogo.marcas : OPC[k]" @cambio="recargar" />
        <fieldset>
          <legend class="etiqueta mb-2 !text-tinta">Precio base ({{ aj.moneda }})</legend>
          <div class="grid grid-cols-2 gap-2">
            <select v-model="filtros.precio_min" class="campo text-sm" aria-label="Precio base desde" @change="recargar">
              <option value="">Desde</option>
              <option v-for="o in conActual(PRECIOS, filtros.precio_min)" :key="o" :value="String(o)">{{ fmtPrecio(o) }}</option>
            </select>
            <select v-model="filtros.precio_max" class="campo text-sm" aria-label="Precio base hasta" @change="recargar">
              <option value="">Hasta</option>
              <option v-for="o in conActual(PRECIOS, filtros.precio_max)" :key="o" :value="String(o)">{{ fmtPrecio(o) }}</option>
            </select>
          </div>
        </fieldset>
        <fieldset>
          <legend class="etiqueta mb-2 !text-tinta">Año</legend>
          <div class="grid grid-cols-2 gap-2">
            <select v-model="filtros.anio_min" class="campo text-sm" aria-label="Año desde" @change="recargar">
              <option value="">Desde</option>
              <option v-for="o in conActual(ANIOS, filtros.anio_min)" :key="o" :value="String(o)">{{ o }}</option>
            </select>
            <select v-model="filtros.anio_max" class="campo text-sm" aria-label="Año hasta" @change="recargar">
              <option value="">Hasta</option>
              <option v-for="o in conActual(ANIOS, filtros.anio_max)" :key="o" :value="String(o)">{{ o }}</option>
            </select>
          </div>
        </fieldset>
        <label class="block">
          <span class="etiqueta mb-2 block !text-tinta">Plazas mínimas</span>
          <select v-model="filtros.plazas" class="campo text-sm" @change="recargar">
            <option value="">Cualquiera</option>
            <option v-for="o in conActual(PLAZAS, filtros.plazas)" :key="o" :value="String(o)">{{ o }} o más</option>
          </select>
        </label>
        <label class="block">
          <span class="etiqueta mb-2 block !text-tinta">Despeje mínimo</span>
          <select v-model="filtros.despeje_min" class="campo text-sm" @change="recargar">
            <option value="">Cualquiera</option>
            <option v-for="o in conActual(DESPEJES, filtros.despeje_min)" :key="o" :value="String(o)">{{ o }} mm o más</option>
          </select>
        </label>
        <label class="block">
          <span class="etiqueta mb-2 block !text-tinta">Baúl mínimo</span>
          <select v-model="filtros.baul_min" class="campo text-sm" @change="recargar">
            <option value="">Cualquiera</option>
            <option v-for="o in conActual(BAULES, filtros.baul_min)" :key="o" :value="String(o)">{{ o }} L o más</option>
          </select>
        </label>
        <label class="block">
          <span class="etiqueta mb-2 block !text-tinta">Consumo real mínimo</span>
          <select v-model="filtros.consumo_min" class="campo text-sm" @change="recargar">
            <option value="">Cualquiera</option>
            <option v-for="o in conActual(CONSUMOS, filtros.consumo_min)" :key="o" :value="String(o)">{{ o }} km/l o más</option>
          </select>
        </label>
        <label class="block">
          <span class="etiqueta mb-2 block !text-tinta">Fiabilidad mínima</span>
          <select v-model="filtros.fiabilidad_min" class="campo text-sm" @change="recargar">
            <option value="">Cualquiera</option>
            <option v-for="o in conActual(FIABILIDADES, filtros.fiabilidad_min)" :key="o" :value="String(o)">{{ o }} de 10 o más</option>
          </select>
        </label>
        <button class="boton-secundario" @click="router.replace({ query: {} })">Limpiar filtros</button>
      </aside>

      <section aria-live="polite">
        <p v-if="datos" class="etiqueta mb-6 num">{{ resumen }}</p>
        <EstadoCarga :cargando="cargando" :error="error" :vacio="!!datos && !datos.total" :filas="6" @reintentar="ejecutar">
          <template #vacio><p class="text-sm text-tenue">{{ datos?.sugerencia }}</p></template>
          <div :class="vista === 'grid' ? 'grid gap-6 sm:grid-cols-2 xl:grid-cols-3' : 'grid gap-6'">
            <TarjetaModelo v-for="m in modelos" :key="`${m.marca}|${m.modelo}`" :m="m" :lista="vista === 'lista'" />
            <TarjetaVehiculo v-for="v in versiones" :key="v.id" :v="v" :lista="vista === 'lista'" />
          </div>
          <nav v-if="datos && datos.paginas > 1" class="mt-12 flex flex-wrap justify-center gap-1.5" aria-label="Paginación">
            <button v-for="n in datos.paginas" :key="n" :class="['chip min-h-[44px] min-w-[44px] justify-center num', n === datos.page ? 'chip-activo' : '']" :aria-current="n === datos.page ? 'page' : undefined" @click="pagina(n)">{{ n }}</button>
          </nav>
        </EstadoCarga>
      </section>
    </div>
  </div>
</template>
