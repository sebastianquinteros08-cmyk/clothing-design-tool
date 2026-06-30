// Vista Render: elige tela de la biblioteca, rasteriza el flat a PNG en el
// cliente (sin dep server-side), renderiza vía fal y muestra la galería.

import { api } from "./api.js";
import { state } from "./state.js";

let fabrics = [];
let selectedFabricId = null;

// Rasteriza el flat (SVG/PNG same-origin) a un dataURL PNG ~1024px de ancho.
function flatToPng(flatUrl) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const targetW = 1024;
      const scale = targetW / (img.naturalWidth || targetW);
      const canvas = document.createElement("canvas");
      canvas.width = targetW;
      canvas.height = Math.round((img.naturalHeight || targetW) * scale);
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      try {
        resolve(canvas.toDataURL("image/png"));
      } catch (e) {
        reject(new Error("no se pudo exportar el flat (canvas tainted): " + e.message));
      }
    };
    img.onerror = () => reject(new Error("no se pudo cargar el flat: " + flatUrl));
    // cache-bust: el flat puede haberse reemplazado (asset); no servir uno viejo cacheado.
    img.src = flatUrl + (flatUrl.includes("?") ? "&" : "?") + "t=" + Date.now();
  });
}

function renderPicker() {
  const el = document.getElementById("fabricPicker");
  el.innerHTML = "";
  for (const f of fabrics) {
    const card = document.createElement("button");
    card.className = "fabric-card" + (f.id === selectedFabricId ? " selected" : "");
    card.innerHTML =
      `<img src="${f.swatch_url}" alt="${f.name}" onerror="this.style.visibility='hidden'">` +
      `<span>${f.name}</span><small>${f.composition}</small>`;
    card.onclick = () => { selectedFabricId = f.id; renderPicker(); };
    el.appendChild(card);
  }
}

function openLightbox(src, caption) {
  const overlay = document.createElement("div");
  overlay.className = "lightbox";
  const img = document.createElement("img");
  img.src = src;
  img.alt = "render";
  const cap = document.createElement("span");
  cap.textContent = caption;
  overlay.append(img, cap);
  overlay.onclick = () => overlay.remove();
  document.addEventListener("keydown", function esc(e) {
    if (e.key === "Escape") { overlay.remove(); document.removeEventListener("keydown", esc); }
  });
  document.body.appendChild(overlay);
}

function renderGallery(records) {
  const el = document.getElementById("renderGallery");
  el.innerHTML = "";
  for (const r of records) {
    const caption = `v${r.garment_version} · ${r.fabric_id} · ${r.color}`;
    const fig = document.createElement("figure");
    fig.className = "render-card";
    fig.innerHTML = `<img src="${r.image_path}" alt="render" title="click para ampliar">` +
      `<figcaption>${caption}</figcaption>`;
    fig.querySelector("img").onclick = () => openLightbox(r.image_path, caption);
    el.appendChild(fig);
  }
}

async function loadGallery() {
  renderGallery(await api.getRenders());
}

async function onRender() {
  const status = document.getElementById("renderStatus");
  const btn = document.getElementById("renderBtn");
  if (!selectedFabricId) { status.textContent = "Elegí una tela primero."; return; }
  const flat = state.garment?.flat?.front;
  if (!flat) { status.textContent = "No hay flat para renderizar."; return; }
  btn.disabled = true;
  status.textContent = "Renderizando… (puede tardar unos segundos)";
  try {
    const flatPng = await flatToPng(flat);
    const color = document.getElementById("renderColor").value.trim() || null;
    await api.createRender(selectedFabricId, color, flatPng);
    status.textContent = "✓ render listo";
    await loadGallery();
  } catch (e) {
    status.textContent = "Error: " + e.message;
  } finally {
    btn.disabled = false;
  }
}

export async function initRender() {
  fabrics = await api.getFabrics();
  selectedFabricId = fabrics[0]?.id ?? null;
  renderPicker();
  document.getElementById("renderBtn").onclick = onRender;
  await loadGallery();
}
