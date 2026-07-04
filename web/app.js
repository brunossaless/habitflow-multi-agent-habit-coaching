/* app.js — HabitFlow Team UI */

const state = {
  cards: {}, order: [], events: [], idx: 0, timer: null,
  running: false, counts: { a2a: 0, mcp: 0, exec: 0 },
};

const el = (s) => document.querySelector(s);
const now = () => new Date().toLocaleTimeString("pt-BR", { hour12: false });

function setStatus(text, cls = "") {
  const pill = el("#statusPill");
  if (!pill) return;
  pill.textContent = text;
  pill.className = "pill " + cls;
}

function setProgress(pct) {
  const wrap = el("#progressWrap");
  const bar = el("#progressBar");
  const label = el("#progressLabel");
  if (!wrap) return;
  wrap.classList.toggle("hidden", pct <= 0 && !state.running);
  if (bar) bar.style.setProperty("--pct", pct + "%");
  if (label) label.textContent = Math.round(pct) + "%";
}

function renderAgents() {
  const box = el("#agents");
  box.innerHTML = "";
  for (const id of Object.keys(AGENTS)) {
    const a = AGENTS[id];
    const node = document.createElement("div");
    node.className = "agent";
    node.id = `agent-${id}`;
    node.style.setProperty("--dot", a.color);
    node.innerHTML = `
      <div class="avatar">${a.icon}</div>
      <div class="meta">
        <div class="name">${a.name}</div>
        <div class="role">${a.role}</div>
      </div>
      <span class="badge" id="badge-${id}">idle</span>`;
    box.appendChild(node);
  }
}

function renderBoard() {
  const board = el("#board");
  board.innerHTML = "";
  for (const col of COLUMNS) {
    const c = document.createElement("div");
    c.className = "col";
    c.dataset.col = col.id;
    c.innerHTML = `
      <div class="col-head">
        <span style="color:${col.color}">${col.name}</span>
        <span class="col-count" id="wip-${col.id}">0</span>
      </div>
      <div class="col-cards" id="cards-${col.id}"></div>`;
    board.appendChild(c);
  }
}

function setAgentActive(id, status = "working") {
  for (const aid of Object.keys(AGENTS)) {
    const node = el(`#agent-${aid}`);
    const badge = el(`#badge-${aid}`);
    if (!node) continue;
    const active = aid === id;
    node.classList.toggle("active", active);
    if (badge) badge.textContent = active ? status : "idle";
  }
}

function cardHTML(card) {
  const tag = card.labels?.[0] || "general";
  const tagColor = LABEL_COLOR[tag] || "var(--muted)";
  const execName = card.executedBy ? (AGENTS[card.executedBy]?.name || card.executedBy) : null;
  return `
    <div class="card ${card.result ? "has-result" : ""}" id="card-${card.id}" data-card="${card.id}" style="--tag:${tagColor}">
      <div class="cid">${card.id}</div>
      <div class="ctitle">${card.title}</div>
      <div class="card-footer">
        <span class="tagchip" style="--tag:${tagColor}">${tag}</span>
        ${execName ? `<span class="exec-badge">✓ ${execName}</span>` : ""}
      </div>
      ${card.result ? '<div class="result-hint">🔎 clique para ver resultado</div>' : ""}
    </div>`;
}

function refreshBoard(boardData) {
  if (boardData?.columns) {
    state.cards = {};
    state.order = [];
    for (const col of boardData.columns) {
      for (const card of col.cards || []) {
        state.cards[card.id] = { ...card, column: col.id };
        if (!state.order.includes(card.id)) state.order.push(card.id);
      }
    }
  }
  let doneCount = 0;
  for (const col of COLUMNS) {
    const wrap = el(`#cards-${col.id}`);
    const list = state.order.map((id) => state.cards[id]).filter((c) => c && c.column === col.id);
    if (wrap) wrap.innerHTML = list.map(cardHTML).join("");
    const wip = el(`#wip-${col.id}`);
    if (wip) wip.textContent = String(list.length);
    if (col.id === "done") doneCount = list.length;
  }
  el("#statDone").textContent = doneCount;
  document.querySelectorAll(".card.has-result").forEach((c) => {
    c.onclick = () => showResult(c.dataset.card);
  });
}

