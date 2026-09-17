"use strict";

const COLORES = {
  critica: "#ff5a5f",
  alta: "#ff9f43",
  media: "#f2c94c",
  info: "#58a6ff",
};
const MAX_FLUJOS = 160;
const VIDA_MS = 9000;

const lienzo = document.getElementById("lienzo");
const ctx = lienzo.getContext("2d");
const tooltip = document.getElementById("tooltip");

const estado = {
  nodos: new Map(),
  paises: null,
  flujos: new Map(),
  alertas: new Map(),
  dispositivos: new Map(),
  severidades: new Map(),
  puntero: null,
  desde: null,
};

// ---------------------------------------------------------------- proyección

function dimensiones() {
  const r = lienzo.getBoundingClientRect();
  const escala = window.devicePixelRatio || 1;
  lienzo.width = r.width * escala;
  lienzo.height = r.height * escala;
  ctx.setTransform(escala, 0, 0, escala, 0, 0);
  return { ancho: r.width, alto: r.height };
}

let vista = { ancho: 0, alto: 0 };

function proyectar(lat, lon) {
  return {
    x: (lon + 180) / 360 * vista.ancho,
    y: (90 - lat) / 180 * vista.alto,
  };
}

// ---------------------------------------------------------------- datos

async function json(url, opciones) {
  const r = await fetch(url, opciones);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

async function cargar() {
  const [paises, nodos, dispositivos, guiones] = await Promise.all([
    json("datos/paises.geojson"),
    json("/api/infraestructura"),
    json("/api/dispositivos"),
    json("/api/guiones"),
  ]);
  estado.paises = paises;
  nodos.forEach((n) => estado.nodos.set(n.id, n));
  dispositivos.forEach((d) => estado.dispositivos.set(d.id, d));
  const select = document.getElementById("guion");
  select.innerHTML = guiones
    .map((g) => `<option value="${g.id}">${g.nombre || g.id}</option>`)
    .join("");
}

function puntosDeRuta(flujo) {
  const puntos = [];
  for (const hop of flujo.ruta || []) {
    const nodo = estado.nodos.get(hop.nodo_id);
    if (nodo) puntos.push({ ...proyectar(nodo.lat, nodo.lon), nodo, observado: hop.observado });
  }
  const d = flujo.destino;
  if (d && (!puntos.length || puntos[puntos.length - 1].nodo.id !== d.nodo_id)) {
    puntos.push({ ...proyectar(d.lat, d.lon), nodo: { nombre: d.organizacion, ciudad: d.ciudad, pais: d.pais }, observado: true });
  }
  return puntos;
}

// ---------------------------------------------------------------- dibujo

function dibujarMapa() {
  ctx.fillStyle = "#0a1020";
  ctx.fillRect(0, 0, vista.ancho, vista.alto);
  if (!estado.paises) return;
  ctx.strokeStyle = "#1c2a46";
  ctx.fillStyle = "#121d33";
  ctx.lineWidth = 0.6;
  for (const f of estado.paises.features) {
    const poligonos = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
    for (const poligono of poligonos) {
      for (const anillo of poligono) {
        ctx.beginPath();
        anillo.forEach(([lon, lat], i) => {
          const p = proyectar(lat, lon);
          i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y);
        });
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      }
    }
  }
}

function dibujarNodos() {
  for (const nodo of estado.nodos.values()) {
    const p = proyectar(nodo.lat, nodo.lon);
    const base = nodo.capa === "dispositivos" ? 2.5 : 2;
    ctx.beginPath();
    ctx.arc(p.x, p.y, base, 0, Math.PI * 2);
    ctx.fillStyle = nodo.pais === "AR" ? "#3ddc97" : "#41608f";
    ctx.fill();
  }
}

function colorFlujo(flujo) {
  if (flujo.severidad) return COLORES[flujo.severidad] || "#58a6ff";
  return flujo.cifrado ? "rgba(88,166,255,.55)" : "rgba(242,201,76,.75)";
}

function dibujarFlujos(ahora) {
  for (const [id, flujo] of estado.flujos) {
    const edad = ahora - flujo.visto;
    if (edad > VIDA_MS) { estado.flujos.delete(id); continue; }
    const puntos = flujo.puntos;
    if (puntos.length < 2) continue;
    const color = colorFlujo(flujo);
    const opaco = flujo.severidad ? 1 : Math.max(0.15, 1 - edad / VIDA_MS);

    ctx.globalAlpha = opaco;
    ctx.strokeStyle = color;
    ctx.lineWidth = flujo.severidad ? 1.8 : 0.9;
    ctx.beginPath();
    puntos.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)));
    ctx.stroke();

    // partícula que viaja por la ruta
    const t = ((ahora / 2200) + flujo.fase) % 1;
    const pos = interpolar(puntos, t);
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, flujo.severidad ? 3.4 : 2, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.globalAlpha = 1;

    if (flujo.severidad === "critica") {
      const destino = puntos[puntos.length - 1];
      const radio = 6 + 6 * Math.abs(Math.sin(ahora / 400));
      ctx.beginPath();
      ctx.arc(destino.x, destino.y, radio, 0, Math.PI * 2);
      ctx.strokeStyle = COLORES.critica;
      ctx.lineWidth = 1.2;
      ctx.stroke();
    }
  }
}

