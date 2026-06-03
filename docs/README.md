# Plan de trabajo — Wave Function Collapse (engine genérico + adapter Sudoku)

## 1. Visión y alcance

Este proyecto implementa el algoritmo **Wave Function Collapse (WFC)** como un **engine reutilizable** para generación procedural y resolución de problemas tipo CSP (Constraint Satisfaction Problem).

WFC fue diseñado originalmente (Maxim Gumin, 2016) para generación procedural — texturas, mapas de tiles, dungeons. Su mecánica central — "celdas en superposición, observación de la celda de menor entropía, colapso, propagación de restricciones" — se aplica también a Sudoku y otros CSPs.

**El proyecto separa explícitamente dos capas:**

- **Engine genérico (`wfc.core`)** — abstracciones del algoritmo: wave, restricciones, propagación, política de resolución, selector de celdas, muestreador de valores. No sabe nada de sudokus, tiles ni dungeons.
- **Adapters (`wfc.sudoku`, futuros `wfc.tiles`, `wfc.dungeons`)** — implementaciones específicas de un dominio: cómo se ven las variables, qué restricciones aplican, cómo se renderiza.

Sudoku es la **primera aplicación** y guía el diseño del engine. Aplicaciones posteriores reutilizan el core sin tocarlo.

Lenguaje: **Python 3.11+**.

---

## 2. Arquitectura por capas

```
~/projects/wfc/
├── README.md
├── pyproject.toml
├── docs/
│   ├── README.md              # (este documento)
│   └── PROGRESS.md            # Bitácora de fases cerradas
├── src/
│   └── wfc/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py             # CLI: despacha a subcomandos por adapter
│       ├── core/              # ENGINE GENÉRICO — no sabe de sudoku
│       │   ├── __init__.py
│       │   ├── exceptions.py  # ContradictionError
│       │   ├── wave.py        # (fase 3b) Wave: variables con dominios finitos
│       │   ├── constraint.py  # (fase 3b) Constraint Protocol
│       │   ├── engine.py      # (fase 3b) loop observe/collapse/propagate
│       │   ├── selector.py    # (fase 3b) CellSelector — entropía mínima default
│       │   ├── sampler.py     # (fase 3b) ValueSampler — uniforme / con pesos
│       │   └── policy.py      # (fase 3b/3c) ResolutionPolicy: Backtrack / Restart / Hybrid
│       └── sudoku/            # ADAPTER 1 — específico de Sudoku 9×9
│           ├── __init__.py
│           ├── board.py       # Cell, Board (modelo de datos)
│           ├── constraints.py # AllDifferent en filas/cols/cajas, propagate
│           ├── generator.py   # Generador de tableros válidos
│           ├── parser.py      # Lectura desde string/archivo
│           ├── adapter.py     # (fase 3b) Glue Board ↔ Wave
│           └── renderer.py    # (fase 4) Renderizado matplotlib
├── tests/
│   ├── conftest.py
│   ├── test_smoke.py
│   ├── core/                  # (fase 3b) Tests del engine genérico
│   └── sudoku/                # Tests del adapter sudoku
│       ├── test_board.py
│       ├── test_constraints.py
│       ├── test_generator.py
│       ├── test_cli.py
│       └── test_solver.py     # (fase 3b)
└── examples/
    ├── easy.txt
    ├── medium.txt
    └── generated/             # Tableros generados con --save
```

**Principio:** una aplicación nueva (tiles, dungeons) se agrega creando un nuevo subpaquete `adapters/<dominio>/` sin modificar `core/` ni `sudoku/`.

---

## 3. Fases de desarrollo

### Fase 0 — Bootstrap del proyecto ✅ CERRADA

Estructura, dependencias, herramientas. Ver `docs/PROGRESS.md`.

### Fase 1 — Modelo de datos del Sudoku ✅ CERRADA

`Cell`, `Board`, `parser`. Ver `docs/PROGRESS.md`.

