// Cliente HTTP del editor. GID sale de la URL (?gid=...); la biblioteca (/) navega acá.
const GID = new URLSearchParams(location.search).get("gid");

async function _json(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  gid: GID,
  getVocab: () => fetch("/api/vocab").then(_json),
  getGarment: () => fetch(`/api/garment/${GID}`).then(_json),
  getVersion: (n) => fetch(`/api/garment/${GID}/version/${n}`).then(_json),
  getHistory: () => fetch(`/api/garment/${GID}/history`).then(_json),
  applyOp: (op) =>
    fetch(`/api/garment/${GID}/op`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ op }),
    }).then(_json),
  restore: (target_version) =>
    fetch(`/api/garment/${GID}/restore`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_version }),
    }).then(_json),
  getFabrics: () => fetch("/api/fabrics").then(_json),
  getRenders: () => fetch(`/api/garment/${GID}/renders`).then(_json),
  createRender: (fabric_id, color, flat_png) =>
    fetch(`/api/garment/${GID}/render`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fabric_id, color, flat_png }),
    }).then(_json),
};