function interpolar(puntos, t) {
  const total = puntos.length - 1;
  const idx = Math.min(total - 1, Math.floor(t * total));
  const local = t * total - idx;
  const a = puntos[idx];
  const b = puntos[idx + 1];
  return { x: a.x + (b.x - a.x) * local, y: a.y + (b.y - a.y) * local };
}

function dibujarPuntero() {
  if (!estado.puntero) { tooltip.classList.add("oculto"); return; }
  const { x, y } = estado.puntero;
  let cerca = null;
  let mejor = 12;
  for (const nodo of estado.nodos.values()) {
    const p = proyectar(nodo.lat, nodo.lon);
    const d = Math.hypot(p.x - x, p.y - y);
    if (d < mejor) { mejor = d; cerca = nodo; }
  }
  if (!cerca) { tooltip.classList.add("oculto"); return; }
  tooltip.classList.remove("oculto");
  tooltip.style.left = `${x + 12}px`;
  tooltip.style.top = `${y + 12}px`;
  tooltip.innerHTML = `<b>${cerca.nombre}</b><br>${cerca.organizacion}<br>${cerca.ciudad} (${cerca.pais})`;
}

function bucle() {
  const ahora = performance.now();
  dibujarMapa();
  dibujarNodos();
  dibujarFlujos(ahora);
  dibujarPuntero();
  requestAnimationFrame(bucle);
}

// ---------------------------------------------------------------- panel

function pintarMetricas(m) {
  document.getElementById("metricas").innerHTML = `
    <div>subida<b>${m.mbps_subida} Mbps</b></div>
    <div>bajada<b>${m.mbps_bajada} Mbps</b></div>
    <div>flujos<b>${m.flujos_activos}</b></div>
    <div>destinos<b>${m.destinos}</b></div>
    <div>cifrado<b>${m.porcentaje_cifrado}%</b></div>
    <div>alertas<b>${m.alertas_abiertas}</b></div>`;
}

const ORDEN = { critica: 0, alta: 1, media: 2, info: 3 };

function pintarAlertas() {
  const lista = [...estado.alertas.values()].sort(
    (a, b) => (ORDEN[a.severidad] - ORDEN[b.severidad]) || b.ts.localeCompare(a.ts),
  );
  document.getElementById("contador").textContent = lista.filter((a) => a.estado === "abierta").length;
  document.getElementById("alertas").innerHTML = lista.map((a) => `
    <div class="alerta ${a.severidad} ${a.estado}" data-id="${a.id}">
      <div class="fila"><span>${a.severidad.toUpperCase()} · ${a.regla}</span><span>${a.ts.slice(11, 19)}</span></div>
      <div class="titulo">${a.titulo}</div>
      <div class="texto">${a.explicacion}</div>
      <div class="fila"><span>${nombreDispositivo(a.dispositivo_id)}</span><span>${a.fuente_explicacion}</span></div>
    </div>`).join("");
}

function nombreDispositivo(id) {
  const d = estado.dispositivos.get(id);
  return d ? d.nombre : id;
}

async function pintarDestinos() {
  const destinos = await json("/api/metricas/destinos");
  document.getElementById("destinos").innerHTML = destinos.slice(0, 8).map((d) => `
    <div class="item"><span>${d.organizacion}</span><span>${d.porcentaje}%</span></div>`).join("");
}

function abrirDetalle(alerta) {
  const evidencia = Object.entries(alerta.evidencia || {})
    .map(([k, v]) => `<dt>${k}</dt><dd>${typeof v === "object" ? JSON.stringify(v) : v}</dd>`).join("");
  document.getElementById("detalle-cuerpo").innerHTML = `
    <h3>${alerta.titulo}</h3>
    <div class="fila">${alerta.severidad.toUpperCase()} · ${alerta.regla} · ${alerta.ts.slice(11, 19)}</div>
    <p>${alerta.explicacion}</p>
    <p><b>Qué hacer:</b> ${alerta.accion_sugerida || "—"}</p>
    <dl><dt>dispositivo</dt><dd>${nombreDispositivo(alerta.dispositivo_id)}</dd>
    <dt>estado</dt><dd>${alerta.estado}</dd>
    <dt>explicación</dt><dd>${alerta.fuente_explicacion}</dd>${evidencia}</dl>
    ${alerta.alertas_relacionadas?.length ? `<p><b>Alertas relacionadas:</b> ${alerta.alertas_relacionadas.join(", ")}</p>` : ""}
    <div class="acciones">
      <button data-accion="reconocer" data-id="${alerta.id}">Reconocer</button>
      <button data-accion="cerrar" data-id="${alerta.id}" class="secundario">Cerrar alerta</button>
    </div>`;
  document.getElementById("detalle").classList.remove("oculto");
}

