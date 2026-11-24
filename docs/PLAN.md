# Plan de ejecución — MiProximoCarro

Repositorio: https://github.com/ingsamuelorozco/MiProximoCarro (cuenta personal `ingsamuelorozco`, público).
Nota: el proyecto arrancó como `AutoVerdict` y se renombró a `MiProximoCarro` (el repo de GitHub también cambió de nombre).

| Hito | Entregable | Criterios de aceptación | Commit |
| --- | --- | --- | --- |
| H0 | Base del repo | `.gitignore`, MIT, `.env.example`, `CONTRIBUTING.md`, este plan | `chore:` |
| H1 | Configuración financiera | JSON en `backend/app/config/` con `vigencia`, `fuente_url`, `fecha_consulta`; sin números mágicos en código | `feat:` |
| H2 | Datos fuente | YAML por marca (18 marcas, 8–30 versiones c/u, ≥300 versiones), `fallas_patrones.yaml`, `recalls.yaml`, `actualizaciones.yaml` (≥20), `imagenes.yaml`; cobertura por segmento según especificación | `data:` |
| H3 | Seeding y control de calidad | `seed.py` idempotente valida con Pydantic, calcula derivados, crea índices y FTS5; `verify_data.py` sale ≠0 ante errores; `verify_images.py` HEAD 200 | `feat:` |
| H4 | Backend | FastAPI con todos los endpoints de la especificación, caché LRU, ETag, GZip, rate limit, errores `{codigo, mensaje, detalle}`, TRM de datos.gov.co con respaldo | `feat:` |
| H5 | Pruebas backend | pytest incluido `test_captiva_turbo_fiabilidad_baja`, financieros, comparador | `test:` |
| H6 | Frontend | Vue 3 + Vite + TS + Tailwind, todas las rutas, stores, comparador hasta 10, siluetas SVG, herramientas | `feat:` |
| H7 | Pruebas frontend | Vitest (formato, ganador, siluetas) y Playwright de humo | `test:` |
| H8 | Entrega | CI, Dockerfile, docker-compose, Makefile, README, METODOLOGIA, FUENTES, tag `v1.0.0` y release | `docs:`/`chore:` |

## Decisiones y límites conocidos

- Las cifras técnicas y los precios de vitrina de los vehículos se cargan como **estimados** (con lógica documentada) mientras no se contrasten con la ficha oficial vigente. Esto queda visible en la interfaz y en el reporte de `verify_data.py`.
- Los parámetros financieros (SOAT 2026, impuesto vehicular 2026, usura nov. 2026, combustibles nov. 2026, matrícula Bogotá 2026, TRM) se consultaron en fuentes públicas el 2026-11-13 y se citan en `docs/FUENTES.md`.
- No hay Docker en el equipo de desarrollo: el Dockerfile se entrega pero se valida solo en CI.
