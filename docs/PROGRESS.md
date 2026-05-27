# Avances del proyecto

Estado en vivo del proyecto WFC para Sudoku. Cada fase referencia el plan en [README.md](./README.md).

**Última actualización:** 2026-05-27

---

## Estado por fase

| Fase | Título | Estado |
| --- | --- | --- |
| 0 | Bootstrap del proyecto | ✅ Completa |
| 1 | Modelo de datos del Sudoku | ✅ Completa |
| 2 | Restricciones y propagación | ✅ Completa |
| 3 | Algoritmo WFC + backtracking | ⏳ Pendiente |
| 4 | Renderizado gráfico | ⏳ Pendiente |
| 5 | CLI y empaquetado | 🟡 Parcial (`show` y `validate` adelantados) |

**Tests:** 75 pasando · **Lint (ruff):** limpio · **Python:** 3.12.3 · **Venv:** `.venv/`

---

## Fase 0 — Bootstrap ✅

**Entregable cumplido:** `pytest` corre y `wfc --help` no falla.

Archivos creados:

- `pyproject.toml` — paquete `wfc 0.1.0`, src-layout, deps (`numpy`, `matplotlib`), deps de dev (`pytest`, `pytest-cov`, `ruff`), entry point `wfc = wfc.cli:main`, configs de `ruff` y `pytest` integradas.
- `Makefile` — targets `install`, `test`, `test-cov`, `lint`, `format`, `run`, `clean`.
- `.gitignore` — Python estándar (`__pycache__`, `.venv`, caches, build artifacts).
- `src/wfc/__init__.py` — expone `__version__`.
- `src/wfc/__main__.py` — habilita `python -m wfc`.
- `src/wfc/cli.py` — stub inicial con `argparse` (luego ampliado en fase 5).
- `tests/conftest.py` — vacío, listo para fixtures.
- `tests/test_smoke.py` — verifica import del paquete.

Entorno: venv creado en `.venv/` con `pip install -e ".[dev]"` tras instalar `python3-pip` y `python3-venv` vía apt.

Decisiones tomadas:
- **src-layout** (no flat). Evita import shadowing entre código local y paquete instalado.
- `pyproject.toml` con configuración completa (no stub mínimo).
- `examples/` y `tests/fixtures/` separados — humanos vs. tests.

---

## Fase 1 — Modelo de datos ✅

**Entregable cumplido:** carga de tablero desde string/archivo + impresión en consola.

Archivos creados:

- `src/wfc/board.py`:
  - Constantes `SIZE = 9`, `BOX = 3`, `ALL_VALUES = frozenset(range(1, 10))`.
  - `Cell` (dataclass): `candidates: set[int]` + `given: bool`; props `collapsed`, `value`, `entropy`.
  - `Board` (dataclass): matriz 9×9 de `Cell`.
  - Métodos: `empty`, `from_string`, `to_string`, `clone`, `entropy(r, c)`, `is_solved`, `__str__`.
  - Iteradores de unidades: `iter_cells`, `row_cells`, `col_cells`, `box_cells`, `iter_units` (27 unidades totales).
- `src/wfc/parser.py`:
  - `from_file(path)` — delega a `Board.from_string` tras leer el archivo.
- `tests/test_board.py` — 22 tests.

Decisiones tomadas:
- **`Cell` con `given: bool`** — distingue pistas iniciales de celdas resueltas por el solver (lo necesita el renderer en fase 4).
- **`candidates: set[int]`** (no bitmask). Se reconsidera si los benchmarks de fase 3 lo justifican.
- **`from_string` tolera whitespace y separadores de grid** (`|`, `+`, `-`). Esto hace que el output formateado de `show`/`generate` sea re-parseable, habilitando pipelines como `wfc generate | wfc show -`. Cualquier otro carácter sigue rechazándose.
- **`to_string` emite `0`** para celdas no colapsadas (formato canónico).
- **`is_solved`** verifica colapso completo **y** restricciones (sin duplicados por unidad).

---

## Fase 2 — Restricciones y propagación ✅

**Entregable cumplido:** propagación reduce candidatos correctamente y detecta contradicciones.

Archivos creados:

- `src/wfc/constraints.py`:
  - `ContradictionError` — excepción levantada cuando el estado deviene insoluble.
  - `peers(r, c)` — frozenset cacheado (`@cache`) con las 20 celdas peer de `(r, c)`.
  - `UNITS` — lista precomputada de las 27 unidades (9 filas + 9 columnas + 9 cajas) como coordenadas.
  - `is_consistent(board)` — verifica no-duplicados entre celdas colapsadas por unidad (sin levantar excepción).
  - `propagate(board, seed=None)` — aplica naked + hidden singles hasta punto fijo, mutando el board:
    - **Naked singles:** una celda colapsada elimina su valor de los candidatos de todos sus peers; las celdas que quedan con un candidato encolan más eliminaciones.
    - **Hidden singles:** dentro de cada unidad, si sólo una celda puede contener un valor `v`, esa celda se colapsa a `v`.
    - **Contradicción:** cualquier celda con candidatos vacíos, o cualquier unidad sin lugar para un valor, levanta `ContradictionError`.
    - `seed` opcional: si se pasa `(r, c)`, parte desde esa celda (incremental); si no, parte de todas las colapsadas (sweep inicial).