function showResult(cardId) {
  const card = state.cards[cardId];
  if (!card?.result) return;
  const r = card.result;
  const agent = AGENTS[card.executedBy];
  el("#modalAgent").textContent = agent ? `${agent.icon} ${agent.name}` : card.executedBy;
  el("#modalTitle").textContent = `${cardId} — ${card.title}`;

  let html = "";
  if (r.notes) html += `<div class="modal-field"><label>Notas</label><div class="value">${r.notes}</div></div>`;
  if (r.metrics) html += `<div class="modal-field"><label>Métricas extraídas</label><div class="value">${JSON.stringify(r.metrics, null, 2)}</div></div>`;
  if (r.insights?.length) {
    html += `<div class="modal-field"><label>Insights</label><div class="value">${r.insights.map(i => `• ${i.pattern} (${Math.round(i.confidence*100)}%)`).join("<br>")}</div></div>`;
  }
  if (r.suggestions?.length) {
    html += `<div class="modal-field"><label>Sugestões</label><div class="value">${r.suggestions.map(s => `• ${s.action}`).join("<br>")}</div></div>`;
  }
  if (r.message) html += `<div class="modal-field"><label>Mensagem</label><div class="value">${r.message}</div></div>`;
  if (r.approved !== undefined) {
    const icon = r.approved ? "✅ Aprovado" : "❌ Bloqueado";
    html += `<div class="modal-field"><label>Guardian</label><div class="value">${icon} — risk: ${r.risk_score ?? "?"}</div></div>`;
  }
  if (r.artifacts?.length) {
    html += `<div class="modal-field"><label>Artefatos</label><div class="modal-artifacts">${r.artifacts.map(a => `<span class="artifact">${a}</span>`).join("")}</div></div>`;
  }
  if (!html) html = `<pre style="font-size:12px;white-space:pre-wrap">${JSON.stringify(r, null, 2)}</pre>`;
  el("#modalBody").innerHTML = html;
  el("#modal").classList.remove("hidden");
}

function appendLog(channel, ev) {
  const logMap = { a2a: "#logA2A", mcp: "#logMCP", exec: "#logExec" };
  const countMap = { a2a: "#countA2A", mcp: "#countMCP", exec: "#countExec" };
  const logEl = el(logMap[channel]);
  if (!logEl) return;

  state.counts[channel] = (state.counts[channel] || 0) + 1;
  const countEl = el(countMap[channel]);
  if (countEl) countEl.textContent = state.counts[channel];

  const from = ev.from_ || ev.from || "system";
  const kind = ev.kind || "";
  const agentColor = AGENTS[from]?.color || "var(--muted)";
  const li = document.createElement("li");
  li.innerHTML = `
    <span class="time">${now()}</span>
    <span class="badge-channel badge-${channel}">${channel}</span>
    <span class="from" style="color:${agentColor}">${from}</span>
    <span class="kind">${kind}</span>
    ${ev.text || ""}`;
  logEl.appendChild(li);
  logEl.scrollTop = logEl.scrollHeight;
}

function findCardResult(agentId) {
  return Object.values(state.cards)
    .filter((c) => c.column === "done" && c.executedBy === agentId && c.result)
    .map((c) => c.result)[0];
}

function formatMetrics(metrics) {
  if (!metrics || !Object.keys(metrics).length) return "";
  const pills = [];
  if (metrics.distance_km != null) pills.push(`${metrics.distance_km} km`);
  if (metrics.duration_min != null) pills.push(`${metrics.duration_min} min`);
  if (metrics.water_liters != null) pills.push(`${metrics.water_liters} L água`);
  return pills.map((p) => `<span class="metric-pill">${p}</span>`).join("");
}

function renderActionHero(primary) {
  if (!primary) return "";
  const dir = primary.direction || "maintain";
  const dirLabel = { increase: "Aumentar", decrease: "Reduzir", maintain: "Manter" }[dir] || "Agir";
  const catLabel = {
    exercise: "Exercício", water: "Água", sleep: "Sono",
    recovery: "Recuperação", data: "Registro", general: "Geral",
  }[primary.category] || primary.category || "Geral";
  return `
    <div class="action-hero action-hero--${dir}">
      <div class="action-hero__icon">${primary.icon || "🎯"}</div>
      <div class="action-hero__body">
        <div class="action-hero__eyebrow">Melhor ação para você agora</div>
        <div class="action-hero__title">${primary.title}</div>
        <div class="action-hero__action">${primary.action}</div>
        <div class="action-hero__reason">${primary.reasoning}</div>
      </div>
      <div class="action-hero__meta">
        <span class="action-hero__badge action-hero__badge--${dir}">${dirLabel}</span>
        <span class="action-hero__badge action-hero__badge--cat">${catLabel}</span>
        ${primary.confidence ? `<span class="action-hero__conf">${Math.round(primary.confidence * 100)}% confiança</span>` : ""}
      </div>
    </div>`;
}

