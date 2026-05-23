const input = document.querySelector("#sessionSearch");
const projectFilter = document.querySelector("#projectFilter");
const hoursFilter = document.querySelector("#hoursFilter");
const clearFilters = document.querySelector("#clearFilters");
const table = document.querySelector("#sessionTable");
const title = document.querySelector("#detailTitle");
const body = document.querySelector("#detailBody");
const source = document.querySelector("#detailSource");
const age = document.querySelector("#detailAge");
const command = document.querySelector("#detailCommand");
const project = document.querySelector("#detailProject");
const tool = document.querySelector("#detailTool");
const git = document.querySelector("#detailGit");
const detailUser = document.querySelector("#detailUser");
const detailFiles = document.querySelector("#detailFiles");
const coldSessions = document.querySelector("#coldSessions");
const hotSessions = document.querySelector("#hotSessions");
const hotWindow = document.querySelector("#hotWindow");
const queryMs = document.querySelector("#queryMs");
const resultSummary = document.querySelector("#resultSummary");
const refreshIndex = document.querySelector("#refreshIndex");
const latestCard = document.querySelector("#latestCard");
const copyCommand = document.querySelector("#copyCommand");
const indexNote = document.querySelector("#indexNote");
const indexMeter = document.querySelector("#indexMeter");

let rows = Array.from(document.querySelectorAll(".session-row"));
let live = location.protocol !== "file:";
let searchTimer = null;
let mode = "all";
let selectedSession = "";

function text(value) {
  return String(value || "");
}

function relativeTime(seconds) {
  if (!seconds) return "";
  const delta = Math.max(0, Date.now() / 1000 - Number(seconds));
  if (delta < 60) return "now";
  if (delta < 3600) return `${Math.round(delta / 60)}m ago`;
  if (delta < 86400) return `${Math.round(delta / 3600)}h ago`;
  return `${Math.round(delta / 86400)}d ago`;
}

function setMode(nextMode) {
  mode = nextMode;
  document.querySelectorAll("[data-mode]").forEach((button) => {
    button.classList.toggle("selected", button.dataset.mode === mode);
    button.classList.toggle("active", button.dataset.mode === mode);
  });
  runSearch();
}

function renderRows(items, meta = {}) {
  table.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "No sessions matched the current filters.";
    table.appendChild(empty);
    rows = [];
    const total = Number(meta.total || 0);
    resultSummary.textContent = total
      ? `0 shown of ${total.toLocaleString()} matches. The visible rows were filtered out.`
      : "No matching sessions. Try All time, Cold, or a broader query.";
    return;
  }

  rows = items.map((item, index) => {
    const row = document.createElement("button");
    row.className = `session-row${index === 0 ? " selected" : ""}`;
    row.type = "button";
    row.dataset.session = item.id || "";
    row.dataset.source = item.source || "index";
    row.innerHTML = `
      <span class="status-dot"></span>
      <span class="session-main">
        <strong></strong>
        <small></small>
      </span>
      <span class="session-meta"></span>
    `;
    row.querySelector("strong").textContent = text(item.title || "Untitled session");
    row.querySelector("small").textContent = text(item.project || item.state || "indexed session");
    row.querySelector(".session-meta").textContent = `${item.source || "index"} · ${relativeTime(item.date)}`;
    row.addEventListener("click", () => selectRow(row));
    table.appendChild(row);
    return row;
  });

  const hotShown = items.filter((item) => item.source === "hot-live").length;
  const total = Number(meta.total || items.length);
  const hotTotal = Number(meta.hot_total || hotShown);
  const coldTotal = Number(meta.cold_total || total - hotTotal);
  if (meta.view === "recent" && !input.value.trim()) {
    const indexedTotal = Number(meta.index?.sessions || coldTotal);
    resultSummary.textContent = `Showing ${items.length.toLocaleString()} recent rows · ${indexedTotal.toLocaleString()} indexed total · ${hotTotal.toLocaleString()} hot now`;
  } else {
    resultSummary.textContent = `Showing ${items.length.toLocaleString()} of ${total.toLocaleString()} matches · ${hotTotal.toLocaleString()} hot · ${coldTotal.toLocaleString()} indexed`;
  }
  selectRow(rows[0]);
}

function selectRow(row) {
  rows.forEach((item) => item.classList.remove("selected"));
  row.classList.add("selected");
  selectedSession = row.dataset.session || "";
  if (live && selectedSession) {
    loadCard(selectedSession);
    return;
  }
  title.textContent = row.querySelector("strong")?.textContent || "Session";
  body.textContent = row.querySelector("small")?.textContent || "";
}

async function loadStatus() {
  if (!live) return;
  const res = await fetch("/api/status");
  const data = await res.json();
  coldSessions.textContent = Number(data.index.sessions || 0).toLocaleString();
  hotSessions.textContent = Number(data.hot_sessions || 0).toLocaleString();
  hotWindow.textContent = `${data.hot_window_minutes || 30}m`;
  indexMeter.style.width = `${Math.min(100, Math.max(12, (data.index.sessions || 0) / 80))}%`;
}

