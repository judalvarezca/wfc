"use strict";

const SIZE = 9;
const FLASH_MS = 180;

const boardEl = document.getElementById("board");
const givensEl = document.getElementById("givens");
const seedEl = document.getElementById("seed");
const delayEl = document.getElementById("delay");
const delayLabel = document.getElementById("delay-label");
const statusEl = document.getElementById("status");
const validateOut = document.getElementById("validate-out");
const boardInput = document.getElementById("board-input");

const btnGenerate = document.getElementById("btn-generate");
const btnSolve = document.getElementById("btn-solve");
const btnStop = document.getElementById("btn-stop");
const btnReset = document.getElementById("btn-reset");
const btnValidate = document.getElementById("btn-validate");

let cells = [];
let currentBoard = "0".repeat(81);
let baselineBoard = "0".repeat(81);
let collapseHistory = new Map();
let playbackTimer = null;
let stopRequested = false;

function buildGrid() {
  boardEl.innerHTML = "";
  cells = [];
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      const cell = document.createElement("div");
      cell.classList.add("cell", `row-${r}`, `col-${c}`);
      cell.dataset.r = r;
      cell.dataset.c = c;
      boardEl.appendChild(cell);
      cells.push(cell);
    }
  }
}

function cellAt(r, c) {
  return cells[r * SIZE + c];
}

function setStatus(text) {
  statusEl.textContent = text;
}

function setControlsBusy(busy) {
  btnGenerate.disabled = busy;
  btnSolve.disabled = busy;
  btnReset.disabled = busy;
  btnValidate.disabled = busy;
  givensEl.disabled = busy;
  seedEl.disabled = busy;
  btnStop.disabled = !busy;
}

function renderBoard(boardStr, { isBaseline = false } = {}) {
  if (boardStr.length !== 81) {
    console.error("invalid board string length", boardStr.length);
    return;
  }
  currentBoard = boardStr;
  if (isBaseline) {
    baselineBoard = boardStr;
    collapseHistory = new Map();
  }
  for (let i = 0; i < 81; i++) {
    const ch = boardStr[i];
    const cell = cells[i];
    cell.classList.remove(
      "given",
      "empty",
      "observed",
      "flash-collapse",
      "flash-backtrack",
    );
    if (ch === "0" || ch === ".") {
      cell.textContent = "";
      cell.classList.add("empty");
    } else {
      cell.textContent = ch;
      if (isBaseline) cell.classList.add("given");
      else if (baselineBoard[i] !== "0" && baselineBoard[i] !== ".") {
        cell.classList.add("given");
      }
    }
  }
  boardEl.classList.remove("flash-solved");
  boardInput.value = boardStr;
}

function setCellValue(r, c, value, klass) {
  const cell = cellAt(r, c);
  cell.textContent = value === 0 ? "" : value;
  cell.classList.remove("empty");
  if (klass) {
    cell.classList.add(klass);
    setTimeout(() => cell.classList.remove(klass), FLASH_MS);
  }
}

function clearObserved() {
  for (const cell of cells) cell.classList.remove("observed");
}

function clearCell(r, c) {
  const cell = cellAt(r, c);
  cell.textContent = "";
  cell.classList.add("empty");
  cell.classList.remove("observed");
}