// ---------------------------------------------------------------- websocket

function absorberFlujo(flujo) {
  const previo = estado.flujos.get(flujo.id);
  estado.flujos.set(flujo.id, {
    id: flujo.id,
    puntos: previo ? previo.puntos : puntosDeRuta(flujo),
    fase: previo ? previo.fase : Math.random(),
    visto: performance.now(),
    cifrado: Boolean(flujo.protocolo?.cifrado),
    severidad: previo?.severidad || estado.severidades.get(flujo.dispositivo_id),
    dispositivo_id: flujo.dispositivo_id,
  });
  if (estado.flujos.size > MAX_FLUJOS) {
    estado.flujos.delete(estado.flujos.keys().next().value);
  }
}

function absorberAlerta(alerta) {
  if (estado.desde && Date.parse(alerta.ts) < estado.desde) return;
  estado.alertas.set(alerta.id, alerta);
  if (ORDEN[alerta.severidad] <= ORDEN.alta) marcarRutas(alerta);
  pintarAlertas();
}

// La correlacionada no trae flujo_id: se resaltan todas las rutas del equipo.
function marcarRutas(alerta) {
  const previa = estado.severidades.get(alerta.dispositivo_id);
  if (previa === undefined || ORDEN[alerta.severidad] < ORDEN[previa]) {
    estado.severidades.set(alerta.dispositivo_id, alerta.severidad);
  }
  for (const flujo of estado.flujos.values()) {
    if (flujo.id === alerta.flujo_id || flujo.dispositivo_id === alerta.dispositivo_id) {
      flujo.severidad = estado.severidades.get(alerta.dispositivo_id);
    }
  }
}

function conectar() {
  const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/flujos`);
  const chip = document.getElementById("estado");

  ws.onopen = () => { chip.textContent = "en vivo"; chip.style.color = "#3ddc97"; };
  ws.onclose = () => {
    chip.textContent = "desconectado";
    chip.style.color = "#ff5a5f";
    setTimeout(conectar, 1500);
  };
  ws.onmessage = (ev) => {
    const { tipo, datos } = JSON.parse(ev.data);
    if (tipo === "flujo") absorberFlujo(datos);
    else if (tipo === "alerta") absorberAlerta(datos);
    else if (tipo === "metricas") pintarMetricas(datos);
    else if (tipo === "dispositivo") estado.dispositivos.set(datos.id, datos);
    else if (tipo === "estado") {
      chip.textContent = datos.ia_conectada ? `en vivo · ${datos.modelo}` : "en vivo · plantillas";
    } else if (tipo === "guion") {
      chip.textContent = `${datos.id} · ${datos.t}s / ${datos.duracion_s}s`;
    }
  };
}

// ---------------------------------------------------------------- eventos

document.getElementById("lanzar").onclick = async () => {
  const id = document.getElementById("guion").value;
  estado.desde = Date.now();
  estado.alertas.clear();
  estado.flujos.clear();
  estado.severidades.clear();
  pintarAlertas();
  await fetch(`/api/guiones/${id}/lanzar`, { method: "POST" });
};

document.getElementById("detener").onclick = async () => {
  const evaluacion = await json("/api/guiones/detener", { method: "POST" });
  document.getElementById("estado").textContent =
    `detenido · ${evaluacion.alertas_generadas} alertas`;
};

document.getElementById("resumir").onclick = async () => {
  const p = document.getElementById("resumen");
  p.textContent = "pensando…";
  const r = await json("/api/asistente/resumen-turno", { method: "POST" });
  p.textContent = `${r.texto} (${r.fuente})`;
};

document.getElementById("alertas").onclick = (ev) => {
  const tarjeta = ev.target.closest(".alerta");
  if (tarjeta) abrirDetalle(estado.alertas.get(tarjeta.dataset.id));
};

document.getElementById("cerrar-detalle").onclick = () =>
  document.getElementById("detalle").classList.add("oculto");

document.getElementById("detalle-cuerpo").onclick = async (ev) => {
  const boton = ev.target.closest("button[data-accion]");
  if (!boton) return;
  const alerta = await json(`/api/alertas/${boton.dataset.id}/${boton.dataset.accion}`, { method: "POST" });
  estado.alertas.set(alerta.id, alerta);
  pintarAlertas();
  abrirDetalle(alerta);
};

lienzo.onmousemove = (ev) => {
  const r = lienzo.getBoundingClientRect();
  estado.puntero = { x: ev.clientX - r.left, y: ev.clientY - r.top };
};
lienzo.onmouseleave = () => { estado.puntero = null; };

window.onresize = () => {
  vista = dimensiones();
  for (const flujo of estado.flujos.values()) flujo.puntos = [];
  estado.flujos.clear();
};

(async function arrancar() {
  vista = dimensiones();
  await cargar();
  (await json("/api/alertas")).forEach(absorberAlerta);
  conectar();
  pintarDestinos();
  setInterval(pintarDestinos, 10000);
  bucle();
})();