### Fase 2 — Restricciones y propagación (sudoku) ✅ CERRADA

`peers`, `UNITS`, `propagate` con naked + hidden singles, `ContradictionError`. Ver `docs/PROGRESS.md`.

### Fase 3 — Refactor a arquitectura por capas + solver

Esta fase se subdivide:

#### Fase 3a — Refactor estructural (sin nueva funcionalidad)

**Objetivo:** establecer la separación core/adapter sin romper nada.

- Crear `src/wfc/core/` con `exceptions.py` (`ContradictionError`).
- Mover `board.py`, `constraints.py`, `generator.py`, `parser.py` a `src/wfc/sudoku/`.
- `wfc.sudoku.constraints` re-exporta `ContradictionError` desde `wfc.core.exceptions` para compatibilidad con tests.
- Reorganizar `tests/` en subcarpetas `tests/sudoku/` (y `tests/core/` vacía para futuro).
- Actualizar imports en CLI y tests.
- **No tocar la lógica funcional.** Los 75 tests deben seguir verdes; ruff limpio.

**Entregable:** `pytest -q` con 75 verdes en la nueva estructura; commit dedicado.

#### Fase 3b — Engine WFC genérico + adapter Sudoku

**Objetivo:** construir el engine y adaptar sudoku para usarlo.

Componentes del **core**:

- `core/wave.py`:
  - `Wave` Protocol — abstracción de "colección de variables con dominios finitos".
  - Operaciones: `variables()`, `domain(var)`, `is_collapsed(var)`, `entropy(var)`, `clone()`, `is_fully_collapsed()`.
- `core/constraint.py`:
  - `Constraint` Protocol — `propagate(wave, recently_collapsed)` aplicado tras un colapso. El adapter aporta las constraints concretas.
- `core/selector.py`:
  - `CellSelector` Protocol — elige qué variable colapsar.
  - Implementación default: `LowestEntropySelector` (MRV generalizado; rompe empates por orden estable o aleatorio con seed).
- `core/sampler.py`:
  - `ValueSampler` Protocol — elige qué valor probar dentro del dominio.
  - Implementación default: `UniformSampler` (uniforme dentro del dominio).
  - Extensible: `WeightedSampler` (para tiles con pesos), hook para LCV opcional.
- `core/policy.py`:
  - `ResolutionPolicy` Protocol — qué hacer ante contradicción.
  - Implementación primera: `BacktrackPolicy` (deshace última decisión).
  - (fase 3c) `RestartPolicy`, `HybridPolicy`.
- `core/engine.py`:
  - `solve(wave, constraints, selector, sampler, policy) -> Wave | None`.
  - Loop: propagate inicial → observe → collapse → propagate → repeat. Ante contradicción, delega en policy.
  - Emite eventos (generator) para instrumentación y visualización: `Observed(var)`, `Collapsed(var, value)`, `Propagated(eliminations)`, `Contradicted`, `Backtracked`.

Componentes del **adapter sudoku**:

- `sudoku/adapter.py`:
  - `BoardWave` — implementa el protocol `Wave` sobre `Board` (o reemplaza `Board` con uso directo).
  - `SudokuConstraint` — implementa `Constraint` con la propagación actual (naked + hidden singles).
- `sudoku/solver.py`:
  - Función `solve(board) -> Board | None` que arma el engine con defaults sudoku-friendly y devuelve la solución.
- CLI: `wfc solve <input>` operativo.

**Decisiones tomadas en esta fase:**
- **Selector default:** entropía mínima (MRV generalizado). Sin LCV en value-ordering inicial — se agrega como hook opcional sólo si benchmarks de sudoku lo justifican.
- **Policy default:** backtracking (toda la maquinaria ya existe: clone + ContradictionError).
- **Estructura de candidatos:** `set[int]` — se reconsidera con bitmasks si los benchmarks lo exigen.

