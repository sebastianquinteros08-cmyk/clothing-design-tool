// Panel de historial: lista las versiones (resumen de la op), permite restaurar
// cualquiera, y cablea el botón "Deshacer" (= restaurar la versión anterior).

import { api } from "./api.js";
import { state, setGarment, setError } from "./state.js";
import { showSaved } from "./feedback.js";

async function restoreTo(version) {
  try {
    const payload = await api.restore(version);
    setGarment(payload, { structural: true });
    showSaved(payload.version);
  } catch (e) {
    setError(e.message);
  }
}

export function wireUndo() {
  document.getElementById("undo").addEventListener("click", () => {
    if (state.version > 1) restoreTo(state.version - 1);
  });
}

export async function renderHistory(state) {
  const panel = document.getElementById("historyPanel");
  document.getElementById("undo").disabled = !(state.version > 1);

  let history = [];
  try {
    history = await api.getHistory();
  } catch {
    return; // un fallo del historial no debe romper el editor
  }

  panel.innerHTML = "<h2>Historial</h2>";
  for (const h of [...history].reverse()) {
    const item = document.createElement("div");
    item.className = "histItem" + (h.version === state.version ? " current" : "");
    const left = document.createElement("span");
    left.textContent = `v${h.version} · ${h.op_type}`;
    const btn = document.createElement("button");
    btn.textContent = "Restaurar";
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      restoreTo(h.version);
    });
    item.append(left, btn);
    panel.append(item);
  }
}