function renderFiles(files) {
  detailFiles.innerHTML = "";
  if (!files || !files.length) {
    const item = document.createElement("li");
    item.textContent = "No touched files in the card.";
    detailFiles.appendChild(item);
    return;
  }
  files.slice(0, 12).forEach((file) => {
    const item = document.createElement("li");
    item.textContent = file;
    item.title = file;
    detailFiles.appendChild(item);
  });
}

async function loadCard(sessionId = "") {
  const res = await fetch(`/api/card${sessionId ? `?session=${encodeURIComponent(sessionId)}` : ""}`);
  const card = await res.json();
  if (card.error) {
    body.textContent = card.error;
    return;
  }
  title.textContent = card.title || "Untitled session";
  body.textContent = card.where_stopped || card.last_assistant || "No summary yet.";
  source.textContent = card.source || "resume card";
  age.textContent = card.age || "";
  command.textContent = card.command || "";
  project.textContent = card.project || card.project_dir || "";
  tool.textContent = card.last_tool || "none";
  detailUser.textContent = card.last_user || "No user message captured.";
  const dirty = card.git?.dirty ? `Dirty, ${card.git.files?.length || card.git.count || 0} files` : "Clean";
  git.textContent = dirty;
  renderFiles(card.files || card.git?.files || []);
}

function searchUrl() {
  const params = new URLSearchParams();
  params.set("q", input.value.trim());
  params.set("limit", "20");
  params.set("mode", mode);
  if (hoursFilter.value !== "0") params.set("hours", hoursFilter.value);
  if (projectFilter.value.trim()) params.set("project", projectFilter.value.trim());
  return `/api/search?${params.toString()}`;
}

async function runSearch() {
  if (!live) {
    applyStaticSearch();
    return;
  }
  table.setAttribute("aria-busy", "true");
  const started = performance.now();
  try {
    const res = await fetch(searchUrl());
    const data = await res.json();
    coldSessions.textContent = Number(data.index.sessions || 0).toLocaleString();
    renderRows(data.items || [], data);
    queryMs.textContent = `${Math.max(1, Math.round(performance.now() - started))}ms`;
  } catch (error) {
    table.innerHTML = `<div class="empty-state">Search failed: ${text(error.message)}</div>`;
  } finally {
    table.removeAttribute("aria-busy");
  }
}

async function refreshColdIndex() {
  if (!live) return;
  refreshIndex.disabled = true;
  refreshIndex.textContent = "...";
  indexNote.textContent = "Refreshing a small cold-index batch...";
  try {
    const res = await fetch("/api/index/refresh");
    const data = await res.json();
    indexNote.textContent = `Checked ${data.checked || 0}; indexed ${data.indexed || 0}; ${data.done ? "cursor complete" : "cursor continuing"}.`;
    coldSessions.textContent = Number(data.index.sessions || 0).toLocaleString();
    runSearch();
  } finally {
    refreshIndex.disabled = false;
    refreshIndex.textContent = "↻";
  }
}

function applyStaticSearch() {
  const query = input.value.trim().toLowerCase();
  let firstVisible = null;
  rows.forEach((row) => {
    const haystack = row.dataset.query || row.textContent;
    const visible = !query || haystack.toLowerCase().includes(query);
    row.classList.toggle("hidden", !visible);
    if (visible && !firstVisible) firstVisible = row;
  });
  if (firstVisible) selectRow(firstVisible);
}

input.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(runSearch, 120);
});

projectFilter.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(runSearch, 160);
});

hoursFilter.addEventListener("change", runSearch);
clearFilters.addEventListener("click", () => {
  input.value = "";
  projectFilter.value = "";
  hoursFilter.value = "0";
  setMode("all");
});
refreshIndex.addEventListener("click", refreshColdIndex);
latestCard.addEventListener("click", () => loadCard());
copyCommand.addEventListener("click", async () => {
  const value = command.textContent.trim();
  if (!value) return;
  await navigator.clipboard.writeText(value);
  copyCommand.textContent = "✓";
  setTimeout(() => {
    copyCommand.textContent = "⧉";
  }, 900);
});

document.querySelectorAll("[data-mode]").forEach((button) => {
  button.addEventListener("click", () => setMode(button.dataset.mode));
});
document.querySelectorAll("[data-panel='card']").forEach((button) => {
  button.addEventListener("click", () => loadCard(selectedSession));
});

rows.forEach((row) => row.addEventListener("click", () => selectRow(row)));

window.addEventListener("keydown", (event) => {
  if (event.key === "/" && document.activeElement !== input) {
    event.preventDefault();
    input.focus();
  }
});

if (live) {
  loadStatus().catch(() => {});
  loadCard().catch(() => {});
  runSearch().catch(() => {});
}
