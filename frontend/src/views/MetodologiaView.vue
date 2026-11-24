<script setup lang="ts">
import { onMounted } from 'vue'
import { useHead } from '@unhead/vue'
import { api } from '@/lib/api'
import { useCarga } from '@/composables/useCarga'
import { useFormato } from '@/composables/useFormato'
import EstadoCarga from '@/components/EstadoCarga.vue'
import type { Fuente } from '@/lib/tipos'

useHead({ title: 'Metodología' })
const f = useFormato()
const { datos: m, cargando, error, ejecutar } = useCarga(() => Promise.all([api.get<any>('/config/metodologia'), api.get<Fuente[]>('/config/fuentes')]))
onMounted(ejecutar)
const NOMBRES: Record<string, string> = { motor_transmision: 'Motor y transmisión', quejas_documentadas: 'Quejas documentadas', repuestos_y_red: 'Repuestos y red', recalls: 'Recalls', costo_reparaciones: 'Costo de reparaciones', electrica_electronica: 'Eléctrica y electrónica' }
</script>

<template>
  <article class="contenedor pagina prosa max-w-4xl">
    <h1 class="titulo-pagina">Metodología</h1>
    <p class="entradilla !max-w-none">Cómo obtenemos cada dato, qué significa «Estimado», cómo calculamos el puntaje y cuáles son los límites de la plataforma.</p>
    <EstadoCarga :cargando="cargando" :error="error" @reintentar="ejecutar">
      <template v-if="m">
        <h2 class="mt-16 border-t border-linea pt-8 text-display-sm">De dónde sale cada dato</h2>
        <p class="mt-3">Cada cifra lleva fuente, fecha y estado: <strong>verificado</strong>, <strong>estimado</strong> o <strong>no disponible</strong>. El orden de consulta es: ficha oficial del fabricante en Colombia, Latin NCAP, Guía de Valores de Fasecolda y prensa automotriz colombiana. Autocosmos, Encycarpedia y CarSized solo sirven para contrastar; no copiamos sus textos, tablas ni imágenes.</p>
        <h2 class="mt-16 border-t border-linea pt-8 text-display-sm">Qué significa «Estimado»</h2>
        <p class="mt-3">Un dato es estimado cuando no lo hemos contrastado aún con una fuente pública vigente, o cuando lo deriva una regla documentada (por ejemplo, el ancho con espejos a partir del ancho sin espejos, o el consumo en ciudad a partir del mixto). <strong>En la versión 1.0, las fichas técnicas y los precios de vitrina del catálogo están marcados como estimados</strong>: provienen de una base editorial de fichas públicas y se irán verificando una a una. Las tarifas de SOAT 2026, la tasa de usura, el precio del combustible de la CREG y la TRM sí se consultaron en fuentes oficiales.</p>
        <h2 id="precios" class="mt-16 border-t border-linea pt-8 text-display-sm">Precios y puesta en calle</h2>
        <p class="mt-3">Precio total puesto en calle = precio base + SOAT + matrícula (derechos, placas, RUNT e impuesto vehicular proporcional a los meses restantes del año). El SOAT depende de la clase (familiar o campero/camioneta), el cilindraje y la antigüedad; los eléctricos tienen 10% de descuento en la prima (Ley 1964 de 2019). El impuesto vehicular se calcula sobre el avalúo comercial, no sobre el cilindraje: para vehículos nuevos lo estimamos como el precio sin IVA ({{ f.pct(m[0].matricula.impuesto.iva_vehiculos) }}). Tarifas nacionales: {{ m[0].matricula.impuesto.rangos_nacionales.map((r: any) => f.pct(r.tarifa)).join(', ') }}; los eléctricos no pagan más de {{ f.pct(m[0].matricula.impuesto.tope_bev) }}.</p>
        <h2 id="fiabilidad" class="mt-16 border-t border-linea pt-8 text-display-sm">Puntaje de fiabilidad</h2>
        <p class="mt-3">Puntaje = <span v-for="(p, k, i) in m[0].fiabilidad.pesos" :key="k">{{ i ? ' + ' : '' }}{{ Math.round(Number(p) * 100) }}% {{ NOMBRES[String(k)] }}</span>. Cada subpuntaje va de 1 a 10. Una alerta ROJA limita el puntaje máximo a {{ f.numero(m[0].fiabilidad.tope_con_alerta_roja, 1) }}. Las fallas «documentadas» exigen al menos dos fuentes públicas; las «editoriales» son opinión rotulada como tal.</p>
        <h2 class="mt-16 border-t border-linea pt-8 text-display-sm">Supuestos de los simuladores</h2>
        <ul class="mt-4 grid [&>li]:border-b [&>li]:border-linea [&>li]:py-3">
          <li><strong>Crédito:</strong> tasa mensual = (1 + E.A.)^(1/12) − 1; cuota = P · i / (1 − (1 + i)^−n). Tasa por defecto {{ f.pct(m[0].credito.tasa_defecto_ea) }} E.A. (estimada); usura vigente {{ f.pct(m[0].credito.tasa_usura_ea) }}.</li>
          <li><strong>Seguro todo riesgo:</strong> valor asegurado × tasa base por segmento × factores (ciudad, edad, uso, antigüedad, hurto, deducible) + componentes fijos; se muestra un rango de ±{{ Math.round(m[0].seguros.amplitud_rango * 100) }}%.</li>
          <li><strong>Mantenimiento:</strong> costo por hito de 10.000 km según el nivel de costo, con un hito mayor cada {{ f.numero(m[0].mantenimiento.hitos_mayores_cada_km) }} km.</li>
          <li><strong>Reventa:</strong> curvas de retención por etiqueta (Baja, Media, Alta depreciación), calibrables por modelo.</li>
          <li><strong>Altura:</strong> pérdida de {{ f.pct(m[0].altura.perdida_por_1000m['Atmosférico']) }} por cada 1.000 m en atmosféricos, {{ f.pct(m[0].altura.perdida_por_1000m.Turbo) }} en turbo y 0% en eléctricos.</li>
          <li><strong>Índice Rompemuelle:</strong> despeje con penalización por voladizo largo; ≥ 200 mm «pasa sin problema», 170–199 «con cuidado», 150–169 «precaución», &lt; 150 «riesgo de raspar». Con carga restamos {{ m[0].indices.rompemuelle.caida_con_carga_mm }} mm.</li>
          <li><strong>Índice de Garaje:</strong> contra una plaza de 5,00 × 2,40 m: holgado, justo, apretado o no cabe según largo y ancho con espejos.</li>
          <li><strong>Puntaje MiProximoCarro (0–100):</strong> cada dimensión se normaliza entre los autos comparados y se pondera según el perfil de uso; una alerta roja resta 35% del puntaje.</li>
        </ul>
        <h2 class="mt-16 border-t border-linea pt-8 text-display-sm">Límites de la plataforma</h2>
        <p class="mt-3">No es una cotización, ni una oferta de crédito, ni asesoría financiera. Las siluetas son esquemáticas y proporcionales, no el diseño real. Las reviews son opinión editorial basada en fuentes públicas citadas, no un diagnóstico mecánico de un vehículo en particular. Las reglas de pico y placa y las tarifas de matrícula fuera de Bogotá son ilustrativas: verifica la norma vigente de tu ciudad.</p>
        <h2 class="mt-16 border-t border-linea pt-8 text-display-sm">Vigencia de los parámetros</h2>
        <ul class="mt-4 grid gap-2 text-sm"><li v-for="(v, k) in m[0].vigencias" :key="k"><strong>{{ k }}:</strong> {{ v.vigencia }} · consultado {{ f.fecha(v.fecha_consulta) }} <a v-if="v.fuente_url" :href="v.fuente_url" class="underline" target="_blank" rel="noopener">fuente</a></li></ul>
        <h2 class="mt-16 border-t border-linea pt-8 text-display-sm">Fuentes registradas ({{ m[1].length }})</h2>
        <ul class="mt-4 grid gap-2 text-sm"><li v-for="s in m[1]" :key="s.id"><a :href="s.url" class="underline" target="_blank" rel="noopener">{{ s.titulo }}</a> <span class="text-tenue">({{ s.tipo }})</span></li></ul>
      </template>
    </EstadoCarga>
  </article>
</template>
