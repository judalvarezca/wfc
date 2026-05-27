# Plan de trabajo — Wave Function Collapse para resolución de Sudokus

## 1. Resumen

Este proyecto implementa el algoritmo **Wave Function Collapse (WFC)** aplicado a la resolución de Sudokus 9×9. Cada celda del tablero se modela como una "función de onda" en superposición de los valores `{1..9}`; el algoritmo colapsa iterativamente la celda de menor entropía y propaga las restricciones (fila, columna y caja 3×3) hasta resolver el tablero o detectar contradicción (en cuyo caso se hace backtracking).

El proyecto se desarrolla en **Python 3.11+** y se organiza en fases incrementales: modelo de datos → algoritmo → visualización → pruebas → CLI.

---

## 2. Estructura del repositorio

```
~/projects/wfc/
├── README.md                  # Descripción de alto nivel del repo
├── pyproject.toml             # Configuración del paquete (deps, ruff, pytest)
├── docs/
│   └── README.md              # (este documento) Plan de trabajo
├── src/
│   └── wfc/
│       ├── __init__.py
│       ├── board.py           # Modelo de tablero y estado de celdas
│       ├── constraints.py     # Restricciones (fila/columna/caja)
│       ├── solver.py          # Núcleo del algoritmo WFC + backtracking
│       ├── renderer.py        # Renderizado gráfico (matplotlib / pygame)
│       ├── parser.py          # Lectura de tableros (string, archivo)
│       └── cli.py             # Punto de entrada en línea de comandos
├── tests/
│   ├── conftest.py
│   ├── fixtures/              # Tableros de prueba (.txt / .json)
│   ├── test_board.py
│   ├── test_constraints.py
│   ├── test_solver.py
│   └── test_renderer.py
└── examples/
    ├── easy.txt
    ├── medium.txt
    ├── hard.txt
    └── expert.txt
```

---

## 3. Fases de desarrollo

### Fase 0 — Bootstrap del proyecto

**Objetivo:** dejar el entorno y la estructura listos para iterar.

- Inicializar `pyproject.toml` con dependencias: `numpy`, `matplotlib`, `pytest`, `pytest-cov`, `ruff`.
- Configurar `ruff` para linting/formato y `pytest` con cobertura mínima.
- Crear la estructura de carpetas (`src/wfc`, `tests`, `examples`).
- Añadir `Makefile` (o scripts) para `make test`, `make lint`, `make run`.

**Entregable:** `pytest` corre (sin tests aún) y `python -m wfc --help` no falla.

---

### Fase 1 — Modelo de datos del Sudoku

**Objetivo:** representar el tablero y el estado de superposición.

- `board.py`: clase `Board` con:
  - Matriz 9×9 de `Cell`, donde cada `Cell` mantiene un `set[int]` con los candidatos posibles.
  - Una celda "colapsada" es aquella con un único candidato.
  - Métodos: `from_string`, `to_string`, `clone`, `is_solved`, `entropy(r, c)`.
- `parser.py`: aceptar formatos comunes:
  - Cadena plana de 81 caracteres (`0` o `.` = vacío).
  - Archivo de texto con 9 líneas de 9 dígitos.
- Validación de entrada: tamaño correcto, sólo dígitos `0-9` o vacíos.

**Entregable:** se puede cargar un tablero desde string/archivo e imprimirlo en consola.

---

### Fase 2 — Restricciones y propagación

**Objetivo:** implementar el motor que reduce candidatos.

- `constraints.py`:
  - `peers(r, c) -> set[(r, c)]`: devuelve las 20 celdas que comparten fila, columna o caja con `(r, c)`.
  - `propagate(board, r, c)`: tras colapsar `(r, c)` a un valor `v`, elimina `v` del conjunto de candidatos de todos sus peers; si algún peer queda con un único candidato, propaga recursivamente (constraint propagation / AC-3 simplificado).
  - Detección de contradicción: una celda con `candidatos = ∅` señala inconsistencia.
- Estrategias adicionales (incrementales, opcionales por fase):
  - **Naked singles** (incluida en la propagación básica).
  - **Hidden singles** dentro de fila/columna/caja.

