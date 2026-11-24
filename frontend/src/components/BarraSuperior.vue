<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { onClickOutside } from '@vueuse/core'
import { ChevronDown, Heart, Menu, Moon, Sun, X } from 'lucide-vue-next'
import MenuDesplegable from '@/components/MenuDesplegable.vue'
import { useAjustes } from '@/stores/ajustes'
import { useFavoritos } from '@/stores/favoritos'
import { formatoNumero } from '@/composables/useFormato'
import { T } from '@/lib/textos'

const aj = useAjustes()
const fav = useFavoritos()
const route = useRoute()
/** En la portada la barra flota transparente sobre el hero; en el resto queda fija arriba. */
const enInicio = computed(() => route.path === '/')
const lateralAbierto = ref(false)
const herramientasMovil = ref(false)
const ajustesAbierto = ref(false)
const ajustesRef = ref<HTMLElement | null>(null)
onClickOutside(ajustesRef, () => (ajustesAbierto.value = false))
watch(() => route.fullPath, () => { lateralAbierto.value = false; ajustesAbierto.value = false })

function cambiarTrm(e: Event) {
  const v = Number((e.target as HTMLInputElement).value.replace(/\./g, '').replace(',', '.'))
  aj.fijarTrm(Number.isFinite(v) && v > 0 ? v : null)
}
const vehiculos = [
  { to: '/buscar', texto: T.navCorto.buscar },
  { to: '/comparador', texto: T.navCorto.comparador },
  { to: '/actualizados', texto: T.navCorto.actualizados },
  { to: '/reviews', texto: T.navCorto.reviews },
]
const enVehiculos = computed(() => vehiculos.some((v) => route.path.startsWith(v.to)))
const vehiculosMovil = ref(false)
const herramientas = T.herramientas.map((h) => ({ to: h.ruta, texto: h.titulo }))
const ciudadNombre = computed(() => aj.ciudades.find((c) => c.id === aj.ciudad)?.nombre ?? '')
</script>