async function api(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : null,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

async function doGenerate() {
  setControlsBusy(true);
  setStatus("Generating…");
  try {
    const givens = parseInt(givensEl.value, 10);
    const seed = seedEl.value === "" ? null : parseInt(seedEl.value, 10);
    const data = await api("/api/generate", { givens, seed });
    renderBoard(data.board, { isBaseline: true });
    setStatus(`Generated puzzle with ${data.givens} givens (seed=${data.seed ?? "random"}).`);
    validateOut.textContent = "";
  } catch (e) {
    setStatus(`Error: ${e.message}`);
  } finally {
    setControlsBusy(false);
  }
}

async function doValidate() {
  try {
    const body = { board: boardInput.value };
    const data = await api("/api/validate", body);
    validateOut.textContent = `Givens: ${data.givens}/81 · Consistent: ${data.consistent} · Solved: ${data.solved}`;
  } catch (e) {
    validateOut.textContent = `Error: ${e.message}`;
  }
}

function delay(ms) {
  return new Promise((resolve) => {
    playbackTimer = setTimeout(resolve, ms);
  });
}

async function playEvents(events) {
  stopRequested = false;
  let collapsedCount = 0;
  const total = events.filter((e) => e.type === "Collapsed").length;
  const step = () => parseInt(delayEl.value, 10);

  for (const event of events) {
    if (stopRequested) {
      setStatus(`Stopped at ${collapsedCount}/${total} collapses.`);
      return;
    }
    switch (event.type) {
      case "Observed": {
        clearObserved();
        const [r, c] = event.var;
        cellAt(r, c).classList.add("observed");
        await delay(step());
        break;
      }
      case "Collapsed": {
        const [r, c] = event.var;
        setCellValue(r, c, event.state, "flash-collapse");
        collapseHistory.set(event.var.join(","), event.state);
        collapsedCount += 1;
        setStatus(`Solving… ${collapsedCount}/${total} collapses.`);
        await delay(step());
        break;
      }
      case "Backtracked": {
        // Flash the original var red, then clear all undid_vars.
        const [r, c] = event.var;
        cellAt(r, c).classList.add("flash-backtrack");
        await delay(step());
        cellAt(r, c).classList.remove("flash-backtrack");
        for (const [ur, uc] of event.undid_vars) {
          const key = `${ur},${uc}`;
          if (collapseHistory.has(key)) {
            collapseHistory.delete(key);
            // Only clear if it wasn't a given.
            const baseChar = baselineBoard[ur * SIZE + uc];
            if (baseChar === "0" || baseChar === ".") {
              clearCell(ur, uc);
              collapsedCount = Math.max(0, collapsedCount - 1);
            }
          }
        }
        setStatus(`Backtracked from (${r},${c})=${event.state}. ${collapsedCount}/${total} collapses.`);
        break;
      }
      case "Solved": {
        clearObserved();
        boardEl.classList.add("flash-solved");
        setStatus("Solved! ✓");
        return;
      }
      case "Contradiction": {
        boardEl.classList.add("flash-backtrack");
        setStatus("No solution: the puzzle is contradictory.");
        return;
      }
    }
  }
}

async function doSolve() {
  setControlsBusy(true);
  validateOut.textContent = "";
  setStatus("Solving…");
  try {
    const seed = seedEl.value === "" ? null : parseInt(seedEl.value, 10);
    const board = boardInput.value || currentBoard;
    renderBoard(board, { isBaseline: true });
    const data = await api("/api/solve", { board, seed });
    if (data.solution === null) {
      setStatus("No solution exists for this puzzle.");
      return;
    }
    await playEvents(data.events);
  } catch (e) {
    setStatus(`Error: ${e.message}`);
  } finally {
    setControlsBusy(false);
  }
}

function doStop() {
  stopRequested = true;
  if (playbackTimer) {
    clearTimeout(playbackTimer);
    playbackTimer = null;
  }
  setControlsBusy(false);
}

function doReset() {
  renderBoard(baselineBoard, { isBaseline: true });
  setStatus("Reset to original puzzle.");
}

delayEl.addEventListener("input", () => {
  delayLabel.textContent = delayEl.value;
});

btnGenerate.addEventListener("click", doGenerate);
btnSolve.addEventListener("click", doSolve);
btnStop.addEventListener("click", doStop);
btnReset.addEventListener("click", doReset);
btnValidate.addEventListener("click", doValidate);

boardInput.addEventListener("input", () => {
  // Light passthrough — only re-render if the input looks valid (81 cell chars).
  const raw = boardInput.value.replace(/[\s|+\-]/g, "");
  if (raw.length === 81 && /^[0-9.]+$/.test(raw)) {
    renderBoard(raw, { isBaseline: true });
  }
});

buildGrid();
renderBoard("0".repeat(81), { isBaseline: true });
setStatus("Ready. Click Generate to start.");