function renderFinalResult(data) {
  const panel = el("#resultPanel");
  const out = el("#finalOutput");
  const trail = el("#agentTrail");
  const badge = el("#resultBadge");
  if (!panel || !out) return;

  const doneCards = Object.values(state.cards).filter((c) => c.column === "done");
  const metrics = findCardResult("analyzer-agent")?.metrics || {};
  const coach = data.coach_result || findCardResult("coach-agent");
  const primary = coach?.primary_action || data.coach_result?.primary_action;
  const guardian = data.guardian_result || findCardResult("guardian-agent");
  const collector = findCardResult("collector-agent");

  const contributors = doneCards
    .filter((c) => c.executedBy && AGENTS[c.executedBy])
    .map((c) => c.executedBy)
    .filter((id, i, arr) => arr.indexOf(id) === i);

  if (badge) badge.textContent = `✓ ${doneCards.length} tarefa${doneCards.length !== 1 ? "s" : ""} concluída${doneCards.length !== 1 ? "s" : ""}`;

  if (trail) {
    trail.innerHTML = contributors.map((id, i) => {
      const a = AGENTS[id];
      const arrow = i < contributors.length - 1 ? '<span class="trail-arrow">→</span>' : "";
      return `<span class="trail-step" style="--dot:${a.color}"><span class="icon">${a.icon}</span>${a.name}</span>${arrow}`;
    }).join("");
  }

  let html = renderActionHero(primary);

  html += '<div class="result-grid">';

  if (Object.keys(metrics).length) {
    html += `<div class="result-card"><h3>🔍 Analyzer</h3><div>${formatMetrics(metrics)}</div></div>`;
  }

  if (collector?.entries_saved) {
    html += `<div class="result-card"><h3>📝 Collector</h3><ul><li>Check-in salvo com ${collector.entries_saved} entrada(s)</li></ul></div>`;
  }

  if (coach?.insights?.length) {
    html += `<div class="result-card"><h3>🧠 Coach — Insights</h3><ul>${coach.insights.map((i) =>
      `<li>• ${i.pattern} <span class="priority-low">(${Math.round((i.confidence || 0) * 100)}%)</span></li>`
    ).join("")}</ul></div>`;
  }

  if (coach?.suggestions?.length) {
    const extra = coach.suggestions.filter((s) => s.action !== primary?.action);
    if (extra.length) {
      html += `<div class="result-card"><h3>💡 Outras sugestões</h3><ul>${extra.map((s) =>
        `<li class="priority-${s.priority || "medium"}">• ${s.action}</li>`
      ).join("")}</ul></div>`;
    }
  }

  if (guardian) {
    const ok = guardian.approved !== false;
    const cls = ok ? "guardian-ok" : "guardian-block";
    const label = ok ? "✅ Aprovado pelo Guardian" : "❌ Bloqueado pelo Guardian";
    html += `<div class="result-card"><h3>🛡️ Guardian</h3><ul><li class="${cls}">${label}</li>${guardian.warnings?.length ? guardian.warnings.map((w) => `<li>• ${w}</li>`).join("") : ""}</ul></div>`;
  }

  html += "</div>";

  if (data.final_message && !primary) {
    html += `<div class="result-card"><h3>📲 Mensagem final</h3><div class="result-message">${data.final_message}</div></div>`;
  } else if (!primary && !Object.keys(metrics).length && !coach?.insights?.length) {
    html += `<div class="result-message">Pipeline executado com sucesso.</div>`;
  }

  out.innerHTML = html;
  panel.classList.remove("hidden");
  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function playEvent(ev) {
  const agent = ev.from_ || ev.from;
  if (agent && AGENTS[agent]) setAgentActive(agent);
  if (ev.channel === "mcp") {
    el("#mcpPulse")?.classList.add("active");
    el("#mcpNode")?.classList.add("active");
  }
  appendLog(ev.channel, ev);
  if (ev.result && ev.cardId) {
    const card = state.cards[ev.cardId];
    if (card) {
      card.result = ev.result;
      card.executedBy = ev.result.executedBy || agent;
    }
  }
}

function getSelectedMode() {
  return document.querySelector('input[name="mode"]:checked')?.value || "auto";
}

async function runPipeline(input) {
  if (state.running) return;
  state.running = true;
  clearLogs();
  renderBoard();
  el("#resultPanel")?.classList.add("hidden");
  el("#btnRun").disabled = true;
  setStatus("● executando…", "pill--running");
  setProgress(1);
  el("#progressWrap")?.classList.remove("hidden");

  try {
    const mode = getSelectedMode();
    const res = await fetch("/api/sprint/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input, user_id: "demo-user", mode }),
    });
    const data = await res.json();
    state.events = data.events || [];
    refreshBoard(data.board || {});
    el("#statEvents").textContent = state.events.length;
    state.idx = 0;
    await playNextEvent(data);
  } catch (err) {
    appendLog("a2a", { from_: "system", kind: "error", text: String(err) });
    setStatus("● erro", "");
  }
}

