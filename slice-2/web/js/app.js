// Bootstrap del editor: carga vocab + prenda, conecta los módulos de render como
// suscriptores del estado, y expone el highlight de marcadores para los forms.

import { api } from "./api.js";
import { setGarment, setVocab, setError, subscribe } from "./state.js";
import { renderForms } from "./forms.js";
import { renderFlat, highlightMarker } from "./flatview.js";
import { renderHistory, wireUndo } from "./history.js";
import { initRender } from "./render.js";

const els = {
  name: document.getElementById("garmentName"),
  version: document.getElementById("versionBadge"),
  error: document.getElementById("error"),
  reference: document.getElementById("referenceImg"),
  referenceMissing: document.getElementById("referenceMissing"),
};

function renderHeader(s) {
  els.name.textContent = s.garment ? s.garment.name : "…";
  els.version.textContent = s.version ? `v${s.version}` : "v—";
  if (s.lastError) {
    els.error.textContent = s.lastError;
    els.error.hidden = false;
  } else {
    els.error.hidden = true;
  }
  // Solo (re)asignar el src si cambió, para no re-pedir la imagen en cada render.
  if (s.garment?.reference_image && !els.reference.src.endsWith(s.garment.reference_image)) {
    // Si la foto falta (gitignored/ausente), mostrar una nota en vez de la <img> rota.
    els.reference.onerror = () => { els.reference.hidden = true; els.referenceMissing.hidden = false; };
    els.reference.onload = () => { els.reference.hidden = false; els.referenceMissing.hidden = true; };
    els.reference.src = s.garment.reference_image;
  }
}

subscribe(renderHeader);
subscribe(renderForms);
subscribe(renderFlat);
subscribe(renderHistory);

// forms.js dispara el highlight del marcador del flat al enfocar/hover una medida
window.__highlightMarker = highlightMarker;

async function boot() {
  if (!api.gid) { location.href = "/"; return; }  // sin gid en la URL → a la biblioteca
  try {
    const [vocab, garment] = await Promise.all([api.getVocab(), api.getGarment()]);
    setVocab(vocab);
    wireUndo();
    setGarment(garment, { structural: true });
  } catch (e) {
    setError(`No se pudo cargar la prenda: ${e.message}`);
  }
}

function wireViewToggle() {
  const editEls = [document.getElementById("doubleView"), document.getElementById("forms"),
                   document.getElementById("historyPanel")];
  const renderView = document.getElementById("renderView");
  const tabEdit = document.getElementById("tabEdit");
  const tabRender = document.getElementById("tabRender");
  let renderInited = false;
  tabEdit.onclick = () => {
    editEls.forEach((e) => e && (e.hidden = false));
    renderView.hidden = true;
    tabEdit.classList.add("active");
    tabRender.classList.remove("active");
  };
  tabRender.onclick = async () => {
    editEls.forEach((e) => e && (e.hidden = true));
    renderView.hidden = false;
    tabRender.classList.add("active");
    tabEdit.classList.remove("active");
    if (!renderInited) { renderInited = true; await initRender(); }
  };
}
wireViewToggle();

boot();