- `tests/test_constraints.py` — 19 tests.

Integración:

- `cmd_validate` en `cli.py` ahora reporta también `Consistent: True|False` usando `is_consistent(board)`.

Verificación práctica: `propagate` aplicado a `examples/easy.txt` resuelve el puzzle completo (de 30 a 81 colapsadas) sin necesidad de backtracking. Esto es esperable — los puzzles "fáciles" suelen ceder ante naked + hidden singles.

Decisiones tomadas:
- `ContradictionError` (suffix `Error` por convención Python, vs. el `Contradiction` informal del plan).
- `peers` cacheada con `@cache` (`UNITS` precomputado al import).
- `propagate` muta el board (no clona); el solver clonará antes de probar ramas.
- `seed` opcional permite tanto la inicialización (todas las givens) como propagación incremental tras un colapso del solver.

---

## Fase 5 (parcial) — CLI 🟡

**Adelantado para poder ejercitar el modelo desde la terminal antes de implementar el solver.**

Archivos creados/modificados:

- `src/wfc/cli.py` — reescrito con:
  - `_load_board(source)` — auto-detección: ruta de archivo, string de 81 chars, o `-` para stdin.
  - `cmd_show` — carga e imprime el tablero formateado.
  - `cmd_validate` — carga y reporta `Givens: N/81` y `Solved: True|False`.
  - `cmd_not_implemented` — placeholder para `solve` y `bench`.
  - Dispatch vía `subparser.set_defaults(func=...)`.
- `examples/easy.txt` — sudoku de ejemplo (30 givens).
- `tests/test_cli.py` — 7 tests (no-args, show desde string/archivo/stdin, input inválido, validate, solve stub).
- `docs/README.md` — anotación en sección 5 sobre los adelantos.

Subcomandos funcionales hoy:

```bash
wfc show <input>                       # carga + imprime
wfc validate <input>                   # carga + reporta givens y estado
wfc generate [--givens N] [--seed N]   # genera tablero válido aleatorio
             [--raw] [--save [PATH]]    # --save: guarda a archivo
```

Donde `<input>` es una ruta de archivo, un string de 81 chars, o `-` para stdin.

Stubs pendientes (esperan fase 3):

```bash
wfc solve <input> [--render PATH] [--animate PATH] [--seed N] [--verbose]
wfc bench <dir>
wfc validate <input> --unique    # chequeo de unicidad de solución
```

### Logging con verbosity (bonus, fuera del plan original)

CLI acepta flag global `-v` / `--verbose` repetible, con tres niveles:

| Flag | Nivel | Qué se muestra |
| --- | --- | --- |
| _(sin flag)_ | `WARNING` | sólo errores y warnings; output principal en stdout sin cambios. |
| `-v` | `INFO` | pasos generales: `generate_solved: seed=42`, `propagate: done in N iter — X eliminations…`, `validate: givens=30, consistent=True, solved=False`. |
| `-vv` (o más) | `DEBUG` | paso a paso: cada eliminación de candidato, cada naked/hidden single, cada transformación del generador, cada hueco cavado. |