**Entregable:** dado un tablero parcialmente resuelto, la propagación reduce candidatos correctamente y detecta contradicciones.

---

### Fase 3 — Algoritmo WFC + backtracking

**Objetivo:** el solver principal.

- `solver.py`: función `solve(board) -> Board | None`:
  1. Propagar restricciones iniciales sobre todas las pistas dadas.
  2. Si el tablero está resuelto → retornar.
  3. Si hay contradicción → retornar `None`.
  4. Elegir la celda no colapsada de **menor entropía** (regla MRV — Minimum Remaining Values; rompe empates aleatoriamente o por orden lexicográfico).
  5. Para cada candidato `v` de esa celda (ordenado opcionalmente por heurística LCV — Least Constraining Value):
     - Clonar el tablero, colapsar a `v`, propagar, recursión.
     - Si la recursión devuelve solución, propagar hacia arriba.
  6. Si ningún candidato funciona → retornar `None` (backtrack).
- Instrumentación: contadores de `collapses`, `propagations`, `backtracks` y tiempo total para evaluar rendimiento.
- Modo "step" que produce un generador con cada estado intermedio (útil para visualización animada).

**Entregable:** `solve()` resuelve los tableros de `examples/` y reporta métricas.

---

### Fase 4 — Renderizado gráfico

**Objetivo:** visualizar el tablero y la ejecución del algoritmo.

- `renderer.py` con **dos backends** (elegir uno; matplotlib como default por simplicidad):
  - **Estático (matplotlib):** rejilla 9×9, bordes gruesos cada 3 celdas, pistas en negrita, valores resueltos en color distinto, candidatos pequeños en celdas no colapsadas.
  - **Animado:** consume el generador `step` del solver y produce un GIF/MP4 (o ventana interactiva) mostrando colapsos y propagaciones.
- API:
  - `render_board(board, path=None)` — guarda PNG o muestra ventana.
  - `render_solution(initial, steps, path)` — anima la resolución.
- Codificación de colores:
  - Pistas iniciales: negro.
  - Celdas colapsadas por el solver: azul.
  - Celdas en propagación reciente: resaltado amarillo (sólo en animación).
  - Contradicción: rojo.

**Entregable:** comando `python -m wfc solve examples/medium.txt --render out.png` genera la imagen del tablero resuelto.

---

### Fase 5 — CLI y empaquetado

**Objetivo:** que sea ejecutable cómodamente.

- `cli.py` con `argparse`:
  - `wfc show <input>` — carga y pinta el tablero (acepta archivo, string de 81 chars o `-` para stdin). *(adelantado tras fase 1.)*
  - `wfc validate <input>` — reporta givens y estado de resolución; en su forma completa chequea unicidad de solución. *(parcial; unicidad requiere solver de fase 3.)*
  - `wfc generate [--givens N] [--seed N] [--raw] [--save [PATH]]` — genera un tablero válido aleatorio (solución completa por defecto, o puzzle con N pistas). Con `--save` guarda en archivo (con `PATH` explícito o auto-nombrado en `examples/generated/`). *(adelantado; unicidad de solución se verifica en fase 3.)*
  - `wfc solve <input> [--render <path>] [--animate <path>] [--seed N] [--verbose]`
  - `wfc bench <dir>` (corre todos los ejemplos y reporta tiempos).
- Entry point en `pyproject.toml` (`[project.scripts] wfc = "wfc.cli:main"`).

**Entregable:** `pip install -e .` y luego `wfc solve …` funciona.

---

## 4. Plan de pruebas

Cada fase incluye sus tests; el conjunto crece de forma acumulativa.

### 4.1 Tests unitarios — `test_board.py`

- Carga desde string de 81 caracteres con `0` y con `.`.
- Rechazo de inputs inválidos (longitud, caracteres).
- Round-trip `from_string` → `to_string`.
- `is_solved` falso en tableros con vacíos, verdadero en uno completamente correcto.
- `clone` produce copia independiente (mutar uno no afecta al otro).

