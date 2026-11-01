/* Refugio web app: the map and the panel. Plain JavaScript, no build step.
 *
 * Data:  web/data/<city>/  (made by pipeline/build.py and pipeline/render_html.py)
 * Map:   MapLibre GL JS with an Amazon Location Service base map
 * Grid:  H3 hexagons, drawn in the browser with h3-js
 */

// ---------------------------------------------------------------- 1. Settings

const CONFIG = window.REFUGIO_CONFIG || {}; // from config.js: { region, apiKey } (not in git)
const REGION = CONFIG.region || "us-west-2";
const API_KEY = CONFIG.apiKey || "";

// Map colors: same 5 blues as pipeline/render_html.py. Lighter = closer to a refuge.
const RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"];
const MIN_POP60_HIGHLIGHT = 10; // "only where older adults live" filter

const params = new URLSearchParams(location.search);
const state = {
  city: params.get("city") || "culiacan",
  mode: "ref", // "ref" = refuges only, "any" = refuges + relief stores
  lang: params.get("lang") === "en" ? "en" : "es",
  refuges: [], // refuge list of the current city (index = "iref" in hex.json)
};

// ---------------------------------------------------------------- 2. Language

// Text created by JavaScript. Text written in index.html uses <span lang="es|en"> instead.
const TEXT = {
  es: {
    minutes: (m) => (m > 60 ? "más de 60 min" : `${Math.round(m)} min`),
    toNearest: "a pie hasta el refugio más cercano",
    toNearestAny: "a pie hasta el lugar fresco más cercano",
    olderHere: (p60, pop) => `${p60} adultos mayores · ${pop} habitantes en este hexágono`,
    proposal: "Edificio público propuesto",
    proposalGain: (n) => `+${n} adultos mayores tendrían un refugio a ≤10 min`,
    demo: "Modo demo: falta la API key de Amazon Location, así que no se ve el mapa base. Los datos y las cifras sí son reales.",
    langButton: "EN",
    types: { plaza: "Plaza comercial", departamental: "Tienda departamental", super: "Supermercado",
             biblioteca: "Biblioteca", museo: "Museo", cultura: "Centro cultural",
             comunitario: "Centro comunitario / DIF", farmacia: "Farmacia", conveniencia: "Tienda de conveniencia" },
  },
  en: {
    minutes: (m) => (m > 60 ? "over 60 min" : `${Math.round(m)} min`),
    toNearest: "on foot to the nearest refuge",
    toNearestAny: "on foot to the nearest cool place",
    olderHere: (p60, pop) => `${p60} older adults · ${pop} people in this hexagon`,
    proposal: "Proposed public building",
    proposalGain: (n) => `+${n} older adults would have a refuge within 10 min`,
    demo: "Demo mode: the Amazon Location API key is missing, so the base map is hidden. The data and figures are real.",
    langButton: "ES",
    types: { plaza: "Shopping mall", departamental: "Department store", super: "Supermarket",
             biblioteca: "Library", museo: "Museum", cultura: "Cultural center",
             comunitario: "Community center", farmacia: "Pharmacy", conveniencia: "Convenience store" },
  },
};
const t = () => TEXT[state.lang];
const fmt = (n) => Math.round(n).toLocaleString("en-US"); // 17,039 (same in Mexico)

function setLanguage(lang) {
  state.lang = lang;
  document.documentElement.lang = lang; // CSS hides the other language's <span lang>
  document.getElementById("lang-toggle").textContent = t().langButton;
  if (usingDemo) showNotice(t().demo);
  updateUrl({ lang: lang === "en" ? "en" : null });
}

function updateUrl(changes) {
  for (const [k, v] of Object.entries(changes)) (v ? params.set(k, v) : params.delete(k));
  const q = params.toString();
  history.replaceState(null, "", q ? `?${q}` : location.pathname);
}

// ---------------------------------------------------------------- 3. The map

