# MiProximoCarro

**Compra el carro, no la promesa.** La plataforma que le dice a un comprador colombiano la verdad completa sobre un carro antes de pagarlo: qué tan grande es en la realidad, cuánto cuesta de verdad tenerlo (puesta en calle, crédito, seguro, combustible, mantenimiento, reventa) y qué se le suele dañar.

- 2.089 versiones de 26 marcas (2000–2026), con reseña honesta por versión.
- Comparador de hasta 10 autos con ganador automático por fila, marcador, Puntaje MiProximoCarro por perfil y siluetas SVG a escala (lateral, planta y frontal) con Índice Rompemuelle e Índice de Garaje.
- Motor financiero colombiano: SOAT 2026, matrícula, impuesto vehicular proporcional, crédito (cuota fija, balón, abonos), seguro todo riesgo por rango, costo total de propiedad, reventa y "¿qué carro me alcanza?".
- Reviews con fallas documentadas (dos o más fuentes), recalls, checklist de usado y alternativas.

## Inicio rápido local

Requisitos: Python 3.12 y Node 20 o superior.

```bash
git clone https://github.com/ingsamuelorozco/MiProximoCarro.git
cd MiProximoCarro
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
python scripts/seed.py              # opcional: db/cars.db ya viene generada
uvicorn backend.app.main:app --reload --port 8000
# en otra terminal
cd frontend && npm install && npm run dev
```

Abre http://localhost:5173 (la API y su documentación OpenAPI quedan en http://localhost:8000/docs).

**Un solo proceso:** `cd frontend && npm run build`, luego `uvicorn backend.app.main:app --port 8000` y abre http://localhost:8000: FastAPI sirve el build.

### Docker

```bash
docker compose up --build   # http://localhost:8000
```

### Pruebas

```bash
pip install -r backend/requirements-dev.txt
python scripts/verify_data.py && python scripts/verify_images.py
pytest -q
cd frontend && npm run test && npm run build && npx playwright install chromium && npm run test:e2e
```

## Estructura

```
backend/app/        FastAPI: main, db, schemas, routers/, services/, config/*.json (tarifas con vigencia y fuente)
backend/tests/      pytest (incluye test_captiva_turbo_fiabilidad_baja)
data/               fuente de verdad editable: vehiculos/<marca>.yaml, fallas_patrones, recalls, actualizaciones, imagenes, fuentes
scripts/            seed.py, verify_data.py, verify_images.py
db/cars.db          SQLite (WAL, FTS5) ya generada
frontend/           Vue 3 + Vite + TypeScript + Tailwind + Pinia
docs/               PLAN.md, METODOLOGIA.md, FUENTES.md
```

## Endpoints

`GET /api/salud` · `GET /api/catalogo/{marcas,modelos,anios,versiones}` · `GET /api/vehiculos` (búsqueda FTS5 y filtros) · `GET /api/vehiculos/{id|slug}` · `GET /api/vehiculos/{id}/rivales` · `POST /api/comparar` · `GET /api/fiabilidad` · `GET /api/fiabilidad/{id|slug}` · `GET /api/actualizados` · `GET /api/actualizados/{id}` · `POST /api/financiero/{puesta-en-calle,credito,seguro,tco,reventa,asequibilidad}` · `GET /api/config/{trm,ciudades,perfiles,metodologia,fuentes,imagenes}`.

## Cómo actualizar los datos

1. Edita el YAML de la marca en `data/vehiculos/` (cada modelo tiene su base técnica, su reseña y sus versiones).
2. Si confirmas un dato con una fuente pública, agrégala en `data/fuentes.yaml` y lista el campo en `campos_verificados`.
3. Las tarifas viven en `backend/app/config/*.json` con `vigencia`, `fuente_url` y `fecha_consulta`.
4. Ejecuta `python scripts/seed.py && python scripts/verify_data.py`.

Metodología completa en [docs/METODOLOGIA.md](docs/METODOLOGIA.md) y fuentes en [docs/FUENTES.md](docs/FUENTES.md). Para contribuir, lee [CONTRIBUTING.md](CONTRIBUTING.md).

## Portada

La barra superior, el hero, el buscador rápido y la sección de características se describen en [docs/LANDING.md](docs/LANDING.md). Los créditos de las imágenes están en [CREDITS.md](CREDITS.md).

## Aviso

Precios referenciales y sujetos a cambio. **No es una cotización ni asesoría financiera.** Las fichas técnicas y los precios de vitrina de la versión 1.0 están marcados como *estimados* hasta contrastarlos con la ficha oficial vigente. Las reviews son opinión editorial basada en fuentes públicas citadas, no un diagnóstico mecánico de un vehículo en particular.

Licencia MIT.