**Entregable:** `wfc solve examples/easy.txt` resuelve; tests del engine genérico (con un mock adapter mínimo) + tests del adapter sudoku.

#### Fase 3c — Restart policy y benchmarking

**Objetivo:** segunda implementación de `ResolutionPolicy` y comparación.

- `core/policy.py`: `RestartPolicy` y `HybridPolicy`.
- `wfc bench` operativo: corre todos los tableros de `examples/` con cada policy y reporta tiempos/backtracks/restarts.
- Decidir el default para sudoku en base a benchmarks.

**Entregable:** `wfc bench examples/` produce tabla comparativa.

---

### Fase 4 — Visualización interactiva (web)

**Decisión:** la visualización es una **app web** (FastAPI + HTML/JS vanilla), no matplotlib. Razones: no requiere display server (funciona en WSL2 sin configuración), interactiva por naturaleza, expone todas las funcionalidades de la CLI en el navegador, y desacopla velocidad de cómputo de velocidad de animación. matplotlib queda como opción futura para export estático (PNG/GIF) si se necesita.

#### Fase 4a — Instrumentación del engine con event stream ✅ CERRADA

- `core/events.py`: `Observed`, `Collapsed`, `Backtracked` (con `undid_vars`), `Solved`, `Contradiction`.
- `Constraint.propagate(on_event)` emite `Collapsed` durante naked/hidden singles.
- `BacktrackPolicy.solve(on_event)` emite `Observed`, `Collapsed` directo, `Backtracked`, `Solved`, `Contradiction`.
- `sudoku.solver.solve_with_events(board, seed) -> (Board | None, list[Event])` captura todo.

#### Fase 4b — Web app ✅ CERRADA

- `wfc.web/`: FastAPI app con endpoints `/api/health`, `/api/generate`, `/api/validate`, `/api/solve`. Modelos Pydantic con discriminador `type` en los eventos.
- Frontend: HTML + CSS + JS vanilla (sin build pipeline) en `wfc/web/static/`. Grilla 9×9 CSS, slider de delay, botones Generate/Solve/Stop/Reset/Validate, textarea para pegar/editar tableros.
- Animación: el cliente recibe la lista completa de eventos en `POST /api/solve` y los reproduce con `setInterval(delay)`. Cada Collapsed pinta celda con flash; Observed pone outline amarillo; Backtracked hace flash rojo y limpia `undid_vars`; Solved tinta verde el tablero completo.
- CLI: `wfc serve [--host H] [--port P] [--reload]` lanza uvicorn.

**Entregable:** `wfc serve` abre el visualizador en `http://localhost:8000`.

#### Fase 4c (futuro, opcional) — Export estático con matplotlib

- `sudoku/renderer.py`: `render(board, path)` produce PNG/SVG; `render_steps(events, path)` genera GIF/MP4 desde el event stream.
- Útil para incluir en docs o compartir resoluciones sin el server.

---

### Fase 5 — CLI y empaquetado

**Estado actual:** parcial.

- ✅ `wfc show <input>`
- ✅ `wfc validate <input>`
- ✅ `wfc generate [--givens N] [--seed N] [--raw] [--save [PATH]]`
- ⏳ `wfc solve <input> [--render <path>] [--animate <path>] [--seed N] [--policy backtrack|restart] [--verbose]` (fase 3b/3c/4)
- ⏳ `wfc bench <dir>` (fase 3c)
- ✅ Logging global `-v` / `-vv`
- ✅ Entry point `wfc` en `pyproject.toml`.

---

## 4. Plan de pruebas

### Tests existentes (75 verdes)

Cubren fases 0/1/2 + CLI parcial. Se reorganizan en `tests/sudoku/`.

### Tests del engine (fase 3b) — `tests/core/`

