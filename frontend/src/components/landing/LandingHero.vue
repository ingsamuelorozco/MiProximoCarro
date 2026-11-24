<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useHead } from '@unhead/vue'
import fondo from '@/assets/images/hero-bg-city.jpg'
import HeroHotspot from '@/components/landing/HeroHotspot.vue'
import IconoMotor from '@/components/landing/IconoMotor.vue'
import { Banknote, Fuel, Luggage, Mountain, Route, ShieldCheck, Timer } from 'lucide-vue-next'
import { api } from '@/lib/api'
import { AUTOS_HERO, ROTACION_MS, type AutoHero, type DatoExtra } from '@/lib/autosHero'
import { T } from '@/lib/textos'
import { formatoNumero, useFormato } from '@/composables/useFormato'
import { useAjustes } from '@/stores/ajustes'

defineProps<{ versiones?: number | null; marcas?: number | null }>()
// El fondo es la imagen más grande sobre el pliegue: se pide antes que el JS de la vista.
useHead({ link: [{ rel: 'preload', as: 'image', href: fondo }] })

const f = useFormato()
const aj = useAjustes()

/** Lo que el hero necesita de la ficha de cada auto. */
interface Ficha {
  especificaciones: { motor: { motor_descripcion: string; potencia_hp: number | null; torque_nm: number | null; aceleracion_0_100_seg: number | null }; chasis: { traccion: string } }
  precio: { puesta_en_calle: { total_cop: number } }
  costo: { consumo: { consumo_real_estimado_kml: number | null; autonomia_estimada_km: number | null } }
  tamano: { medidas: { capacidad_baul_litros: number | null } }
  fiabilidad: { puntaje: number | null; etiqueta: string }
  ciudad: { nombre: string }
}
const fichas = reactive<Record<string, Ficha>>({})
async function cargarFicha(a: AutoHero) {
  const clave = `${a.slug}|${aj.ciudad}`
  if (fichas[clave]) return
  try { fichas[clave] = await api.get<Ficha>(`/vehiculos/${a.slug}`, { ciudad: aj.ciudad }) } catch { /* el punto muestra "—" */ }
}

const indice = ref(0)
const auto = computed(() => AUTOS_HERO[indice.value])
const ficha = computed(() => fichas[`${auto.value.slug}|${aj.ciudad}`])

const ICONO_EXTRA = { aceleracion: Timer, consumo: Fuel, autonomia: Route, traccion: Mountain, fiabilidad: ShieldCheck, baul: Luggage } as const
const EXTRA: Record<DatoExtra, (d: Ficha) => [string, string]> = {
  aceleracion: (d) => ['0 a 100 km/h', `${formatoNumero(d.especificaciones.motor.aceleracion_0_100_seg, 1)} s · tracción ${d.especificaciones.chasis.traccion.toLowerCase()}`],
  consumo: (d) => ['Consumo real estimado', f.consumo(d.costo.consumo.consumo_real_estimado_kml)],
  autonomia: (d) => ['Autonomía', `${formatoNumero(d.costo.consumo.autonomia_estimada_km)} km por carga`],
  traccion: (d) => ['Tracción', `${d.especificaciones.chasis.traccion} · 0 a 100 en ${formatoNumero(d.especificaciones.motor.aceleracion_0_100_seg, 1)} s`],
  fiabilidad: (d) => ['Fiabilidad MiProximoCarro', `${formatoNumero(d.fiabilidad.puntaje, 1)} de 10 · ${d.fiabilidad.etiqueta}`],
  baul: (d) => ['Baúl', `${formatoNumero(d.tamano.medidas.capacidad_baul_litros)} litros`],
}
const puntos = computed(() => {
  const a = auto.value, d = ficha.value
  const m = d?.especificaciones.motor
  return [
    { clave: 'motor', icono: IconoMotor, xy: a.puntos.motor, titulo: 'Motor', texto: m ? `${m.motor_descripcion} · ${formatoNumero(m.potencia_hp)} hp · ${formatoNumero(m.torque_nm)} Nm` : '—' },
    { clave: 'costo', icono: Banknote, xy: a.puntos.costo, titulo: d ? `Precio en calle · ${d.ciudad.nombre}` : 'Precio en calle', texto: d ? f.dinero(d.precio.puesta_en_calle.total_cop) : '—' },
    { clave: 'extra', icono: ICONO_EXTRA[a.extra], xy: a.puntos.extra, ...(d ? { titulo: EXTRA[a.extra](d)[0], texto: EXTRA[a.extra](d)[1] } : { titulo: 'Dato', texto: '—' }) },
  ]
})

/** Precarga la foto y la ficha del siguiente para que el cambio no parpadee. */
function precargar(i: number) {
  const a = AUTOS_HERO[i % AUTOS_HERO.length]
  const img = new Image()
  img.src = a.imagen
  cargarFicha(a)
}
function irA(i: number) {
  indice.value = (i + AUTOS_HERO.length) % AUTOS_HERO.length
  cargarFicha(auto.value)
  precargar(indice.value + 1)
}