### 4.2 Tests unitarios — `test_constraints.py`

- `peers(0,0)` devuelve exactamente 20 celdas conocidas.
- Propagar un colapso elimina el valor de todos los peers.
- Propagar genera cadenas de naked singles correctas.
- Tablero con contradicción explícita es detectado.
- Hidden singles: dado un escenario donde sólo una celda de un bloque puede contener `7`, esa celda se colapsa.

### 4.3 Tests del solver — `test_solver.py`

Casos por dificultad (en `tests/fixtures/`):

| Caso | Tipo | Qué prueba |
| --- | --- | --- |
| `easy_1` | Sudoku fácil (≥45 pistas) | Se resuelve sin backtracking. |
| `medium_1` | Sudoku medio | Se resuelve con propagación + pocas decisiones. |
| `hard_1` | Sudoku difícil | Requiere backtracking moderado. |
| `expert_1` | "AI Escargot" (uno de los más difíciles conocidos) | Stress test de backtracking. |
| `minimal_17` | Sudoku con 17 pistas (mínimo conocido) | El solver llega a una única solución. |
| `multiple_solutions` | Tablero con <17 pistas y múltiples soluciones | `solve` retorna alguna válida; `validate` reporta no-único. |
| `unsolvable` | Tablero con contradicción inicial | `solve` retorna `None`. |
| `already_solved` | Tablero completo y correcto | Devuelto sin cambios. |
| `invalid_complete` | Tablero completo pero con un duplicado | `solve` retorna `None`. |

Aserciones en cada caso:
- Solución válida: cada fila, columna y caja contiene `{1..9}` exactamente.
- Las pistas iniciales se preservan.
- Determinismo bajo `--seed` fijo.

### 4.4 Tests de rendimiento (smoke) — `test_solver.py`

- Cada caso resuelto en menos de un umbral razonable (`easy` < 50 ms, `expert` < 5 s en CI). Marcar como `pytest.mark.slow` los que excedan.

### 4.5 Tests de renderizado — `test_renderer.py`

- `render_board` produce un archivo PNG no vacío y con dimensiones esperadas.
- No se hace comparación pixel-perfect; se valida que el archivo se crea y que `render_solution` produce N frames esperados.

### 4.6 Integración

- Test end-to-end vía CLI con `subprocess`: `wfc solve examples/easy.txt` retorna código 0 y stdout con tablero resuelto.

---

## 5. Hitos y orden de ejecución

1. **Hito 1 — Datos:** Fases 0–1 cerradas + tests de board pasando.
2. **Hito 2 — Lógica:** Fase 2 + tests de constraints.
3. **Hito 3 — Solver funcional:** Fase 3 resolviendo `easy/medium/hard`.
4. **Hito 4 — Stress:** Solver pasa `expert` y `minimal_17`.
5. **Hito 5 — Visualización:** Fase 4 con renderizado estático.
6. **Hito 6 — UX:** Fase 5 (CLI) + animación + benchmarks.

---

## 6. Decisiones técnicas a confirmar

- **Backend gráfico:** `matplotlib` (estático y GIF vía `FuncAnimation`) vs. `pygame` (interactivo). Default propuesto: matplotlib.
- **Estructura de candidatos:** `set[int]` (claridad) vs. bitmask `int` de 9 bits (rendimiento). Default propuesto: `set` en primera iteración, optimizar si el benchmark lo exige.
- **Estrategia de búsqueda:** sólo MRV vs. MRV + LCV. Default: MRV; añadir LCV si los tiempos del caso `expert` lo justifican.
- **Aleatoriedad:** semilla fija por defecto para tests deterministas; flag `--seed` en CLI.

---

## 7. Riesgos y mitigaciones

- **Backtracking explosivo en casos extremos:** mitigar con propagación más fuerte (hidden singles, naked pairs) antes de añadir más profundidad de búsqueda.
- **Tests lentos en CI:** marcar casos pesados como `slow` y excluirlos del run por defecto.
- **Acoplamiento renderer ↔ solver:** mantener el solver agnóstico (emite estados via generator); el renderer los consume.
