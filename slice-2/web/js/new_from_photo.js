// Flujo "Nueva prenda — desde foto": foto → segmentar (puntos +/− / caja) → vectorizar →
// detectar componentes por IA → confirmar/editar → crear la Coat → abrir en el editor.
// El mapeo de coords del canvas viene de Slice 1 (validado E2E) — no se reinventa.

const MAX_W = 800;
const COST_PER_RUN = 0.003;

const state = {
  id: null, falImageUrl: null, w: 0, h: 0,
  scale: 1, mode: "include", points: [], box: null, runs: 0,
};
let stage, imageLayer, markLayer, maskNode = null, drawingBox = null;
let vocab = null;

const $ = (sel) => document.querySelector(sel);
const showError = (msg) => { const e = $("#error"); e.textContent = msg; e.hidden = !msg; };
const setCost = () => { $("#newCost").textContent = `$${(state.runs * COST_PER_RUN).toFixed(4)}`; };

// ---------- Paso 1: foto + segmentación (port de Slice 1) ----------
$("#file").addEventListener("change", async (ev) => {
  const file = ev.target.files[0];
  if (!file) return;
  showError("");
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch("/api/photo/upload", { method: "POST", body: fd });
  if (!res.ok) { showError((await res.json()).detail || "error al subir"); return; }
  const data = await res.json();
  Object.assign(state, {
    id: data.id, falImageUrl: data.fal_image_url, w: data.width, h: data.height,
    points: [], box: null, runs: 0,
  });
  setCost();
  loadImage(data.image_url);
  $("#newTools").hidden = false;
});

function loadImage(url) {
  state.scale = Math.min(1, MAX_W / state.w);
  const dispW = Math.round(state.w * state.scale);
  const dispH = Math.round(state.h * state.scale);
  $("#newCanvas").innerHTML = "";
  stage = new Konva.Stage({ container: "newCanvas", width: dispW, height: dispH });
  imageLayer = new Konva.Layer();
  markLayer = new Konva.Layer();
  stage.add(imageLayer, markLayer);
  maskNode = null;
  const img = new Image();
  img.onload = () => {
    imageLayer.add(new Konva.Image({ image: img, width: dispW, height: dispH }));
    imageLayer.draw();
  };
  img.src = url;
  bindCanvasEvents();
  redrawMarks();
}

document.querySelectorAll("#newTools button.mode").forEach((b) => {
  b.addEventListener("click", () => {
    document.querySelectorAll("#newTools button.mode").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    state.mode = b.dataset.mode;
  });
});
$("#clear").addEventListener("click", () => { state.points = []; state.box = null; redrawMarks(); });

function bindCanvasEvents() {
  stage.on("mousedown", (e) => {
    const pos = stage.getPointerPosition();
    if (state.mode === "box") {
      const ix = toImg(pos.x), iy = toImg(pos.y);
      drawingBox = { x_min: ix, y_min: iy, x_max: ix, y_max: iy };
      return;
    }
    if (e.target !== stage && e.target.attrs.pointIndex !== undefined) {
      state.points.splice(e.target.attrs.pointIndex, 1);
      redrawMarks();
      return;
    }
    const label = state.mode === "include" ? 1 : 0;
    state.points.push({ x: toImg(pos.x), y: toImg(pos.y), label });
    redrawMarks();
  });
  stage.on("mousemove", () => {
    if (!drawingBox) return;
    const pos = stage.getPointerPosition();
    drawingBox.x_max = toImg(pos.x);
    drawingBox.y_max = toImg(pos.y);
    redrawMarks();
  });
  stage.on("mouseup", () => {
    if (drawingBox) { state.box = drawingBox; drawingBox = null; redrawMarks(); }
  });
}

const toImg = (c) => Math.round(c / state.scale);
const clampX = (v) => Math.max(0, Math.min(v, state.w - 1));
const clampY = (v) => Math.max(0, Math.min(v, state.h - 1));

