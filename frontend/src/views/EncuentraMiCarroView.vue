<script setup lang="ts">
import { computed, ref } from 'vue'
import { useHead } from '@unhead/vue'
import { api } from '@/lib/api'
import { useAjustes } from '@/stores/ajustes'
import { useFormato } from '@/composables/useFormato'
import TarjetaVehiculo from '@/components/TarjetaVehiculo.vue'
import type { Paginado, Tarjeta } from '@/lib/tipos'

useHead({ title: 'Encuentra mi carro' })
const aj = useAjustes()
const f = useFormato()
const paso = ref(0)
const r = ref({ presupuesto: 120, uso: 'ciudad', ciudad: aj.ciudad, pasajeros: 5, prioridad: 'ahorro', electrico: 'indiferente' })
const PREGUNTAS = [
  { k: 'presupuesto', t: '¿Cuál es tu presupuesto máximo (precio base)?' },
  { k: 'uso', t: '¿Dónde lo usarás más?' },
  { k: 'ciudad', t: '¿En qué ciudad vives?' },
  { k: 'pasajeros', t: '¿Cuántas personas lleva normalmente?' },
  { k: 'prioridad', t: '¿Qué priorizas?' },
  { k: 'electrico', t: '¿Te interesa un eléctrico o híbrido?' },
]
const resultados = ref<{ v: Tarjeta; razones: string[]; puntaje: number }[] | null>(null)
const PERFIL: Record<string, string> = { ahorro: 'ahorrador', espacio: 'familiar', desempeno: 'rendimiento', confianza: 'fiabilidad' }

async function terminar() {
  const params: Record<string, unknown> = { precio_max: r.value.presupuesto * 1_000_000, plazas: r.value.pasajeros, size: 100, estado: ['Vigente'] }
  if (r.value.electrico === 'si') params.electrificado = true
  if (r.value.electrico === 'no') params.electrificado = false
  if (r.value.uso === 'destapado') params.despeje_min = 190
  const lista = (await api.get<Paginado<Tarjeta>>('/vehiculos', params as never)).resultados
  if (!lista.length) { resultados.value = []; return }
  const cmp = await api.post<{ puntajes: { id: number; puntaje: number }[] }>('/comparar', { ids: [...lista].sort((a, b) => (b.puntaje_miproximocarro_base || 0) - (a.puntaje_miproximocarro_base || 0)).slice(0, 10).map((v) => v.id).concat(lista.length === 1 ? [] : []), ciudad: r.value.ciudad, perfil: PERFIL[r.value.prioridad] })
    .catch(() => ({ puntajes: lista.map((v) => ({ id: v.id, puntaje: v.puntaje_miproximocarro_base || 0 })) }))
  const pts = new Map(cmp.puntajes.map((p) => [p.id, p.puntaje]))
  const modelos = new Set<string>()
  resultados.value = lista.filter((v) => pts.has(v.id)).sort((a, b) => (pts.get(b.id) || 0) - (pts.get(a.id) || 0))
    .filter((v) => !modelos.has(v.modelo) && modelos.add(v.modelo)).slice(0, 5)
    .map((v) => ({ v, puntaje: pts.get(v.id) || 0, razones: razones(v) }))
  paso.value = PREGUNTAS.length
}
function razones(v: Tarjeta): string[] {
  const x: string[] = []
  x.push(`Precio base ${f.dinero(v.precio_base_cop)}, dentro de tu presupuesto.`)
  if (r.value.prioridad === 'confianza') x.push(`Fiabilidad ${f.numero(v.puntaje_fiabilidad, 1)}/10.`)
  if (r.value.prioridad === 'ahorro' && v.consumo_real_estimado_kml) x.push(`Consumo real estimado de ${f.consumo(v.consumo_real_estimado_kml)}.`)
  if (r.value.prioridad === 'espacio') x.push(`Baúl de ${f.numero(v.capacidad_baul_litros)} L y ${v.plazas} plazas.`)
  if (r.value.prioridad === 'desempeno') x.push(`${f.numero(v.potencia_hp)} hp.`)
  if (r.value.uso === 'destapado') x.push(`Despeje de ${v.distancia_libre_suelo_mm} mm.`)
  if (v.tiene_alerta_roja) x.push('Ojo: tiene alerta roja de fiabilidad.')
  return x
}
const actual = computed(() => PREGUNTAS[paso.value])
</script>

