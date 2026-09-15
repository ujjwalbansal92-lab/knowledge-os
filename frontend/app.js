const STORAGE_KEY = "kos_backend_url";

function getBackendUrl() {
  return localStorage.getItem(STORAGE_KEY) || "";
}
function setBackendUrl(url) {
  localStorage.setItem(STORAGE_KEY, url.replace(/\/$/, ""));
}

const el = (id) => document.getElementById(id);

let activeTag = null;
let lastFailedUrl = null;

function showStatus(message, type = "info") {
  const s = el("status");
  s.textContent = message;
  s.className = `status ${type}`;
  s.classList.remove("hidden");
}
function hideStatus() {
  el("status").classList.add("hidden");
}

async function apiFetch(path, options = {}) {
  const base = getBackendUrl();
  if (!base) {
    throw new Error("NO_BACKEND_URL");
  }
  const res = await fetch(`${base}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail?.message || data.detail || "Request failed");
    err.status = res.status;
    err.payload = data.detail;
    throw err;
  }
  return data;
}

async function submitLink() {
  const url = el("yt-url").value.trim();
  if (!url) return;

  el("manual-fallback").classList.add("hidden");
  showStatus("Extracting transcript and generating card…", "info");

  try {
    await apiFetch("/api/cards", {
      method: "POST",
      body: JSON.stringify({ url }),
    });
    showStatus("Card created.", "success");
    el("yt-url").value = "";
    loadCards();
  } catch (e) {
    if (e.message === "NO_BACKEND_URL") {
      showStatus("Set your backend URL first (⚙️ top right).", "error");
      el("config-panel").classList.remove("hidden");
      return;
    }
    if (e.status === 409 && e.payload?.needs_manual) {
      lastFailedUrl = url;
      showStatus("Automatic extraction failed. Paste the transcript below to continue.", "error");
      el("manual-fallback").classList.remove("hidden");
      return;
    }
    showStatus(`Error: ${e.message}`, "error");
  }
}

async function submitManual() {
  const transcript = el("manual-transcript").value.trim();
  if (!transcript) return;

  showStatus("Generating card from pasted transcript…", "info");
  try {
    await apiFetch("/api/cards/manual", {
      method: "POST",
      body: JSON.stringify({ url: lastFailedUrl, transcript }),
    });
    showStatus("Card created from pasted transcript.", "success");
    el("manual-transcript").value = "";
    el("manual-fallback").classList.add("hidden");
    el("yt-url").value = "";
    lastFailedUrl = null;
    loadCards();
  } catch (e) {
    showStatus(`Error: ${e.message}`, "error");
  }
}

function renderTagChips(tags) {
  const container = el("tag-chips");
  container.innerHTML = "";
  tags.forEach(({ tag, count }) => {
    const chip = document.createElement("span");
    chip.className = "chip" + (activeTag === tag ? " active" : "");
    chip.textContent = `${tag} (${count})`;
    chip.onclick = () => {
      activeTag = activeTag === tag ? null : tag;
      el("clear-filter").classList.toggle("hidden", !activeTag);
      loadCards();
      loadTags();
    };
    container.appendChild(chip);
  });
}

function renderCards(cards) {
  const list = el("cards-list");
  list.innerHTML = "";
  if (!cards.length) {
    list.innerHTML = `<div class="empty-state">No cards yet. Paste a YouTube link above to create your first one.</div>`;
    return;
  }
  cards.forEach((card) => {
    const div = document.createElement("div");
    div.className = "card";
    const tagsHtml = card.tags.map((t) => `<span class="tag">${t}</span>`).join("");
    const sourceLink = card.source_url
      ? `<a class="source-link" href="${card.source_url}" target="_blank" rel="noopener">source ↗</a>`
      : "";
    div.innerHTML = `
      <h3>${escapeHtml(card.title)}</h3>
      <div class="tags">${tagsHtml}</div>
      <p>${escapeHtml(card.summary)}</p>
      <div class="meta">${card.extraction_source} · ${new Date(card.created_at * 1000).toLocaleDateString()} ${sourceLink}</div>
    `;
    list.appendChild(div);
  });
}

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

async function loadCards() {
  try {
    const path = activeTag ? `/api/cards?tag=${encodeURIComponent(activeTag)}` : "/api/cards";
    const cards = await apiFetch(path);
    renderCards(cards);
  } catch (e) {
    if (e.message !== "NO_BACKEND_URL") {
      el("cards-list").innerHTML = `<div class="empty-state">Couldn't load cards: ${e.message}</div>`;
    }
  }
}

async function loadTags() {
  try {
    const tags = await apiFetch("/api/tags");
    renderTagChips(tags);
  } catch (e) {
    // silent — tag bar just stays empty if backend isn't configured yet
  }
}

function initConfigPanel() {
  const saved = getBackendUrl();
  el("backend-url").value = saved;
  if (!saved) el("config-panel").classList.remove("hidden");

  el("config-toggle").onclick = () => el("config-panel").classList.toggle("hidden");
  el("save-config").onclick = () => {
    setBackendUrl(el("backend-url").value.trim());
    el("config-panel").classList.add("hidden");
    loadCards();
    loadTags();
  };
}

el("submit-link").onclick = submitLink;
el("submit-manual").onclick = submitManual;
el("clear-filter").onclick = () => {
  activeTag = null;
  el("clear-filter").classList.add("hidden");
  loadCards();
  loadTags();
};

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}

initConfigPanel();
loadCards();
loadTags();
