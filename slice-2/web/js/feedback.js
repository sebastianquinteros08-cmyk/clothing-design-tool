// Feedback visual de guardado: toast "✓ guardado · vN" + flash verde en el campo
// editado. Confirma que la edición se persistió (el flat NO cambia en 2b — eso es
// Slice 3; sin esta señal el autosave se siente "muerto").

let toastEl = null;
let hideTimer = null;

function ensureToast() {
  if (!toastEl) {
    toastEl = document.createElement("div");
    toastEl.id = "saveToast";
    document.body.appendChild(toastEl);
  }
  return toastEl;
}

export function showSaved(version) {
  const el = ensureToast();
  el.textContent = `✓ guardado · v${version}`;
  el.classList.add("show");
  clearTimeout(hideTimer);
  hideTimer = setTimeout(() => el.classList.remove("show"), 1500);
}

export function flashField(el) {
  if (!el) return;
  el.classList.remove("saved-flash");
  void el.offsetWidth; // reflow para reiniciar la animación en ediciones repetidas
  el.classList.add("saved-flash");
}