- Logs a `stderr` (no contaminan stdout → pipelines siguen funcionando).
- Format: `[LEVEL] message`.
- Cada módulo (`wfc.constraints`, `wfc.generator`, `wfc.cli`) tiene su propio `logging.getLogger(__name__)`; CLI configura el logger raíz `wfc` para no afectar otros loggers del sistema.
- `_configure_logging` recrea el handler en cada llamada a `main()` (necesario para que pytest's `capsys` pueda interceptar el stderr correctamente entre tests).

Ejemplos:

```bash
wfc -v generate --givens 30 --seed 42 --raw     # ve los pasos del generador
wfc -vv generate --givens 30 --seed 42           # paso a paso: cada hueco, cada shuffle
wfc -v validate examples/easy.txt                # ve qué reportó validate
```

### Generador (bonus, fuera del plan original)

- `src/wfc/generator.py` — funciones `generate_solved(seed)` y `generate_puzzle(givens, seed)`.
- Algoritmo: parte del grid canónico
  `value(r, c) = ((r % 3) * 3 + r // 3 + c) % 9 + 1`
  y aplica simetrías que preservan validez — relabel de dígitos, shuffle de filas dentro de bandas, de columnas dentro de stacks, de bandas, de stacks, y transpose opcional. Cubre todo el espacio de sudokus equivalentes al canónico (~6.7×10²¹).
- `generate_puzzle` cava huecos aleatoriamente desde una solución; **no garantiza unicidad de solución** (lo verificaremos cuando exista el solver).
- `tests/test_generator.py` — 9 tests (determinismo por seed, validez de la solución, conteo de givens, consistencia entre solved/puzzle con misma seed, validación de rango).

**Persistencia (`--save`):**
- `--save PATH` — guarda el tablero en PATH (formato de 9 líneas, parent dirs auto-creados).
- `--save` sin argumento — auto-nombra en `examples/generated/`:
  - con seed: `puzzle_givens<N>_seed<S>.txt` (determinista, sobrescribe).
  - sin seed: `puzzle_givens<N>_<YYYYMMDD_HHMMSS>.txt`.
- `examples/generated/` agregado a `.gitignore`.
- Round-trip verificado: `wfc generate --save f.txt` → `wfc show f.txt` reproduce el mismo tablero.

---

## Resumen de tests (75 total)

| Archivo | Count | Cubre |
| --- | --- | --- |
| `tests/test_smoke.py` | 1 | Import del paquete + `__version__`. |
| `tests/test_board.py` | 21 | `Cell`, `Board`, parsing (zeros/dots/whitespace/inválido), round-trip, `is_solved` (vacío/completo/duplicado), `clone` independencia, `entropy`, conteo de unidades, `box_cells`, render con `__str__`, lectura desde archivo. |
| `tests/test_constraints.py` | 19 | `peers` (count 20, no-self, cobertura row/col/box), naked singles eliminación + encadenamiento, contradicciones (row/col/box/hidden), hidden singles (row/col/box + sin candidato), `is_consistent` (vacío/solved/duplicado), propagate sobre easy / solved / empty. |
| `tests/test_cli.py` | 20 | Help, `show` desde string/archivo/stdin, input inválido, `validate` (con `Consistent`), `solve` stub, `generate` (formateado/raw/con givens/inválido), `--save` (explícito/parent dirs/formato 9 líneas/round-trip/auto-path), logging (`-v`/`-vv` emisión / default sin logs). |
| `tests/test_generator.py` | 9 | `generate_solved` determinismo + validez, `generate_puzzle` conteo de givens, consistencia con solved, candidatos vacíos, casos límite (0, 81), rangos inválidos. |

---

## Cómo verificar localmente

```bash
cd ~/projects/wfc

# tests
.venv/bin/pytest -q

# lint
.venv/bin/ruff check src tests

# demo CLI
.venv/bin/wfc show examples/easy.txt
.venv/bin/wfc validate examples/easy.txt
.venv/bin/wfc generate --seed 42
.venv/bin/wfc generate --givens 30 --seed 42
.venv/bin/wfc generate --seed 42 --raw | .venv/bin/wfc validate -
```

---

## Decisiones pendientes para fases futuras

Las tres preguntas abiertas del plan que aún no se han cerrado:

1. **WFC puro vs. WFC + backtracking vs. híbrido** — define el carácter de la fase 3.
2. **Backend gráfico** — `matplotlib` (default propuesto) vs. `pygame`.
3. **Heurísticas de búsqueda** — sólo MRV (default propuesto) vs. MRV + LCV.

---

## Próximos pasos

1. **Cerrar decisión sobre variante de WFC** antes de empezar fase 3 (pregunta abierta — recomendación: WFC + backtracking pragmático, ya que toda la maquinaria está lista: `propagate` + `clone` + `ContradictionError`).
2. **Cerrar decisión sobre heurísticas** (MRV solo, o MRV + LCV).
3. **Fase 3 — solver:** colapso por MRV + propagación + (según decisión) backtracking. Tests de los 9 casos del plan (`easy`, `medium`, `hard`, `expert`, `minimal_17`, etc.). Estructura: `src/wfc/solver.py` con `solve(board) -> Board | None`.
4. **Fase 4 — renderer:** decisión backend (matplotlib default), `src/wfc/renderer.py` con `render_board` y `render_solution`.
5. **Fase 5 (cierre):** wirear `cmd_solve` y `cmd_bench` a la implementación real; añadir `validate --unique` cuando el solver esté listo.

---

## Resumen de la sesión 2026-05-27

**Cerradas en esta sesión:** fases 0, 1, 2 + parcial de 5.

**Bonus implementados (fuera del plan original):**
- Generador de tableros válidos vía simetrías (`generate_solved`, `generate_puzzle`).
- Subcomando `wfc generate` con `--givens`, `--seed`, `--raw`, `--save [PATH]`.
- Persistencia auto-nombrada en `examples/generated/` (gitignored).
- Parser tolerante a separadores `|`, `+`, `-` → habilita pipelines `wfc generate | wfc show -`.
- Logging con verbosity en 3 niveles (`-v`, `-vv`).

**Estado del repo al cierre:**
- 75 tests passing.
- Ruff sin warnings.
- Estructura `src/wfc/` lista para fase 3: `board`, `parser`, `constraints`, `generator`, `cli`. Falta `solver.py` y `renderer.py`.

**Cómo retomar:**
1. Activar venv: `source ~/projects/wfc/.venv/bin/activate` (o usar `.venv/bin/...`).
2. Verificar baseline: `pytest -q && ruff check src tests`.
3. Cerrar las 2 decisiones pendientes (variante + heurísticas).
4. Arrancar fase 3 creando `src/wfc/solver.py`. Importar `propagate`, `ContradictionError`, `is_consistent` de `constraints`. El solver clonará el board (`Board.clone`) antes de probar cada candidato (el `propagate` actual muta).