- `test_wave.py`: una implementación mock mínima (e.g. variables en lista, dominios `set[int]`) satisface el protocol. Operaciones básicas (clone, entropy, is_fully_collapsed).
- `test_engine.py`: con un constraint trivial y un wave de 3-4 variables, el engine resuelve, detecta contradicción, hace backtracking.
- `test_selector.py`: `LowestEntropySelector` elige correctamente; rompe empates de forma determinista con seed.
- `test_sampler.py`: `UniformSampler` recorre el dominio; con seed es determinista.
- `test_policy.py`: `BacktrackPolicy` reintenta con otro valor; falla cuando el dominio se agota.

### Tests del adapter sudoku (fase 3b en adelante) — `tests/sudoku/`

- `test_solver.py` (fase 3b):

  | Caso | Tipo | Qué prueba |
  | --- | --- | --- |
  | `easy_1` | ≥45 pistas | Resuelto sin backtracking. |
  | `medium_1` | medio | Pocas decisiones. |
  | `hard_1` | difícil | Backtracking moderado. |
  | `expert_1` | AI Escargot | Stress test. |
  | `minimal_17` | 17 pistas | Solución única encontrada. |
  | `multiple_solutions` | <17 pistas | Devuelve alguna válida; `validate` reporta no-único. |
  | `unsolvable` | Contradicción inicial | Devuelve `None`. |
  | `already_solved` | Completo correcto | Sin cambios. |
  | `invalid_complete` | Completo con duplicado | Devuelve `None`. |

  Aserciones: solución válida (filas/cols/cajas = `{1..9}`); pistas preservadas; determinismo bajo `--seed`.

- `test_renderer.py` (fase 4): PNG no vacío, dimensiones esperadas, N frames en `render_steps`.

### Integración end-to-end

`subprocess` invocando la CLI con tableros de `examples/`.

---

## 5. Hitos

1. **Hito 1 — Datos:** fases 0–1. ✅
2. **Hito 2 — Lógica básica:** fase 2. ✅
3. **Hito 3a — Refactor:** estructura core/adapter, 75 tests verdes. ⏳ (en curso)
4. **Hito 3b — Solver:** engine genérico + sudoku resuelve easy/medium/hard.
5. **Hito 3c — Policies:** backtrack + restart + benchmark.
6. **Hito 4 — Visualización:** matplotlib estático + GIF.
7. **Hito 5 — UX:** CLI completa, animación, segunda aplicación (tiles) como prueba de reutilización.

---

## 6. Decisiones técnicas (consolidadas)

- **Variante WFC:** `ResolutionPolicy` pluggable. Default sudoku: backtracking. Restart se agrega en 3c para validar la reutilización.
- **Heurística de selección:** entropía mínima en el core (universal a WFC). LCV no se implementa por defecto; queda como hook opcional en el sampler si benchmarks lo justifican.
- **Muestreo de valores:** uniforme por defecto. `WeightedSampler` para aplicaciones futuras con pesos por estado (tiles).
- **Backend gráfico (sudoku):** matplotlib estático + GIF. Interactivo (matplotlib animation o pygame) se agrega con backend separado.
- **Estructura de candidatos:** `set[int]` por claridad; bitmask si benchmarks lo exigen.
- **Aleatoriedad:** seed fija en tests; `--seed` en CLI.
- **Eventos del engine:** generator de eventos tipados — permite instrumentación, logs y animación desacopladas del loop.

---

## 7. Riesgos y mitigaciones

- **Sobreingeniería del engine genérico:** mitigar con regla "primero hacerlo funcionar para sudoku, abstraer sólo lo que la segunda aplicación necesite". No inventar Protocols sin un segundo cliente real en mente.
- **Backtracking explosivo en casos extremos:** propagación más fuerte (naked pairs, X-wing) antes que más profundidad.
- **Tests lentos en CI:** marcar pesados como `slow`, excluir del run por defecto.
- **Acoplamiento renderer ↔ solver:** el engine emite eventos; el renderer los consume. Cero acoplamiento directo.