function redrawMarks() {
  markLayer.destroyChildren();
  state.points.forEach((p, i) => {
    markLayer.add(new Konva.Circle({
      x: p.x * state.scale, y: p.y * state.scale, radius: 6,
      fill: p.label === 1 ? "#0a0" : "#c00", stroke: "#fff", strokeWidth: 2, pointIndex: i,
    }));
  });
  const b = drawingBox || state.box;
  if (b) {
    markLayer.add(new Konva.Rect({
      x: Math.min(b.x_min, b.x_max) * state.scale, y: Math.min(b.y_min, b.y_max) * state.scale,
      width: Math.abs(b.x_max - b.x_min) * state.scale, height: Math.abs(b.y_max - b.y_min) * state.scale,
      stroke: "#06f", strokeWidth: 2, dash: [6, 4],
    }));
  }
  markLayer.draw();
}

$("#segment").addEventListener("click", async () => {
  if (!state.id) return;
  showError("");
  const body = {
    id: state.id, fal_image_url: state.falImageUrl,
    points: state.points.map((p) => ({ x: clampX(p.x), y: clampY(p.y), label: p.label })),
    box: state.box ? {
      x_min: clampX(state.box.x_min), y_min: clampY(state.box.y_min),
      x_max: clampX(state.box.x_max), y_max: clampY(state.box.y_max),
    } : null,
  };
  const res = await fetch("/api/photo/segment", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!res.ok) { showError((await res.json()).detail || "error al segmentar"); return; }
  state.runs += 1; setCost();
  const { mask_url } = await res.json();
  drawMask(mask_url + "?t=" + state.runs);
  $("#vectorize").disabled = false;
});

function drawMask(url) {
  if (maskNode) maskNode.destroy();
  const img = new Image();
  img.onload = () => {
    maskNode = new Konva.Image({ image: img, width: stage.width(), height: stage.height(), opacity: 0.5 });
    imageLayer.add(maskNode);
    imageLayer.draw();
  };
  img.src = url;
}

// ---------- Paso 2: vectorizar → detectar → confirmar ----------
$("#vectorize").addEventListener("click", async () => {
  showError("");
  $("#vectorize").disabled = true;
  $("#vectorize").textContent = "Procesando…";
  try {
    const vec = await fetch("/api/photo/vectorize", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: state.id }),
    });
    if (!vec.ok) throw new Error((await vec.json()).detail || "error al vectorizar");

    // Detección por IA del recorte. Si falla → degradar a manual (form en blanco + aviso).
    let detected = null, failed = false;
    const det = await fetch("/api/photo/detect", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: state.id }),
    });
    if (det.ok) { detected = await det.json(); } else { failed = true; }

    vocab = await fetch("/api/vocab").then((r) => r.json());
    buildConfirm(detected, failed);
    $("#stepConfirm").hidden = false;
    $("#stepConfirm").scrollIntoView({ behavior: "smooth" });
  } catch (e) {
    showError(e.message);
    $("#vectorize").disabled = false;
  } finally {
    $("#vectorize").textContent = "Usar este recorte →";
  }
});

// Config de componentes para el form de confirmación (mapea al schema DetectedGarment).
const COMPONENTS = [
  { key: "collar", label: "Cuello", vocabKey: "collar",
    fields: [{ name: "lapel_width_cm", label: "Ancho solapa (cm)", type: "number", step: "0.5" }] },
  { key: "closure", label: "Cierre", vocabKey: "closure",
    fields: [{ name: "button_count", label: "Botones", type: "number" },
             { name: "button_rows", label: "Hileras", type: "number" }] },
  { key: "sleeve", label: "Manga", vocabKey: "sleeve",
    fields: [{ name: "fit", label: "Fit", type: "select", vocabKey: "sleeve_fits" },
             { name: "length", label: "Largo", type: "text" }] },
  { key: "pockets", label: "Bolsillos", vocabKey: "pocket",
    fields: [{ name: "placement", label: "Ubicación", type: "select", vocabKey: "pocket_placements" },
             { name: "count", label: "Cantidad", type: "number" }] },
  { key: "hem", label: "Ruedo", vocabKey: "hem", fields: [] },
];