// Amazon Location base map (Monochrome keeps the hexagon colors readable)
const STYLE_URL = `https://maps.geo.${REGION}.amazonaws.com/v2/styles/Monochrome/descriptor?key=${API_KEY}&color-scheme=Light`;
// Demo mode: a plain background instead of the base map
const DEMO_STYLE = { version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": "#eef0f2" } }] };

const map = new maplibregl.Map({
  container: "map",
  style: API_KEY ? STYLE_URL : DEMO_STYLE,
  center: [-107.394, 24.799],
  zoom: 11.8,
  attributionControl: {
    compact: true,
    customAttribution: "© OpenStreetMap contributors, Overture Maps Foundation · Population: Meta & CIESIN HRSL (CC BY 4.0)",
  },
});
map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

// Keep the map's center in the part of the screen the panel doesn't cover
const isPhone = () => window.matchMedia("(max-width: 899px)").matches;
function fitPadding() {
  const panel = document.getElementById("panel");
  map.setPadding(isPhone() ? { top: 0, right: 0, left: 0, bottom: Math.round(panel.offsetHeight * 0.9) }
                           : { top: 0, right: 0, bottom: 0, left: panel.offsetWidth + 24 });
}
fitPadding();
window.addEventListener("resize", fitPadding);

let usingDemo = !API_KEY;
if (usingDemo) showNotice(t().demo);

// If the base map can't load (no key, wrong key, blocked domain), switch to demo mode
map.on("error", (e) => {
  if (!usingDemo && !map.isStyleLoaded()) {
    console.warn("Base map failed, switching to demo mode:", e.error);
    usingDemo = true;
    showNotice(t().demo);
    map.setStyle(DEMO_STYLE);
  }
});

// Each time a style finishes loading (the real one or the demo one), add our layers on top
map.on("style.load", () => addDataLayers().catch((err) => console.error(err)));

// Start downloading the data right away, while the base map loads
let cityData = loadCity(state.city);

async function loadCity(city) {
  const get = (file) => fetch(`data/${city}/${file}`).then((r) => {
    if (!r.ok) throw new Error(`${file}: HTTP ${r.status}`);
    return r.json();
  });
  const [hex, refuges, proposals, stats] = await Promise.all(
    [get("hex.json"), get("refuges.geojson"), get("proposals.geojson"), get("stats.json")]);
  return { hex, refuges, proposals, stats };
}

// hex.json stores one row per hexagon; turn each into a polygon the map can draw
function hexagonsToGeoJSON(hex) {
  const col = Object.fromEntries(hex.fields.map((name, i) => [name, i]));
  return {
    type: "FeatureCollection",
    features: hex.rows.map((row, id) => ({
      type: "Feature",
      id, // needed for the hover highlight
      properties: { ref: row[col.ref], any: row[col.any], pop: row[col.pop], pop60: row[col.pop60],
                    iref: row[col.iref], iany: row[col.iany] },
      geometry: { type: "Polygon", coordinates: [h3.cellToBoundary(row[col.h], true)] }, // true = [lon, lat]
    })),
  };
}

// Color by walking minutes: <=5, 5-10, 10-15, 15-20, >20 (minutes come rounded to 0.1)
function colorBy(field) {
  return ["step", ["get", field], RAMP[0], 5.05, RAMP[1], 10.05, RAMP[2], 15.05, RAMP[3], 20.05, RAMP[4]];
}

async function addDataLayers() {
  if (map.getSource("hexes")) return; // already added for this style
  const data = await cityData;
  state.refuges = data.refuges.features;

  // Put the hexagons under the base map's labels, so street names stay readable
  const firstLabel = map.getStyle().layers.find((l) => l.type === "symbol")?.id;

  map.addSource("hexes", { type: "geojson", data: hexagonsToGeoJSON(data.hex) });
  map.addLayer({ id: "hexes", type: "fill", source: "hexes",
                 paint: { "fill-color": colorBy(state.mode), "fill-opacity": 0.78, "fill-outline-color": "rgba(255,255,255,0.25)" } },
               firstLabel);
  map.addLayer({ id: "hex-hover", type: "line", source: "hexes",
                 paint: { "line-color": "#0b0b0b", "line-width": 2,
                          "line-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 1, 0] } },
               firstLabel);

  map.addSource("refuges", { type: "geojson", data: data.refuges });
  map.addLayer({ id: "alivio", type: "circle", source: "refuges", filter: ["==", ["get", "k"], "alivio"],
                 layout: { visibility: state.mode === "any" ? "visible" : "none" },
                 paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 11, 1.8, 15, 4],
                          "circle-color": "#52514e", "circle-stroke-color": "#ffffff", "circle-stroke-width": 1 } });
  map.addLayer({ id: "refugios", type: "circle", source: "refuges", filter: ["==", ["get", "k"], "refugio"],
                 paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 11, 3, 15, 6.5],
                          "circle-color": "#ffffff", "circle-stroke-color": "#0b0b0b", "circle-stroke-width": 1.5 } });

  addProposalMarkers(data.proposals);
  applyFilters();
  map.jumpTo({ center: data.stats.center, zoom: data.stats.zoom });
}