<template>
  <div class="contenedor pagina max-w-4xl">
    <h1 class="titulo-pagina">Encuentra mi carro</h1>
    <p class="entradilla">Seis preguntas. Cinco recomendaciones explicadas con el Puntaje MiProximoCarro.</p>
    <div v-if="paso < PREGUNTAS.length" class="tarjeta mt-12 p-6 lg:p-10">
      <p class="etiqueta num">Pregunta {{ paso + 1 }} de {{ PREGUNTAS.length }}</p>
      <div class="mt-3 h-1 bg-linea"><div class="h-1 bg-tinta transition-all" :style="{ width: `${((paso + 1) / PREGUNTAS.length) * 100}%` }" /></div>
      <h2 class="mt-8 text-display-sm normal-case tracking-normal">{{ actual.t }}</h2>
      <div class="mt-6">
        <label v-if="actual.k === 'presupuesto'" class="block">Hasta <strong class="num">{{ f.cop(r.presupuesto * 1_000_000) }}</strong><input v-model.number="r.presupuesto" type="range" min="40" max="500" step="5" class="mt-2 w-full" /></label>
        <div v-else-if="actual.k === 'uso'" class="flex flex-wrap gap-2"><button v-for="[v, t] in [['ciudad', 'Ciudad'], ['carretera', 'Carretera'], ['mixto', 'Mixto'], ['destapado', 'Fincas y destapado']]" :key="v" :class="['chip min-h-[48px] px-5 text-base', r.uso === v ? 'chip-activo' : '']" @click="r.uso = v">{{ t }}</button></div>
        <div v-else-if="actual.k === 'ciudad'" class="flex flex-wrap gap-2"><button v-for="c in aj.ciudades" :key="c.id" :class="['chip min-h-[48px] px-5 text-base', r.ciudad === c.id ? 'chip-activo' : '']" @click="r.ciudad = c.id">{{ c.nombre }}</button></div>
        <div v-else-if="actual.k === 'pasajeros'" class="flex flex-wrap gap-2"><button v-for="n in [2, 4, 5, 7]" :key="n" :class="['chip min-h-[48px] px-5 text-base num', r.pasajeros === n ? 'chip-activo' : '']" @click="r.pasajeros = n">{{ n }}{{ n === 7 ? ' o más' : '' }}</button></div>
        <div v-else-if="actual.k === 'prioridad'" class="flex flex-wrap gap-2"><button v-for="[v, t] in [['ahorro', 'Ahorro'], ['espacio', 'Espacio'], ['desempeno', 'Desempeño'], ['confianza', 'Confianza mecánica']]" :key="v" :class="['chip min-h-[48px] px-5 text-base', r.prioridad === v ? 'chip-activo' : '']" @click="r.prioridad = v">{{ t }}</button></div>
        <div v-else class="flex flex-wrap gap-2"><button v-for="[v, t] in [['si', 'Sí, eléctrico o híbrido'], ['no', 'No'], ['indiferente', 'Me da igual']]" :key="v" :class="['chip min-h-[48px] px-5 text-base', r.electrico === v ? 'chip-activo' : '']" @click="r.electrico = v">{{ t }}</button></div>
      </div>
      <div class="mt-10 flex justify-between gap-3 border-t border-linea pt-6">
        <button class="boton-secundario" :disabled="paso === 0" @click="paso--">Atrás</button>
        <button v-if="paso < PREGUNTAS.length - 1" class="boton-solido" @click="paso++">Siguiente</button>
        <button v-else class="boton-solido" @click="terminar">Ver recomendaciones</button>
      </div>
    </div>
    <div v-else class="mt-12 grid gap-6">
      <p v-if="resultados && !resultados.length">No encontramos opciones con esas respuestas. <button class="underline" @click="paso = 0">Ajusta tus respuestas</button>.</p>
      <div v-for="(x, i) in resultados" :key="x.v.id" class="grid gap-px border border-linea bg-linea md:grid-cols-[1fr_18rem] [&>article]:border-0">
        <TarjetaVehiculo :v="x.v" />
        <div class="celda-dato text-sm">
          <p class="etiqueta">#{{ i + 1 }} · Puntaje MiProximoCarro</p>
          <p class="cifra mt-2 lg:text-display-md">{{ x.puntaje }}<span class="text-base font-light tracking-normal text-tenue">/100</span></p>
          <ul class="mt-4 grid gap-2 text-tenue [&>li]:border-t [&>li]:border-linea [&>li]:pt-2"><li v-for="z in x.razones" :key="z">{{ z }}</li></ul>
        </div>
      </div>
      <button class="boton-secundario" @click="paso = 0; resultados = null">Volver a empezar</button>
    </div>
  </div>
</template>
