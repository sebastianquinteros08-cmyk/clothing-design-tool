// Doble vista — lado flat: dibuja el flat SVG (estático) y los marcadores de POM
// encima (coords en fracción [0,1] de las annotations). El stage respeta el aspect
// ratio del flat (ancho fijo, alto según la imagen). highlightMarker resalta el
// marcador de un POM cuando se enfoca/hover su medida.

let stage = null;
let imgLayer = null;
let markerLayer = null;
let lastFlatSrc = null;
let annotations = [];
const markers = {}; // pom_code -> Konva.Circle
const STAGE_W = 340; // ancho fijo; el alto se deriva del aspect ratio de la imagen
let dispW = STAGE_W;
let dispH = 460;

function ensureStage() {
  if (stage) return;
  stage = new Konva.Stage({ container: "flatStage", width: dispW, height: dispH });
  imgLayer = new Konva.Layer();
  markerLayer = new Konva.Layer();
  stage.add(imgLayer, markerLayer);
}

function drawMarkers() {
  markerLayer.destroyChildren();
  for (const k of Object.keys(markers)) delete markers[k];
  for (const a of annotations) {
    const circle = new Konva.Circle({
      x: a.x * dispW,
      y: a.y * dispH,
      radius: 7,
      fill: "#c98a00",
      stroke: "#fff",
      strokeWidth: 2,
      opacity: 0.9,
    });
    const label = new Konva.Text({
      x: a.x * dispW + 9,
      y: a.y * dispH - 7,
      text: a.pom_code,
      fontSize: 13,
      fill: "#3a3a3a",
    });
    markers[a.pom_code] = circle;
    markerLayer.add(circle, label);
  }
  markerLayer.draw();
}

export function renderFlat(state) {
  if (!state.garment?.flat) return;
  ensureStage();
  const flat = state.garment.flat;
  annotations = flat.annotations || [];

  if (flat.front !== lastFlatSrc) {
    lastFlatSrc = flat.front;
    const img = new Image();
    img.onload = () => {
      // respetar aspect ratio: ancho fijo, alto proporcional
      dispW = STAGE_W;
      dispH = Math.round((img.naturalHeight / img.naturalWidth) * STAGE_W) || dispH;
      stage.width(dispW);
      stage.height(dispH);
      imgLayer.destroyChildren();
      imgLayer.add(new Konva.Image({ image: img, width: dispW, height: dispH }));
      imgLayer.draw();
      drawMarkers(); // re-ubicar markers con las dims reales ya conocidas
    };
    img.src = flat.front + (flat.front.includes("?") ? "&" : "?") + "t=" + Date.now();
  }

  drawMarkers();
}

export function highlightMarker(pomCode, on) {
  const circle = markers[pomCode];
  if (!circle) return;
  circle.radius(on ? 12 : 7);
  circle.fill(on ? "#e53935" : "#c98a00");
  markerLayer.draw();
}
