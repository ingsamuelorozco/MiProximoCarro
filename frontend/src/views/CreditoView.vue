<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useHead } from '@unhead/vue'
import { useDebounceFn } from '@vueuse/core'
import { Download, Plus, Trash2 } from 'lucide-vue-next'
import { api } from '@/lib/api'
import { useFormato } from '@/composables/useFormato'
import GraficoLineas from '@/components/GraficoLineas.vue'

useHead({ title: 'Simulador de crédito' })
const f = useFormato()
const e = ref({
  precio: 100_000_000, tramites: 1_800_000, financiarTramites: false, modoInicial: 'pct' as 'pct' | 'cop', inicialPct: 30, inicialCop: 30_000_000,
  plazo: 60, tasa: 15.5, vida: 0.12, seguroVeh: 0, comision: 0, tipo: 'fija' as 'fija' | 'balon', balon: 30, maxPct: 30,
  modoAbono: 'plazo' as 'plazo' | 'cuota', abonos: [] as { mes: number; valor: number }[],
})
const r = ref<any>(null)
const tablaAbierta = ref(false)
const calcular = useDebounceFn(async () => {
  r.value = await api.post('/financiero/credito', {
    precio_cop: e.value.precio, tramites_cop: e.value.tramites, financiar_tramites: e.value.financiarTramites,
    ...(e.value.modoInicial === 'pct' ? { cuota_inicial_pct: e.value.inicialPct / 100 } : { cuota_inicial_cop: e.value.inicialCop }),
    plazo_meses: e.value.plazo, tasa_ea: e.value.tasa / 100, seguro_vida_mensual_pct: e.value.vida / 100,
    seguro_vehiculo_mensual_cop: e.value.seguroVeh, comision_cop: e.value.comision, tipo_cuota: e.value.tipo,
    valor_final_pct: e.value.tipo === 'balon' ? e.value.balon / 100 : 0, abonos: e.value.abonos.filter((a) => a.valor > 0),
    modo_abono: e.value.modoAbono, max_pct_ingreso: e.value.maxPct / 100,
  }).catch(() => null)
}, 250)
watch(e, calcular, { deep: true, immediate: true })
const series = computed(() => (r.value?.tabla ? [
  { nombre: 'Saldo', puntos: r.value.tabla.map((t: any) => ({ x: t.mes, y: t.saldo_cop })) },
  { nombre: 'Intereses acumulados', puntos: r.value.tabla.map((t: any) => ({ x: t.mes, y: t.interes_acumulado_cop })) },
] : []))
function csv() {
  if (!r.value?.tabla) return
  const filas = [['mes', 'cuota', 'interes', 'capital', 'abono', 'seguros', 'saldo'], ...r.value.tabla.map((t: any) => [t.mes, t.cuota_cop, t.interes_cop, t.capital_cop, t.abono_cop, t.seguros_cop, t.saldo_cop])]
  const url = URL.createObjectURL(new Blob([filas.map((x) => x.join(';')).join('\n')], { type: 'text/csv;charset=utf-8' }))
  const a = document.createElement('a'); a.href = url; a.download = 'amortizacion-miproximocarro.csv'; a.click(); URL.revokeObjectURL(url)
}
</script>