function optionList(values, selected) {
  const vals = [...values];
  if (selected && !vals.includes(selected)) vals.unshift(selected); // valor custom de la IA
  return vals.map((v) => `<option value="${v}"${v === selected ? " selected" : ""}>${v}</option>`).join("");
}

function buildConfirm(detected, failed) {
  const d = detected || {};
  const note = $("#confirmNote");
  if (failed) {
    note.textContent = "No se pudo autodetectar — completá los componentes a mano.";
    note.hidden = false;
  } else {
    note.hidden = true;
  }
  const form = $("#confirmForm");
  form.innerHTML = "";

  // Metadata
  const meta = document.createElement("div");
  meta.className = "card";
  meta.innerHTML = `
    <h3>Prenda</h3>
    <div class="field"><label>Nombre</label><input id="f-name" type="text" value="${d.name || ""}"></div>
    <div class="field"><label>Silueta</label><input id="f-silhouette" type="text" value="${d.silhouette || ""}"></div>`;
  form.appendChild(meta);

  // Componentes
  COMPONENTS.forEach((c) => {
    const present = !!d[c.key];
    const cd = d[c.key] || {};
    const card = document.createElement("div");
    card.className = "card";
    card.dataset.comp = c.key;
    const subOpts = optionList(vocab[c.vocabKey], cd.subtype);
    const fieldsHtml = c.fields.map((f) => {
      const val = cd[f.name];
      if (f.type === "select") {
        return `<div class="field"><label>${f.label}</label>
          <select data-field="${f.name}">${optionList(vocab[f.vocabKey], val)}</select></div>`;
      }
      const step = f.step ? ` step="${f.step}"` : "";
      return `<div class="field"><label>${f.label}</label>
        <input data-field="${f.name}" type="${f.type}"${step} value="${val ?? ""}"></div>`;
    }).join("");
    card.innerHTML = `
      <h3><span>${c.label}</span>
        <label class="incl"><input type="checkbox" data-include${present ? " checked" : ""}> incluir</label></h3>
      <div class="field"><label>Tipo</label><select data-field="subtype">${subOpts}</select></div>
      ${fieldsHtml}`;
    form.appendChild(card);
  });
}

function readComponent(card) {
  if (!card.querySelector("[data-include]").checked) return null;
  const obj = {};
  card.querySelectorAll("[data-field]").forEach((el) => {
    const key = el.dataset.field;
    if (el.type === "number") {
      obj[key] = el.value === "" ? null : Number(el.value);
    } else {
      obj[key] = el.value || null;
    }
  });
  // Limpiar nulls de campos opcionales (ej. lapel_width_cm) para no romper la validación.
  Object.keys(obj).forEach((k) => { if (obj[k] === null) delete obj[k]; });
  return obj;
}

$("#createBtn").addEventListener("click", async () => {
  showError("");
  const status = $("#createStatus");
  const detected = {
    name: $("#f-name").value.trim() || "Prenda sin nombre",
    silhouette: $("#f-silhouette").value.trim() || "regular",
  };
  document.querySelectorAll("#confirmForm .card[data-comp]").forEach((card) => {
    const obj = readComponent(card);
    if (obj) detected[card.dataset.comp] = obj;
  });

  $("#createBtn").disabled = true;
  status.textContent = "Creando…";
  try {
    const res = await fetch("/api/garments", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ photo_session_id: state.id, detected }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || `HTTP ${res.status}`);
    const { gid } = await res.json();
    location.href = `/editor.html?gid=${encodeURIComponent(gid)}`;
  } catch (e) {
    showError(`No se pudo crear: ${e.message}`);
    status.textContent = "";
    $("#createBtn").disabled = false;
  }
});