// The 10 proposed buildings: numbered markers (HTML, so they work even without the base map)
let proposalMarkers = [];
function addProposalMarkers(proposals) {
  proposalMarkers.forEach((m) => m.remove());
  proposalMarkers = proposals.features.map((f) => {
    const p = f.properties;
    const el = document.createElement("button");
    el.className = "proposal-marker";
    el.type = "button";
    el.textContent = p.rank;
    el.setAttribute("aria-label", `${p.rank}. ${p.name}`);
    const popup = new maplibregl.Popup({ offset: 14 }).setHTML(proposalHtml(p));
    return new maplibregl.Marker({ element: el }).setLngLat(f.geometry.coordinates).setPopup(popup).addTo(map);
  });
}

function proposalHtml(p) {
  return `<p class="pop-kicker">${t().proposal} #${p.rank}</p><p class="pop-title">${escapeHtml(p.name)}</p>` +
         `<p>${t().proposalGain(fmt(p.new_pop60))}</p>`;
}

// ---------------------------------------------------------------- 4. Hover and click

const hoverPopup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 8, className: "hover-popup" });
let hoveredId = null;

function hexHtml(p) {
  const minutes = state.mode === "ref" ? p.ref : p.any;
  const idx = state.mode === "ref" ? p.iref : p.iany;
  const place = idx >= 0 ? state.refuges[idx]?.properties : null;
  const where = place ? `<p>${escapeHtml(place.n)} · ${t().types[place.t] || place.t}</p>` : "";
  return `<p class="pop-title">${t().minutes(minutes)} <span class="muted">${state.mode === "ref" ? t().toNearest : t().toNearestAny}</span></p>` +
         where + `<p class="muted">${t().olderHere(fmt(p.pop60), fmt(p.pop))}</p>`;
}

map.on("mousemove", "hexes", (e) => {
  const f = e.features[0];
  if (hoveredId !== null) map.setFeatureState({ source: "hexes", id: hoveredId }, { hover: false });
  hoveredId = f.id;
  map.setFeatureState({ source: "hexes", id: hoveredId }, { hover: true });
  map.getCanvas().style.cursor = "pointer";
  hoverPopup.setLngLat(e.lngLat).setHTML(hexHtml(f.properties)).addTo(map);
});

map.on("mouseleave", "hexes", () => {
  if (hoveredId !== null) map.setFeatureState({ source: "hexes", id: hoveredId }, { hover: false });
  hoveredId = null;
  map.getCanvas().style.cursor = "";
  hoverPopup.remove();
});

// Click (and tap on phones): a place if there is one under the finger, otherwise the hexagon
map.on("click", (e) => {
  if (!map.getLayer("hexes")) return;
  const place = map.queryRenderedFeatures(e.point, { layers: ["refugios", "alivio"] })[0];
  if (place) {
    const p = place.properties;
    new maplibregl.Popup({ offset: 8 }).setLngLat(place.geometry.coordinates)
      .setHTML(`<p class="pop-title">${escapeHtml(p.n)}</p><p class="muted">${t().types[p.t] || p.t}</p>`).addTo(map);
    return;
  }
  const hex = map.queryRenderedFeatures(e.point, { layers: ["hexes"] })[0];
  if (hex) new maplibregl.Popup({ offset: 8 }).setLngLat(e.lngLat).setHTML(hexHtml(hex.properties)).addTo(map);
});

