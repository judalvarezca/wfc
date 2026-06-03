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

// State model
//   baselineBoard: 81-char puzzle the user started from (givens marked here)
//   currentBoard:  81-char live state, mutated as animation plays
//   solveCache:    last /api/solve result and its request fingerprint
//   playbackIndex: next event index to apply (0 = nothing played)
//   isPlaying:     guard against re-entrant playback
//   stopRequested: cooperative cancel flag for the running playback loop
let baselineBoard = "0".repeat(81);
let currentBoard = "0".repeat(81);
let solveCache = null; // {fingerprint, events, solution}
let playbackIndex = 0;
let isPlaying = false;
let stopRequested = false;
let playbackTimer = null;
let pendingResolve = null; // resolves the current `delay` promise on stop
let activeGen = 0; // monotonic; older playFrom invocations bail when superseded

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

function setBoardChar(i, ch) {
  // currentBoard is a string; we keep it immutable-ish by splicing.
  currentBoard = currentBoard.substring(0, i) + ch + currentBoard.substring(i + 1);
}

function isGiven(i) {
  const ch = baselineBoard[i];
  return ch >= "1" && ch <= "9";
}

function renderFreshPuzzle(boardStr) {
  // Used when loading a new baseline (generate, paste, reset). Wipes
  // solver state and the playback cache.
  if (boardStr.length !== 81) {
    console.error("invalid board string length", boardStr.length);
    return;
  }
  baselineBoard = boardStr;
  currentBoard = boardStr;
  invalidateCache();
  for (let i = 0; i < 81; i++) {
    const cell = cells[i];
    cell.classList.remove(
      "given",
      "empty",
      "observed",
      "flash-collapse",
      "flash-backtrack",
    );
    const ch = boardStr[i];
    if (ch === "0" || ch === ".") {
      cell.textContent = "";
      cell.classList.add("empty");
    } else {
      cell.textContent = ch;
      cell.classList.add("given");
    }
  }
  boardEl.classList.remove("flash-solved");
  boardInput.value = boardStr;
}

function invalidateCache() {
  solveCache = null;
  playbackIndex = 0;
}

function applyCollapse(r, c, value, withFlash) {
  const i = r * SIZE + c;
  setBoardChar(i, String(value));
  const cell = cellAt(r, c);
  cell.textContent = value === 0 ? "" : value;
  cell.classList.remove("empty");
  if (withFlash) {
    cell.classList.add("flash-collapse");
    setTimeout(() => cell.classList.remove("flash-collapse"), FLASH_MS);
  }
}

function applyClear(r, c) {
  const i = r * SIZE + c;
  if (isGiven(i)) return; // never clear givens
  setBoardChar(i, "0");
  const cell = cellAt(r, c);
  cell.textContent = "";
  cell.classList.add("empty");
  cell.classList.remove("observed");
}

