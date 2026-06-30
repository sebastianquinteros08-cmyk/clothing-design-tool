// Biblioteca de prendas: lista, abre el editor, borra. "Nueva prenda" arranca en /new.html.
const grid = document.getElementById("grid");
const empty = document.getElementById("empty");
const errEl = document.getElementById("error");

function showError(msg) {
  errEl.textContent = msg;
  errEl.hidden = !msg;
}

function editorHref(gid) {
  return `/editor.html?gid=${encodeURIComponent(gid)}`;
}

function card(g) {
  const el = document.createElement("article");
  el.className = "garment-card";
  const href = editorHref(g.garment_id);
  const thumb = g.thumbnail_url
    ? `<img src="${g.thumbnail_url}" alt="" onerror="this.outerHTML='<div class=\\'thumb-missing\\'>sin imagen</div>'">`
    : `<div class="thumb-missing">sin imagen</div>`;
  el.innerHTML = `
    <a class="thumb" href="${href}">${thumb}</a>
    <div class="meta">
      <a class="name" href="${href}"></a>
      <small></small>
    </div>
    <button class="rm">Borrar</button>`;
  // textContent (no innerHTML) para nombre/tipo: evita inyección desde datos de la prenda.
  el.querySelector(".name").textContent = g.name;
  el.querySelector(".meta small").textContent = `${g.garment_type} · v${g.version}`;
  const rm = el.querySelector(".rm");
  rm.dataset.gid = g.garment_id;
  rm.dataset.name = g.name;
  return el;
}

async function load() {
  showError("");
  let list;
  try {
    const res = await fetch("/api/garments");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    list = await res.json();
  } catch (e) {
    showError(`No se pudo cargar la biblioteca: ${e.message}`);
    return;
  }
  grid.innerHTML = "";
  empty.hidden = list.length > 0;
  list.forEach((g) => grid.appendChild(card(g)));
}

grid.addEventListener("click", async (ev) => {
  const btn = ev.target.closest(".rm");
  if (!btn) return;
  ev.preventDefault();
  if (!confirm(`¿Borrar "${btn.dataset.name}"? Se borran la prenda y sus renders.`)) return;
  const res = await fetch(`/api/garments/${encodeURIComponent(btn.dataset.gid)}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    showError("No se pudo borrar la prenda.");
    return;
  }
  load();
});

load();