<template>
  <header :class="['sobre-foto top-0 z-40 w-full', enInicio ? 'absolute inset-x-0 bg-transparent' : 'sticky bg-velo']">
    <a href="#contenido" class="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:bg-tinta focus:px-3 focus:py-2 focus:text-papel">Saltar al contenido</a>
    <div class="flex h-barra items-stretch pl-4 lg:pl-6">
      <RouterLink to="/" class="mr-8 flex shrink-0 min-[1440px]:mr-10 items-center gap-2.5 text-xl font-bold uppercase tracking-[0.5px] text-tinta" aria-label="MiProximoCarro, inicio">
        <img src="/favicon.svg" alt="" class="h-[30px] w-[30px]" width="30" height="30" />
        <span>{{ T.marca }}</span>
      </RouterLink>

      <nav class="hidden items-stretch gap-6 nav:flex min-[1440px]:gap-7" aria-label="Secciones principales">
        <RouterLink to="/" class="enlace-barra" exact-active-class="enlace-barra-activo">{{ T.navCorto.inicio }}</RouterLink>
        <MenuDesplegable :etiqueta="T.navCorto.vehiculos" :opciones="vehiculos" :activo="enVehiculos" />
        <MenuDesplegable :etiqueta="T.navCorto.herramientas" :opciones="herramientas" :activo="route.path.startsWith('/herramientas')" />
      </nav>

      <div class="ml-auto hidden items-stretch pr-1 nav:flex">
        <!-- Ajustes regionales agrupados en un solo panel para despejar la barra -->
        <div ref="ajustesRef" class="relative flex h-full items-center">
          <button class="flex items-center gap-6 pr-6 text-xs font-bold uppercase tracking-[0.5px] text-tinta transition-colors hover:text-acento-texto" :aria-expanded="ajustesAbierto" aria-haspopup="dialog" title="Moneda, TRM y ciudad" @click="ajustesAbierto = !ajustesAbierto">
            <span class="text-acento-texto num">{{ aj.moneda }}<span> · TRM {{ formatoNumero(aj.trm) }}</span></span>
            <span>{{ ciudadNombre || 'Ajustes' }}</span>
          </button>
          <div v-if="ajustesAbierto" class="absolute right-0 top-full grid w-80 gap-5 border border-t-0 border-linea bg-papel p-6 shadow-menu" role="dialog" aria-label="Ajustes regionales">
            <div>
              <p class="etiqueta">Moneda</p>
              <div class="mt-2 flex border border-linea" role="group" aria-label="Moneda">
                <button v-for="m in ['COP', 'USD'] as const" :key="m" :aria-pressed="aj.moneda === m" :class="['h-11 flex-1 text-xs font-bold tracking-maquinado transition-colors', aj.moneda === m ? 'bg-tinta text-papel' : 'text-tenue hover:text-tinta']" @click="aj.moneda = m; aj.guardar()">{{ m }}</button>
              </div>
            </div>
            <label class="etiqueta block" title="TRM editable: vacía el campo para volver a la oficial">
              TRM (pesos por dólar)
              <input :value="Math.round(aj.trm)" inputmode="decimal" class="campo mt-2 num" aria-label="TRM en pesos por dólar" @change="cambiarTrm" />
              <span class="mt-2 block text-xs font-light normal-case tracking-normal text-apagado">Vacía el campo para volver a la oficial.</span>
            </label>
            <label class="etiqueta block">
              Ciudad
              <select v-model="aj.ciudad" class="campo mt-2 normal-case tracking-normal" aria-label="Ciudad" @change="aj.guardar()">
                <option v-for="c in aj.ciudades" :key="c.id" :value="c.id">{{ c.nombre }}</option>
              </select>
            </label>
            <button class="boton-secundario w-full" @click="aj.alternarTema()">
              <Sun v-if="aj.tema === 'oscuro'" class="h-4 w-4" aria-hidden="true" /><Moon v-else class="h-4 w-4" aria-hidden="true" />
              Tema {{ aj.tema === 'oscuro' ? 'claro' : 'oscuro' }}
            </button>
          </div>
        </div>
        <RouterLink to="/buscar?favoritos=1" class="relative mr-5 grid h-11 w-11 place-items-center self-center rounded-full text-tinta transition-colors hover:bg-white/10" :aria-label="`Favoritos (${fav.ids.length})`">
          <Heart class="h-5 w-5" aria-hidden="true" />
          <span v-if="fav.ids.length" class="absolute right-0.5 top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-acento px-1 text-[10px] font-bold text-white num">{{ fav.ids.length }}</span>
        </RouterLink>
      </div>

      <button class="ml-auto grid w-[72px] place-items-center text-tinta transition-colors hover:bg-white/10 nav:hidden" aria-label="Abrir menú" @click="lateralAbierto = true"><Menu class="h-6 w-6" aria-hidden="true" /></button>
    </div>

    <!-- Menú móvil: hoja a pantalla completa con la franja M arriba -->
    <div v-if="lateralAbierto" class="fixed inset-0 z-50 flex flex-col overflow-y-auto bg-papel nav:hidden" role="dialog" aria-modal="true" aria-label="Menú">
      <div class="franja-m shrink-0" aria-hidden="true" />
      <div class="contenedor flex h-16 shrink-0 items-center justify-between border-b border-linea">
        <span class="text-lg font-bold uppercase tracking-[1px] text-tinta">{{ T.marca }}</span>
        <button class="grid h-11 w-11 place-items-center text-tinta" aria-label="Cerrar menú" @click="lateralAbierto = false"><X class="h-6 w-6" aria-hidden="true" /></button>
      </div>
      <div class="contenedor flex flex-col pb-10">
        <RouterLink to="/" class="border-b border-linea py-5 text-2xl font-bold uppercase text-tinta" exact-active-class="!text-acento-texto" @click="lateralAbierto = false">{{ T.navCorto.inicio }}</RouterLink>
        <button class="flex items-center justify-between border-b border-linea py-5 text-2xl font-bold uppercase text-tinta" :aria-expanded="vehiculosMovil" aria-controls="vehiculos-movil" @click="vehiculosMovil = !vehiculosMovil">
          {{ T.navCorto.vehiculos }} <ChevronDown :class="['h-6 w-6 transition-transform', vehiculosMovil ? 'rotate-180' : '']" aria-hidden="true" />
        </button>
        <div v-show="vehiculosMovil" id="vehiculos-movil" class="flex flex-col">
          <RouterLink v-for="v in vehiculos" :key="v.to" :to="v.to" class="border-b border-linea py-4 pl-4 text-tinta" active-class="!text-acento-texto" @click="lateralAbierto = false">{{ v.texto }}</RouterLink>
        </div>
        <button class="flex items-center justify-between border-b border-linea py-5 text-2xl font-bold uppercase text-tinta" :aria-expanded="herramientasMovil" aria-controls="herramientas-movil" @click="herramientasMovil = !herramientasMovil">
          {{ T.navCorto.herramientas }} <ChevronDown :class="['h-6 w-6 transition-transform', herramientasMovil ? 'rotate-180' : '']" aria-hidden="true" />
        </button>
        <div v-show="herramientasMovil" id="herramientas-movil" class="flex flex-col">
          <RouterLink v-for="h in T.herramientas" :key="h.ruta" :to="h.ruta" class="border-b border-linea py-4 pl-4 text-tinta" @click="lateralAbierto = false">{{ h.titulo }}</RouterLink>
        </div>
        <RouterLink to="/buscar?favoritos=1" class="border-b border-linea py-4 text-tinta" @click="lateralAbierto = false">Favoritos ({{ fav.ids.length }})</RouterLink>
        <p class="etiqueta mt-8">Ajustes</p>
        <div class="mt-3 grid grid-cols-2 gap-4">
          <div class="col-span-2 flex border border-linea" role="group" aria-label="Moneda">
            <button v-for="m in ['COP', 'USD'] as const" :key="m" :aria-pressed="aj.moneda === m" :class="['h-12 flex-1 text-sm font-bold tracking-maquinado', aj.moneda === m ? 'bg-tinta text-papel' : 'text-tenue']" @click="aj.moneda = m; aj.guardar()">{{ m }}</button>
          </div>
          <label class="text-sm">TRM <input :value="Math.round(aj.trm)" class="campo mt-1 num" inputmode="decimal" @change="cambiarTrm" /></label>
          <label class="text-sm">Ciudad
            <select v-model="aj.ciudad" class="campo mt-1" @change="aj.guardar()"><option v-for="c in aj.ciudades" :key="c.id" :value="c.id">{{ c.nombre }}</option></select>
          </label>
          <button class="boton-secundario col-span-2" @click="aj.alternarTema()">Tema {{ aj.tema === 'oscuro' ? 'claro' : 'oscuro' }}</button>
        </div>
      </div>
    </div>
  </header>
</template>