function clearObserved() {
  for (const cell of cells) cell.classList.remove("observed");
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

function delay(ms) {
  return new Promise((resolve) => {
    pendingResolve = resolve;
    playbackTimer = setTimeout(() => {
      pendingResolve = null;
      playbackTimer = null;
      resolve();
    }, ms);
  });
}

function fingerprintFor(board, seed) {
  return `${board}|${seed === null ? "" : seed}`;
}

function currentCounts() {
  let givens = 0;
  let collapsed = 0;
  let missing = 0;
  for (let i = 0; i < 81; i++) {
    if (isGiven(i)) {
      givens += 1;
    } else if (currentBoard[i] >= "1" && currentBoard[i] <= "9") {
      collapsed += 1;
    } else {
      missing += 1;
    }
  }
  return { givens, collapsed, missing };
}

function isConsistent() {
  const groups = [];
  for (let r = 0; r < SIZE; r++) {
    groups.push(Array.from({ length: SIZE }, (_, c) => r * SIZE + c));
  }
  for (let c = 0; c < SIZE; c++) {
    groups.push(Array.from({ length: SIZE }, (_, r) => r * SIZE + c));
  }
  for (let b = 0; b < SIZE; b++) {
    const br = Math.floor(b / 3) * 3;
    const bc = (b % 3) * 3;
    const idx = [];
    for (let dr = 0; dr < 3; dr++) {
      for (let dc = 0; dc < 3; dc++) {
        idx.push((br + dr) * SIZE + (bc + dc));
      }
    }
    groups.push(idx);
  }
  for (const unit of groups) {
    const seen = new Set();
    for (const i of unit) {
      const ch = currentBoard[i];
      if (ch === "0" || ch === ".") continue;
      if (seen.has(ch)) return false;
      seen.add(ch);
    }
  }
  return true;
}

function isSolved() {
  if (currentBoard.includes("0") || currentBoard.includes(".")) return false;
  return isConsistent();
}

function applyEvent(ev) {
  switch (ev.type) {
    case "Observed": {
      clearObserved();
      const [r, c] = ev.var;
      cellAt(r, c).classList.add("observed");
      break;
    }
    case "Collapsed": {
      const [r, c] = ev.var;
      applyCollapse(r, c, ev.state, true);
      break;
    }
    case "Backtracked": {
      const [r, c] = ev.var;
      const cell = cellAt(r, c);
      cell.classList.add("flash-backtrack");
      // Schedule the un-flash but don't await it — we want the red blink to
      // overlap with the next event's delay, not block playback.
      setTimeout(() => cell.classList.remove("flash-backtrack"), FLASH_MS);
      for (const [ur, uc] of ev.undid_vars) {
        applyClear(ur, uc);
      }
      break;
    }
    case "Solved": {
      clearObserved();
      boardEl.classList.add("flash-solved");
      break;
    }
    case "Contradiction": {
      boardEl.classList.add("flash-backtrack");
      break;
    }
  }
}

function totalCollapsesIn(events) {
  return events.filter((e) => e.type === "Collapsed").length;
}

async function playFrom(startIdx) {
  if (!solveCache) return;
  const myGen = ++activeGen;
  isPlaying = true;
  stopRequested = false;
  setControlsBusy(true);
  const events = solveCache.events;
  const total = totalCollapsesIn(events);
  try {
    for (let i = startIdx; i < events.length; i++) {
      if (myGen !== activeGen) return; // superseded by a newer playFrom
      if (stopRequested) {
        playbackIndex = i;
        // Don't set status here — leave it to whoever called doStop, so
        // doReset's "Reset to original puzzle" doesn't get overwritten by
        // the microtask-deferred "Paused at..." message.
        return;
      }
      const ev = events[i];
      applyEvent(ev);
      if (ev.type === "Solved") {
        playbackIndex = i + 1;
        setStatus("Solved! ✓");
        return;
      }
      if (ev.type === "Contradiction") {
        playbackIndex = i + 1;
        setStatus("No solution: the puzzle is contradictory.");
        return;
      }
      const { collapsed } = currentCounts();
      if (ev.type === "Collapsed") {
        setStatus(`Solving… ${collapsed}/${total} collapses.`);
      } else if (ev.type === "Observed") {
        const [r, c] = ev.var;
        setStatus(`Observing (${r},${c}). ${collapsed}/${total}.`);
      } else if (ev.type === "Backtracked") {
        const [r, c] = ev.var;
        setStatus(`Backtracked (${r},${c})=${ev.state}. ${collapsed}/${total}.`);
      }
      await delay(parseInt(delayEl.value, 10));
      playbackIndex = i + 1;
    }
  } finally {
    // Only the current generation owns the global flags. If we've been
    // superseded, the new playFrom is in charge of them.
    if (myGen === activeGen) {
      isPlaying = false;
      setControlsBusy(false);
    }
  }
}

async function doGenerate() {
  if (isPlaying) doStop();
  setControlsBusy(true);
  setStatus("Generating…");
  try {
    const givens = parseInt(givensEl.value, 10);
    const seed = seedEl.value === "" ? null : parseInt(seedEl.value, 10);
    const data = await api("/api/generate", { givens, seed });
    renderFreshPuzzle(data.board);
    setStatus(`Generated puzzle with ${data.givens} givens (seed=${data.seed ?? "random"}).`);
    validateOut.textContent = "";
  } catch (e) {
    setStatus(`Error: ${e.message}`);
  } finally {
    setControlsBusy(false);
  }
}

function doValidate() {
  // Local validation against the live state, so the breakdown reflects what
  // the user actually sees (givens vs solver-placed vs missing).
  const { givens, collapsed, missing } = currentCounts();
  const consistent = isConsistent();
  const solved = isSolved();
  validateOut.textContent =
    `Givens (original):    ${String(givens).padStart(2)}\n` +
    `Collapsed by solver:  ${String(collapsed).padStart(2)}\n` +
    `Missing:              ${String(missing).padStart(2)}\n` +
    `Consistent:          ${consistent ? "Yes" : "No"}\n` +
    `Solved:              ${solved ? "Yes" : "No"}`;
}

async function doSolve() {
  if (isPlaying) return;
  const seed = seedEl.value === "" ? null : parseInt(seedEl.value, 10);
  const inputBoard = boardInput.value.replace(/[\s|+\-]/g, "");
  // If the textarea got edited to something different from the baseline,
  // adopt it as the new baseline before solving.
  if (inputBoard.length === 81 && inputBoard !== baselineBoard) {
    renderFreshPuzzle(inputBoard);
  }
  const fingerprint = fingerprintFor(baselineBoard, seed);

  // Resume if we have cached events for this exact request and stopped mid-way.
  if (
    solveCache &&
    solveCache.fingerprint === fingerprint &&
    playbackIndex > 0 &&
    playbackIndex < solveCache.events.length
  ) {
    setStatus("Resuming…");
    await playFrom(playbackIndex);
    return;
  }

  // Fresh solve: reset grid to baseline (clears any prior animation state).
  renderFreshPuzzle(baselineBoard);
  setControlsBusy(true);
  setStatus("Solving…");
  try {
    const data = await api("/api/solve", { board: baselineBoard, seed });
    solveCache = {
      fingerprint,
      events: data.events,
      solution: data.solution,
    };
    playbackIndex = 0;
    // Contradiction (data.solution === null) is emitted as a single event;
    // playFrom will pick that up and set the status accordingly.
    await playFrom(0);
  } catch (e) {
    setStatus(`Error: ${e.message}`);
    setControlsBusy(false);
  }
}

function doStop() {
  stopRequested = true;
  if (playbackTimer) {
    clearTimeout(playbackTimer);
    playbackTimer = null;
  }
  // Resolve the pending delay so playFrom's `await` returns and the loop
  // sees stopRequested. clearTimeout alone does NOT resolve the promise.
  if (pendingResolve) {
    const r = pendingResolve;
    pendingResolve = null;
    r();
  }
  // Flip flags eagerly so a fast click on Solve isn't swallowed by the
  // guard in doSolve. The superseded playFrom will bail via activeGen.
  isPlaying = false;
  setControlsBusy(false);
  if (solveCache) {
    const total = totalCollapsesIn(solveCache.events);
    const { collapsed } = currentCounts();
    setStatus(`Paused at ${collapsed}/${total} collapses. Click Solve to resume.`);
  }
}

function doReset() {
  if (isPlaying) doStop();
  renderFreshPuzzle(baselineBoard);
  setStatus("Reset to original puzzle.");
  validateOut.textContent = "";
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
  const raw = boardInput.value.replace(/[\s|+\-]/g, "");
  if (raw.length === 81 && /^[0-9.]+$/.test(raw) && raw !== baselineBoard) {
    renderFreshPuzzle(raw);
  }
});

buildGrid();
renderFreshPuzzle("0".repeat(81));
setStatus("Ready. Click Generate to start.");
