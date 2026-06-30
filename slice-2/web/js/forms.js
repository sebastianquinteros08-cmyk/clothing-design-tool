// Formularios sobre el DSL: cards de componentes (dropdowns + campos), sliders de
// medidas y metadata. Cada cambio arma una Operation y la despacha (autosave, con
// debounce en sliders). Re-render completo solo en cambios estructurales.

import { api } from "./api.js";
import { setGarment, setError } from "./state.js";
import { showSaved, flashField } from "./feedback.js";

const CUSTOM = "__custom__";

// Campos editables por tipo de componente. `vocab` referencia una clave de /api/vocab.
const FIELD_SCHEMA = {
  collar: [
    { f: "subtype", t: "subtype", vocab: "collar" },
    { f: "lapel_width_cm", t: "number", step: 0.5 },
  ],
  closure: [
    { f: "subtype", t: "subtype", vocab: "closure" },
    { f: "button_count", t: "number", step: 1 },
    { f: "button_rows", t: "number", step: 1 },
  ],
  sleeve: [
    { f: "subtype", t: "subtype", vocab: "sleeve" },
    { f: "fit", t: "select", vocab: "sleeve_fits" },
    { f: "length", t: "text" },
  ],
  pocket: [
    { f: "subtype", t: "subtype", vocab: "pocket" },
    { f: "placement", t: "select", vocab: "pocket_placements" },
    { f: "count", t: "number", step: 1 },
  ],
  hem: [{ f: "subtype", t: "subtype", vocab: "hem" }],
};

function debounce(fn, ms) {
  let t;
  return (...a) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...a), ms);
  };
}

// structural=true rebuildea los forms tras la respuesta (add/remove); false los deja
// como están (el DOM ya refleja la edición). En error: revertir refrescando del backend.
async function dispatch(op, { structural = false, flashEl = null } = {}) {
  try {
    const payload = await api.applyOp(op);
    setGarment(payload, { structural });
    showSaved(payload.version);
    if (flashEl) flashField(flashEl);
  } catch (e) {
    // Revertir primero (re-fetch resetea lastError y restaura el valor bueno en el DOM),
    // y mostrar el error DESPUÉS para que persista visible (si no, el revert lo limpia).
    try {
      setGarment(await api.getGarment(), { structural: true });
    } catch {
      /* si el re-fetch falla, igual mostramos el error original abajo */
    }
    setError(e.message);
  }
}
const dispatchDebounced = debounce(dispatch, 300);

function fieldRow(labelText, ...controls) {
  const wrap = document.createElement("div");
  wrap.className = "field";
  const label = document.createElement("label");
  label.textContent = labelText;
  wrap.append(label, ...controls);
  return wrap;
}

function setField(comp, field, value, flashEl) {
  dispatch(
    { op_type: "set_component_field", component_id: comp.component_id, field, value },
    { flashEl },
  );
}

function subtypeRow(comp, vocabList) {
  const sel = document.createElement("select");
  for (const v of vocabList) {
    const o = document.createElement("option");
    o.value = v;
    o.textContent = v;
    sel.append(o);
  }
  const customOpt = document.createElement("option");
  customOpt.value = CUSTOM;
  customOpt.textContent = "otro…";
  sel.append(customOpt);

  const txt = document.createElement("input");
  txt.type = "text";
  txt.placeholder = "subtipo custom";
  txt.className = "custom-input";

  const isCustom = !vocabList.includes(comp.subtype);
  sel.value = isCustom ? CUSTOM : comp.subtype;
  txt.value = isCustom ? comp.subtype : "";
  txt.hidden = !isCustom;

  sel.addEventListener("change", () => {
    if (sel.value === CUSTOM) {
      txt.hidden = false;
      txt.focus();
    } else {
      txt.hidden = true;
      setField(comp, "subtype", sel.value, sel);
    }
  });
  txt.addEventListener("change", () => {
    const v = txt.value.trim();
    if (v) setField(comp, "subtype", v, txt);
  });

  const row = fieldRow("subtype", sel, txt);
  if (isCustom) {
    const tag = document.createElement("span");
    tag.className = "custom-tag";
    tag.textContent = "custom";
    row.append(tag);
  }
  return row;
}

function selectRow(comp, spec, vocabList) {
  const sel = document.createElement("select");
  const values = vocabList.includes(comp[spec.f]) ? vocabList : [comp[spec.f], ...vocabList];
  for (const v of values) {
    const o = document.createElement("option");
    o.value = v;
    o.textContent = v;
    sel.append(o);
  }
  sel.value = comp[spec.f];
  sel.addEventListener("change", () => setField(comp, spec.f, sel.value, sel));
  return fieldRow(spec.f, sel);
}