// ---------------------------------------------------------------- 5. Panel controls

// "Refuges only" / "Refuges + relief stores"
document.querySelectorAll('input[name="mode"]').forEach((input) =>
  input.addEventListener("change", () => {
    state.mode = input.value;
    applyFilters();
  }));

// "Only where older adults live"
document.getElementById("highlight60").addEventListener("change", applyFilters);

function applyFilters() {
  // The stacked bar that matches the current mode
  document.querySelectorAll("#city-panel .bands").forEach((fig) => (fig.hidden = fig.dataset.mode !== state.mode));
  if (!map.getLayer("hexes")) return;
  map.setPaintProperty("hexes", "fill-color", colorBy(state.mode));
  map.setLayoutProperty("alivio", "visibility", state.mode === "any" ? "visible" : "none");
  const only60 = document.getElementById("highlight60").checked;
  const filter = only60 ? [">=", ["get", "pop60"], MIN_POP60_HIGHLIGHT] : null;
  map.setFilter("hexes", filter);
  map.setFilter("hex-hover", filter);
}

// Zones and proposals in the panel: fly the map there
document.getElementById("city-panel").addEventListener("click", (e) => {
  const button = e.target.closest("button[data-lon]");
  if (!button) return;
  const center = [Number(button.dataset.lon), Number(button.dataset.lat)];
  map.flyTo({ center, zoom: Number(button.dataset.zoom) || 14.5, essential: true });
  const rank = Number(button.dataset.rank);
  if (rank) {
    proposalMarkers.forEach((m) => m.getPopup().isOpen() && m.togglePopup());
    map.once("moveend", () => proposalMarkers[rank - 1]?.togglePopup());
  }
  if (isPhone()) setSheet(false); // show the map on phones
});

// City selector (only shown when there is more than one city)
fetch("data/cities.json").then((r) => r.json()).then((cities) => {
  if (cities.length < 2) return;
  const select = document.getElementById("city-select");
  select.innerHTML = cities.map((c) => `<option value="${c.id}">${escapeHtml(c.city)}, ${escapeHtml(c.state)}</option>`).join("");
  select.value = state.city;
  document.getElementById("city-select-wrap").hidden = false;
  select.addEventListener("change", () => switchCity(select.value));
}).catch(() => {});

async function switchCity(city) {
  state.city = city;
  updateUrl({ city: city === "culiacan" ? null : city });
  const html = await fetch(`data/${city}/panel.html`).then((r) => r.text());
  document.getElementById("city-panel").innerHTML = html; // text made by render_html.py
  cityData = loadCity(city);
  for (const id of ["hex-hover", "hexes", "refugios", "alivio"]) if (map.getLayer(id)) map.removeLayer(id);
  for (const id of ["hexes", "refuges"]) if (map.getSource(id)) map.removeSource(id);
  await addDataLayers();
}

// Language button
document.getElementById("lang-toggle").addEventListener("click", () => setLanguage(state.lang === "es" ? "en" : "es"));

// "How it works" dialog
document.getElementById("about-open").addEventListener("click", () => document.getElementById("about").showModal());

// Phones: the panel is a bottom sheet that can be hidden to see the whole map
function setSheet(open) {
  document.getElementById("panel").classList.toggle("collapsed", !open);
  document.getElementById("sheet-handle").setAttribute("aria-expanded", String(open));
  if (open) fitPadding();
  else map.setPadding({ top: 0, right: 0, left: 0, bottom: 44 }); // only the handle is left on screen
}
document.getElementById("sheet-handle").addEventListener("click", () =>
  setSheet(document.getElementById("panel").classList.contains("collapsed")));

// ---------------------------------------------------------------- 6. Helpers

function showNotice(text) {
  const el = document.getElementById("notice");
  el.textContent = text;
  el.hidden = false;
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

setLanguage(state.lang);