let temporizador: ReturnType<typeof setInterval> | undefined
function reiniciar() {
  clearInterval(temporizador)
  temporizador = setInterval(() => { if (!document.hidden) irA(indice.value + 1) }, ROTACION_MS)
}
function elegir(i: number) { irA(i); reiniciar() }
onMounted(() => { irA(0); reiniciar() })
onUnmounted(() => clearInterval(temporizador))
watch(() => aj.ciudad, () => cargarFicha(auto.value))
</script>

<template>
  <section class="sobre-foto relative isolate flex min-h-[calc(100svh-57px)] items-center overflow-hidden bg-velo nav:min-h-svh" aria-labelledby="hero-titulo">
    <img :src="fondo" alt="" class="absolute inset-0 -z-20 h-full w-full object-cover grayscale" width="1600" height="1193" fetchpriority="high" decoding="async" />
    <div class="absolute inset-0 -z-10 bg-velo/[0.88]" aria-hidden="true" />

    <!-- Dos columnas en flujo normal: el texto y el auto nunca se enciman, sea cual sea el alto de la pantalla -->
    <div class="relative mx-auto grid w-full max-w-[1400px] grid-cols-[minmax(0,1fr)] items-center gap-10 px-4 pb-[120px] pt-[calc(72px+24px)] sm:px-6 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.45fr)] lg:gap-8 lg:px-10 lg:pb-[150px] xl:pl-[110px]">
      <div class="relative z-20">
        <h1 id="hero-titulo" class="whitespace-nowrap text-[44px] leading-[0.95] tracking-[-1px] text-tinta sm:text-[56px] lg:text-[64px]">
          <Transition mode="out-in" enter-active-class="transition duration-500 ease-out" leave-active-class="transition duration-300 ease-in" enter-from-class="translate-y-3 opacity-0" leave-to-class="-translate-y-3 opacity-0">
            <span :key="auto.slug" class="block"><span class="block text-acento-texto">{{ auto.pregunta[0] }}</span> <span class="block">{{ auto.pregunta[1] }}</span></span>
          </Transition>
        </h1>
        <p class="mt-6 max-w-[320px] text-[15px] font-normal leading-[1.6] text-tinta">{{ T.sublema }}</p>
        <div class="mt-8 border-l-2 border-acento pl-4">
          <p class="text-sm font-bold uppercase tracking-[1px] text-acento-texto">{{ T.landing.hero.datoTitulo }}</p>
          <p class="mt-2 text-sm font-bold text-tinta"><span class="num">{{ versiones ?? '—' }}</span> versiones · <span class="num">{{ marcas ?? '—' }}</span> marcas</p>
        </div>
      </div>

      <div class="relative z-10">
        <div class="relative aspect-[2/1]">
          <Transition enter-active-class="transition duration-500 ease-out" leave-active-class="transition duration-300 ease-in" enter-from-class="translate-x-8 opacity-0" leave-to-class="-translate-x-8 opacity-0">
          <div :key="auto.slug" class="absolute inset-x-0 bottom-0">
            <img :src="auto.imagen" :alt="auto.alt" class="block w-full drop-shadow-[0_24px_24px_rgb(0_0_0/0.55)]" width="1400" :height="auto.alto" decoding="async" />
            <HeroHotspot v-for="p in puntos" :key="p.clave" :x="p.xy[0]" :y="p.xy[1]" :titulo="p.titulo" :texto="p.texto" :icono="p.icono" />
          </div>
          </Transition>
        </div>
        <!-- Nombre del auto, enlace a su ficha y selector manual -->
        <div class="mt-4 flex items-center justify-between gap-3">
          <RouterLink :to="`/vehiculo/${auto.slug}`" class="min-w-0 truncate text-xs font-bold uppercase tracking-maquinado text-tinta transition-colors hover:text-acento-texto">{{ auto.nombre }} · ver ficha</RouterLink>
          <div class="flex shrink-0 items-center gap-1" role="group" aria-label="Elegir auto del encabezado">
            <button v-for="(a, i) in AUTOS_HERO" :key="a.slug" type="button" class="group/p flex h-6 items-center px-0.5" :aria-label="`Ver ${a.nombre}`" :aria-current="i === indice" @click="elegir(i)">
              <span :class="['block h-0.5 transition-all', i === indice ? 'w-6 bg-acento' : 'w-3 bg-white/30 group-hover/p:bg-white/60']" />
            </button>
          </div>
        </div>
        <p class="mt-1 truncate text-right text-[10px] text-apagado">Foto: <a :href="auto.credito.url" target="_blank" rel="noopener" class="underline hover:text-white">{{ auto.credito.autor }}</a>, {{ auto.credito.licencia }}</p>
      </div>
    </div>
  </section>
</template>