function playNextEvent(sprintData) {
  return new Promise((resolve) => {
    if (state.idx >= state.events.length) {
      if (sprintData?.board) refreshBoard(sprintData.board);
      renderFinalResult(sprintData || {});
      setAgentActive(null);
      setProgress(100);
      setStatus("● concluído", "pill--done");
      state.running = false;
      el("#btnRun").disabled = false;
      el("#mcpPulse")?.classList.remove("active");
      el("#mcpNode")?.classList.remove("active");
      resolve();
      return;
    }

    const pct = (state.idx / state.events.length) * 100;
    setProgress(pct);

    const ev = state.events[state.idx++];
    const cardId = ev.cardId;

    if (cardId && ev.kind === "card.move" && ev.text) {
      const m = ev.text.match(/→ (\w+)/);
      if (m && state.cards[cardId]) {
        state.cards[cardId].column = m[1];
        const cardEl = el(`#card-${cardId}`);
        if (cardEl) {
          cardEl.classList.add("moving");
          setTimeout(() => cardEl?.classList.remove("moving"), 400);
        }
      }
      refreshBoard({
        columns: COLUMNS.map((c) => ({
          id: c.id,
          cards: state.order.map((id) => state.cards[id]).filter((x) => x && x.column === c.id),
        })),
      });
    }

    playEvent(ev);
    state.timer = setTimeout(() => playNextEvent(sprintData).then(resolve), 350);
  });
}

function clearLogs() {
  ["#logA2A", "#logMCP", "#logExec"].forEach((s) => { const l = el(s); if (l) l.innerHTML = ""; });
  state.counts = { a2a: 0, mcp: 0, exec: 0 };
  ["#countA2A", "#countMCP", "#countExec"].forEach((s) => { const c = el(s); if (c) c.textContent = "0"; });
}

function setupTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".log").forEach((l) => l.classList.remove("active"));
      tab.classList.add("active");
      const map = { a2a: "A2A", mcp: "MCP", exec: "Exec" };
      el(`#log${map[tab.dataset.tab]}`)?.classList.add("active");
    });
  });
}

function setupQuickChips() {
  const box = el("#quickChips");
  QUICK_INPUTS.forEach(({ text, mode }) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.textContent = text.slice(0, 32) + (text.length > 32 ? "…" : "");
    chip.addEventListener("click", () => {
      el("#fInput").value = text;
      const radio = document.querySelector(`input[name="mode"][value="${mode}"]`);
      if (radio) radio.checked = true;
    });
    box.appendChild(chip);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  renderAgents();
  renderBoard();
  setupTabs();
  setupQuickChips();

  el("#inputForm")?.addEventListener("submit", (e) => {
    e.preventDefault();
    runPipeline(el("#fInput").value.trim());
  });
  el("#btnRun")?.addEventListener("click", () => runPipeline(el("#fInput").value.trim()));
  el("#btnReset")?.addEventListener("click", () => {
    clearTimeout(state.timer);
    state.events = []; state.idx = 0; state.running = false;
    clearLogs(); renderBoard();
    el("#resultPanel")?.classList.add("hidden");
    el("#finalOutput").innerHTML = "";
    el("#agentTrail").innerHTML = "";
    el("#progressWrap")?.classList.add("hidden");
    setAgentActive(null); setStatus("● pronto", "pill--live");
    el("#statDone").textContent = "0";
    el("#statEvents").textContent = "0";
    el("#btnRun").disabled = false;
  });
  el("#btnStep")?.addEventListener("click", () => {
    if (state.idx < state.events.length) {
      playEvent(state.events[state.idx++]);
      setProgress((state.idx / state.events.length) * 100);
    }
  });
  el("#modalClose")?.addEventListener("click", () => el("#modal").classList.add("hidden"));
  el("#modal")?.addEventListener("click", (e) => {
    if (e.target === el("#modal")) el("#modal").classList.add("hidden");
  });
});