<template>
  <div class="contenedor pagina">
    <h1 class="titulo-pagina">Simulador de crédito</h1>
    <p class="entradilla">Cuota fija (sistema francés) o con cuota balón, abonos a capital y tres escenarios de plazo. <strong>Estimado, no es una oferta de crédito.</strong></p>
    <div class="mt-12 grid gap-10 lg:grid-cols-[24rem_1fr]">
      <form class="tarjeta grid content-start gap-5 p-6 text-sm lg:sticky lg:top-24" @submit.prevent>
        <label>Precio del vehículo (COP)<input v-model.number="e.precio" type="number" min="1000000" step="100000" class="campo mt-1 num" /></label>
        <label>Trámites (SOAT + matrícula)<input v-model.number="e.tramites" type="number" min="0" step="10000" class="campo mt-1 num" /></label>
        <label class="flex items-center gap-2"><input v-model="e.financiarTramites" type="checkbox" class="h-4 w-4" /> Financiar SOAT y matrícula</label>
        <fieldset class="grid gap-2 border-t border-linea pt-5"><legend class="etiqueta float-left mb-3 w-full !text-tinta">Cuota inicial</legend>
          <div class="flex gap-2"><button type="button" :class="['chip', e.modoInicial === 'pct' ? 'chip-activo' : '']" @click="e.modoInicial = 'pct'">%</button><button type="button" :class="['chip', e.modoInicial === 'cop' ? 'chip-activo' : '']" @click="e.modoInicial = 'cop'">COP</button></div>
          <input v-if="e.modoInicial === 'pct'" v-model.number="e.inicialPct" type="number" min="0" max="90" class="campo num" aria-label="Cuota inicial en porcentaje" />
          <input v-else v-model.number="e.inicialCop" type="number" min="0" step="100000" class="campo num" aria-label="Cuota inicial en pesos" />
        </fieldset>
        <label>Plazo: <strong class="num">{{ e.plazo }} meses</strong><input v-model.number="e.plazo" type="range" min="12" max="84" step="6" class="w-full" /></label>
        <label>Tasa efectiva anual (%)<input v-model.number="e.tasa" type="number" min="0" max="40" step="0.1" class="campo mt-1 num" /></label>
        <label>Seguro de vida deudor (% mensual sobre saldo)<input v-model.number="e.vida" type="number" min="0" max="1" step="0.01" class="campo mt-1 num" /></label>
        <label>Seguro del vehículo financiado (COP/mes)<input v-model.number="e.seguroVeh" type="number" min="0" step="10000" class="campo mt-1 num" /></label>
        <label>Comisión o estudio de crédito (COP)<input v-model.number="e.comision" type="number" min="0" step="10000" class="campo mt-1 num" /></label>
        <fieldset class="grid gap-2 border-t border-linea pt-5"><legend class="etiqueta float-left mb-3 w-full !text-tinta">Tipo de cuota</legend>
          <div class="flex gap-2"><button type="button" :class="['chip', e.tipo === 'fija' ? 'chip-activo' : '']" @click="e.tipo = 'fija'">Fija</button><button type="button" :class="['chip', e.tipo === 'balon' ? 'chip-activo' : '']" @click="e.tipo = 'balon'">Balón / valor final</button></div>
          <label v-if="e.tipo === 'balon'">Porcentaje diferido al último mes<input v-model.number="e.balon" type="number" min="0" max="60" class="campo mt-1 num" /></label>
        </fieldset>
        <fieldset class="grid gap-2 border-y border-linea py-5"><legend class="etiqueta float-left mb-3 w-full !text-tinta">Abonos extra a capital</legend>
          <div v-for="(a, i) in e.abonos" :key="i" class="flex gap-2"><input v-model.number="a.mes" type="number" min="1" max="84" class="campo w-20 num" aria-label="Mes del abono" /><input v-model.number="a.valor" type="number" min="0" step="100000" class="campo num" aria-label="Valor del abono" /><button type="button" class="grid w-11 place-items-center" aria-label="Quitar abono" @click="e.abonos.splice(i, 1)"><Trash2 class="h-4 w-4" aria-hidden="true" /></button></div>
          <button type="button" class="boton-secundario" @click="e.abonos.push({ mes: 12, valor: 5_000_000 })"><Plus class="h-4 w-4" aria-hidden="true" /> Agregar abono</button>
          <div v-if="e.abonos.length" class="flex gap-2"><button type="button" :class="['chip', e.modoAbono === 'plazo' ? 'chip-activo' : '']" @click="e.modoAbono = 'plazo'">Reducir plazo</button><button type="button" :class="['chip', e.modoAbono === 'cuota' ? 'chip-activo' : '']" @click="e.modoAbono = 'cuota'">Reducir cuota</button></div>
        </fieldset>
        <label>Máximo del ingreso para la cuota (%)<input v-model.number="e.maxPct" type="number" min="5" max="60" class="campo mt-1 num" /></label>
      </form>

      <div v-if="r" class="grid content-start gap-6" aria-live="polite">
        <div class="tarjeta grid gap-x-6 gap-y-8 p-6 sm:grid-cols-3 lg:p-8">
          <div><p class="etiqueta">Cuota mensual</p><p class="cifra mt-2 lg:text-display-md">{{ f.dinero(r.cuota_mensual_con_seguros_cop) }}</p><p class="text-xs text-tenue">incluye seguros del primer mes</p></div>
          <div><p class="etiqueta">Total intereses</p><p class="mt-2 text-2xl font-bold text-tinta num">{{ f.dinero(r.total_intereses_cop) }}</p><p class="text-xs text-tenue num">Costo del crédito {{ f.dinero(r.costo_total_credito_cop) }} · {{ f.pct(r.sobrecosto_pct) }} sobre el precio</p></div>
          <div><p class="etiqueta">Ingreso mínimo recomendado</p><p class="mt-2 text-2xl font-bold text-tinta num">{{ f.dinero(r.ingreso_minimo_recomendado_cop) }}</p><p class="text-xs text-tenue">cuota ≤ {{ e.maxPct }}% del ingreso neto</p></div>
          <p v-if="r.valor_final_cop" class="text-sm sm:col-span-3">Cuota balón al final: <strong class="num">{{ f.dinero(r.valor_final_cop) }}</strong></p>
          <p v-if="r.ahorro_intereses_por_abonos_cop" class="text-sm text-mejor sm:col-span-3">Con tus abonos ahorras <strong class="num">{{ f.dinero(r.ahorro_intereses_por_abonos_cop) }}</strong> en intereses y terminas en {{ r.meses_efectivos }} meses.</p>
          <p class="text-xs text-tenue sm:col-span-3">Tasa de usura vigente: {{ f.pct(r.tasa_usura_ea) }} E.A. (consulta {{ f.fecha(r.fecha_consulta) }}). <span v-if="r.supera_usura" class="font-semibold text-roja">La tasa ingresada supera la usura.</span></p>
        </div>
        <div class="tarjeta p-6">
          <h2 class="text-2xl">El costo de alargar el plazo</h2>
          <div class="mt-6 grid gap-px border border-linea bg-linea sm:grid-cols-3">
            <div v-for="s in r.escenarios" :key="s.plazo_meses" class="celda-dato">
              <p class="etiqueta">{{ s.plazo_meses }} meses</p>
              <p class="mt-2 text-2xl font-bold text-tinta num">{{ f.dinero(s.cuota_mensual_con_seguros_cop) }}</p>
              <p class="text-sm text-tenue num">Intereses {{ f.dinero(s.total_intereses_cop) }} · {{ f.pct(s.sobrecosto_pct) }}</p>
            </div>
          </div>
        </div>
        <div class="tarjeta p-6">
          <h2 class="text-2xl">Saldo contra intereses acumulados</h2>
          <GraficoLineas class="mt-4" titulo="Saldo del crédito e intereses acumulados por mes" :series="series" etiqueta-x="mes" :formato-y="(y: number) => f.millones(y)" />
        </div>
        <div class="tarjeta p-6">
          <div class="flex flex-wrap items-center gap-3">
            <button class="boton-secundario px-5" :aria-expanded="tablaAbierta" @click="tablaAbierta = !tablaAbierta">{{ tablaAbierta ? 'Ocultar' : 'Ver' }} tabla de amortización</button>
            <button class="boton-secundario px-5" @click="csv"><Download class="h-4 w-4" aria-hidden="true" /> Exportar CSV</button>
          </div>
          <div v-if="tablaAbierta" class="mt-4 max-h-96 overflow-auto">
            <table class="w-full text-sm num">
              <thead class="sticky top-0 bg-superficie"><tr class="text-right text-tenue"><th class="py-2 text-left font-normal">Mes</th><th class="font-normal">Cuota</th><th class="font-normal">Interés</th><th class="font-normal">Capital</th><th class="font-normal">Abono</th><th class="font-normal">Seguros</th><th class="font-normal">Saldo</th></tr></thead>
              <tbody><tr v-for="t in r.tabla" :key="t.mes" class="border-t border-linea text-right"><td class="py-2 text-left">{{ t.mes }}</td><td>{{ f.cop(t.cuota_cop) }}</td><td>{{ f.cop(t.interes_cop) }}</td><td>{{ f.cop(t.capital_cop) }}</td><td>{{ t.abono_cop ? f.cop(t.abono_cop) : '' }}</td><td>{{ f.cop(t.seguros_cop) }}</td><td>{{ f.cop(t.saldo_cop) }}</td></tr></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
