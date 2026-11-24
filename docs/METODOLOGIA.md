# Metodología

## Estados del dato
Cada cifra lleva fuente, fecha y estado: `verificado`, `estimado` o `no_disponible`. En la versión 1.0 **todas las fichas técnicas y los precios de vitrina están marcados como estimados** (`campos_estimados`): provienen de una base editorial de fichas públicas y deben contrastarse con la ficha oficial vigente en Colombia. Los parámetros financieros (SOAT, usura, combustibles, matrícula de Bogotá, impuesto vehicular, TRM) sí se consultaron en fuentes oficiales el 2026-11-13 (ver [FUENTES.md](FUENTES.md)).

Reglas de estimación (`data/defaults.yaml`): ancho con espejos = ancho sin espejos + 190 mm; voladizos repartidos 46/54; consumo ciudad = mixto × 0,84 y carretera = mixto × 1,20 (híbridos: 1,10 y 0,95); consumo real = mixto × 0,86 cuando no hay dato editorial; CO₂ = 2.310 g/L (gasolina) o 2.640 g/L (diésel) ÷ km/l.

## Precios
Precio de vitrina: estimación editorial (fuente `editorial-precio`). Puesta en calle = precio base + SOAT + matrícula (derechos, placas, RUNT e impuesto vehicular proporcional a los meses restantes). Avalúo estimado = precio ÷ 1,19.

## Puntaje de fiabilidad
Puntaje = 35% motor y transmisión + 20% quejas documentadas + 15% repuestos y red + 10% recalls + 10% costo de reparaciones + 10% eléctrica y electrónica. Una alerta ROJA limita el máximo a 4,0. Las fallas "documentadas" tienen dos o más fuentes; las "editoriales" son opinión rotulada.

## Simuladores
- Crédito: i = (1 + EA)^(1/12) − 1; cuota = P·i / (1 − (1 + i)^−n); balón con valor presente del pago final.
- Seguro todo riesgo: valor asegurado × tasa por segmento × factores + fijos; rango ±18%.
- TCO: energía, mantenimiento por hitos de 10.000 km, seguro, SOAT, impuesto (sobre avalúo depreciado), RTM desde el año 6, intereses, menos la reventa.
- Altura: −10% por cada 1.000 m en atmosféricos, −3% en turbo, 0% en eléctricos.
- Índices Rompemuelle y de Garaje: umbrales en `backend/app/config/indices.json`.
- Puntaje MiProximoCarro: dimensiones normalizadas entre los autos comparados, ponderadas por perfil (`perfiles.json`); la alerta roja resta 35%.

## Límites
Siluetas esquemáticas, no el diseño real. Las reglas de pico y placa y la matrícula fuera de Bogotá son ilustrativas. No es una cotización ni una oferta de crédito.
