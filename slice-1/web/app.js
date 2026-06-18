const MAX_W = 800;                       // ancho de display máximo
const COST_PER_RUN = 0.003;

const state = {
  id: null, falImageUrl: null, w: 0, h: 0,
  scale: 1, mode: "include", points: [], box: null, runs: 0,
};

let stage, imageLayer, markLayer, maskNode = null;
let drawingBox = null;                    // rect Konva mientras se arrastra

const $ = (sel) => document.querySelector(sel);
const showError = (msg) => { const e = $("#error"); e.textContent = msg; e.hidden = !msg; };
const setCost = () => { $("#cost").textContent = `$${(state.runs * COST_PER_RUN).toFixed(4)} acumulado`; };

// ---- Upload ----
$("#file").addEventListener("change", async (ev) => {
  const file = ev.target.files[0];
  if (!file) return;
  showError("");
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch("/api/upload", { method: "POST", body: fd });
  if (!res.ok) { showError((await res.json()).detail || "error al subir"); return; }
  const data = await res.json();
  Object.assign(state, {
    id: data.id, falImageUrl: data.fal_image_url, w: data.width, h: data.height,
    points: [], box: null, runs: 0,
  });
  setCost();
  loadImage(data.image_url);
  $("#tools").hidden = false;
});

function loadImage(url) {
  state.scale = Math.min(1, MAX_W / state.w);
  const dispW = Math.round(state.w * state.scale);
  const dispH = Math.round(state.h * state.scale);

  $("#canvas").innerHTML = "";
  stage = new Konva.Stage({ container: "canvas", width: dispW, height: dispH });
  imageLayer = new Konva.Layer();
  markLayer = new Konva.Layer();
  stage.add(imageLayer, markLayer);
  maskNode = null;

  const img = new Image();
  img.onload = () => {
    const kimg = new Konva.Image({ image: img, width: dispW, height: dispH });
    imageLayer.add(kimg);
    imageLayer.draw();
  };
  img.src = url;

  bindCanvasEvents();
  redrawMarks();
}

// ---- Modos ----
document.querySelectorAll("button.mode").forEach((b) => {
  b.addEventListener("click", () => {
    document.querySelectorAll("button.mode").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    state.mode = b.dataset.mode;
  });
});

$("#clear").addEventListener("click", () => {
  state.points = []; state.box = null; redrawMarks();
});

// ---- Eventos de canvas ----
function bindCanvasEvents() {
  stage.on("mousedown", (e) => {
    const pos = stage.getPointerPosition();
    if (state.mode === "box") {
      const ix = toImg(pos.x), iy = toImg(pos.y);
      drawingBox = { x_min: ix, y_min: iy, x_max: ix, y_max: iy };
      return;
    }
    // click sobre un punto existente lo borra
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

// conversión canvas->imagen: dividir por el factor de escala y redondear.
// El clamp a los límites se aplica por eje al armar el body del segment (clampX/clampY),
// y el backend revalida (build_prompts). Verificado por el test de mapeo (Task 9).
function toImg(canvasCoord) {
  return Math.round(canvasCoord / state.scale);
}

function clampX(v) { return Math.max(0, Math.min(v, state.w - 1)); }
function clampY(v) { return Math.max(0, Math.min(v, state.h - 1)); }

function redrawMarks() {
  markLayer.destroyChildren();
  state.points.forEach((p, i) => {
    markLayer.add(new Konva.Circle({
      x: p.x * state.scale, y: p.y * state.scale, radius: 6,
      fill: p.label === 1 ? "#0a0" : "#c00", stroke: "#fff", strokeWidth: 2,
      pointIndex: i,
    }));
  });
  const b = drawingBox || state.box;
  if (b) {
    markLayer.add(new Konva.Rect({
      x: Math.min(b.x_min, b.x_max) * state.scale,
      y: Math.min(b.y_min, b.y_max) * state.scale,
      width: Math.abs(b.x_max - b.x_min) * state.scale,
      height: Math.abs(b.y_max - b.y_min) * state.scale,
      stroke: "#06f", strokeWidth: 2, dash: [6, 4],
    }));
  }
  markLayer.draw();
}

// ---- Segmentar ----
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
  const res = await fetch("/api/segment", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!res.ok) { showError((await res.json()).detail || "error al segmentar"); return; }
  state.runs += 1; setCost();
  const { mask_url } = await res.json();
  drawMask(mask_url + "?t=" + state.runs);   // cache-bust: la máscara se sobrescribe
  $("#vectorize").disabled = false;
});

function drawMask(url) {
  if (maskNode) maskNode.destroy();
  const img = new Image();
  img.onload = () => {
    maskNode = new Konva.Image({
      image: img, width: stage.width(), height: stage.height(), opacity: 0.5,
    });
    imageLayer.add(maskNode);
    imageLayer.draw();
  };
  img.src = url;
}

// ---- Vectorizar ----
$("#vectorize").addEventListener("click", async () => {
  showError("");
  const res = await fetch("/api/vectorize", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: state.id }),
  });
  if (!res.ok) { showError((await res.json()).detail || "error al vectorizar"); return; }
  const { svg_url } = await res.json();
  const bust = svg_url + "?t=" + state.runs;
  $("#download").href = bust;
  $("#svgPreview").innerHTML = `<img src="${bust}" alt="flat">`;
  $("#result").hidden = false;
});
