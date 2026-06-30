// Estado en memoria del editor: espejo de lo que devuelve el backend (fuente de verdad).
// Las notificaciones llevan `opts.structural`: true => re-render completo de los forms
// (carga inicial, add/remove componente, restore); false => solo badge/flat/historial
// (ediciones de campo — el DOM del form ya tiene el valor que tipeó el usuario).

const _subs = [];

export const state = {
  garment: null,
  version: null,
  vocab: null,
  lastError: null,
};

export function subscribe(fn) {
  _subs.push(fn);
}

function _notify(opts) {
  for (const fn of _subs) fn(state, opts);
}

export function setVocab(v) {
  state.vocab = v;
}

export function setGarment(payload, opts = { structural: true }) {
  state.garment = payload.garment;
  state.version = payload.version;
  state.lastError = null;
  _notify(opts);
}

export function setError(msg) {
  state.lastError = msg;
  _notify({ structural: false });
}

export function getComponent(id) {
  return (state.garment?.components || []).find((c) => c.component_id === id) || null;
}