function inputRow(comp, spec) {
  const input = document.createElement("input");
  input.type = spec.t;
  if (spec.step) input.step = spec.step;
  input.value = comp[spec.f] ?? "";
  input.addEventListener("change", () => {
    const value = spec.t === "number" ? Number(input.value) : input.value;
    setField(comp, spec.f, value, input);
  });
  return fieldRow(spec.f, input);
}

function componentCard(comp, vocab) {
  const card = document.createElement("div");
  card.className = "card";
  const h = document.createElement("h3");
  h.textContent = comp.kind;
  const rm = document.createElement("button");
  rm.className = "rm";
  rm.textContent = "Quitar";
  rm.addEventListener("click", () =>
    dispatch({ op_type: "remove_component", component_id: comp.component_id }, { structural: true }),
  );
  h.append(" ", rm);
  card.append(h);

  for (const spec of FIELD_SCHEMA[comp.kind] || []) {
    if (spec.t === "subtype") card.append(subtypeRow(comp, vocab[spec.vocab]));
    else if (spec.t === "select") card.append(selectRow(comp, spec, vocab[spec.vocab]));
    else card.append(inputRow(comp, spec));
  }
  return card;
}

function addComponentRow(vocab) {
  const wrap = document.createElement("div");
  wrap.className = "add-component";
  const sel = document.createElement("select");
  for (const kind of Object.keys(FIELD_SCHEMA)) {
    const o = document.createElement("option");
    o.value = kind;
    o.textContent = kind;
    sel.append(o);
  }
  const btn = document.createElement("button");
  btn.textContent = "Agregar componente";
  btn.addEventListener("click", () => {
    const kind = sel.value;
    const defaultSubtype = vocab[FIELD_SCHEMA[kind][0].vocab][0];
    dispatch(
      { op_type: "add_component", component: { kind, subtype: defaultSubtype } },
      { structural: true },
    );
  });
  wrap.append(sel, btn);
  return wrap;
}

function measureRow(pom) {
  const wrap = document.createElement("div");
  wrap.className = "field measure";
  wrap.dataset.pom = pom.code;

  const label = document.createElement("label");
  label.textContent = `${pom.code} — ${pom.description}`;

  const slider = document.createElement("input");
  slider.type = "range";
  slider.min = "0";
  slider.max = "200";
  slider.step = "0.5";
  slider.value = pom.base_measurement;

  const out = document.createElement("output");
  out.textContent = `${pom.base_measurement} cm`;

  const send = () =>
    dispatchDebounced(
      {
        op_type: "set_measurement",
        pom_code: pom.code,
        base_measurement: Number(slider.value),
        tol_plus: pom.tol_plus,
        tol_minus: pom.tol_minus,
      },
      { flashEl: slider },
    );

  slider.addEventListener("input", () => {
    out.textContent = `${slider.value} cm`;
    send();
  });
  const hl = (on) => window.__highlightMarker && window.__highlightMarker(pom.code, on);
  slider.addEventListener("focus", () => {
    wrap.classList.add("highlight");
    hl(true);
  });
  slider.addEventListener("blur", () => {
    wrap.classList.remove("highlight");
    hl(false);
  });
  slider.addEventListener("mouseenter", () => hl(true));
  slider.addEventListener("mouseleave", () => {
    if (document.activeElement !== slider) hl(false);
  });

  wrap.append(label, slider, out);
  out.insertAdjacentText("afterend", ` ±${pom.tol_plus}/${pom.tol_minus}`);
  if (pom.derivation) {
    const d = document.createElement("span");
    d.className = "deriv";
    d.textContent = `derivado: ${pom.derivation.body_measure} + ${pom.derivation.ease_cm} ease`;
    wrap.append(d);
  }
  return wrap;
}

export function renderForms(state, opts) {
  if (opts && !opts.structural) return; // edición de campo: el DOM ya está correcto
  if (!state.garment || !state.vocab) return;
  const g = state.garment;

  const meta = document.getElementById("metadataPanel");
  meta.innerHTML = "<h2>Prenda</h2>";
  for (const f of ["name", "description", "silhouette"]) {
    const input = document.createElement("input");
    input.type = "text";
    input.value = g[f] ?? "";
    input.addEventListener("change", () =>
      dispatch({ op_type: "set_garment_field", field: f, value: input.value }, { flashEl: input }),
    );
    meta.append(fieldRow(f, input));
  }

  const comps = document.getElementById("componentsPanel");
  comps.innerHTML = "<h2>Componentes</h2>";
  for (const c of g.components) comps.append(componentCard(c, state.vocab));
  comps.append(addComponentRow(state.vocab));

  const meas = document.getElementById("measurementsPanel");
  meas.innerHTML = "<h2>Medidas</h2>";
  for (const pom of g.measurements.poms) meas.append(measureRow(pom));
}
