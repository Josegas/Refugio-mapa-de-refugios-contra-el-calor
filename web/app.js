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
const HEX_OPACITY = 0.75;  // hexagon fill; lower = more of the streets and names show through

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
    searchHere: "Calcular mi caminata desde aquí",
    from: "Desde",
    nearestRefuge: "Refugio más cercano",
    onFootRoute: (min, km) => `${min} min a pie · ruta de Amazon Location (${km} km)`,
    openDataEstimate: (min) => `${min} según el mapa de datos abiertos`,
    closerByAmazon: (name, cat, m) => `Amazon Location conoce un lugar tipo refugio más cerca: <strong>${name}</strong> (${cat}, a ${m} m en línea recta). No está en los datos abiertos del mapa, así que desde aquí el tiempo real puede ser menor. Pasa en cerca de 1 de cada 10 hexágonos.`,
    straightLine: "Línea recta (modo demo): la ruta real por las calles no se pudo calcular.",
    isolinesNote: "Áreas punteadas: todo lo que queda dentro lo alcanzas caminando en 5, 10 o 15 min. Si un lugar fresco cae dentro, es una opción para ti (Amazon Location, velocidad peatonal estándar).",
    nearbyTitle: "Lugares frescos cerca según Amazon Location",
    nearbyNone: "Amazon Location no encontró lugares de estas categorías a menos de 1.5 km.",
    meters: (m) => (m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m)} m`),
    noRefuge: "No hay un refugio a menos de 60 min a pie de este punto.",
    outside: "Ese punto está fuera del área de estudio (la mancha urbana de la ciudad).",
    notFound: "No encontramos esa dirección. Prueba con calle y colonia.",
    searching: "Calculando…",
    tooMany: "Llegaste al límite de búsquedas de esta visita (cuidamos el uso gratuito). Recarga la página para seguir.",
    apiFailed: "Amazon Location no respondió; se muestran solo los datos abiertos.",
    locating: "Pidiendo tu ubicación…",
    noLocation: "No se pudo obtener tu ubicación.",
    clear: "Limpiar",
    placeholder: (city) => `Calle y colonia, ${city}`,
    zoneDir: (dir, km) => `Zona ${{ N: "norte", NE: "noreste", E: "este", SE: "sureste", S: "sur", SW: "suroeste", W: "oeste", NW: "noroeste" }[dir]} (${km} km)`,
    nearbyCats: { shopping_mall: "Plaza", department_store: "Departamental", grocery: "Súper", library: "Biblioteca",
                  museum: "Museo", "civic-community_center": "Centro comunitario", pharmacy: "Farmacia",
                  drugstore: "Farmacia", drugstore_or_pharmacy: "Farmacia", convenience_store: "Conveniencia" },
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
    searchHere: "Calculate my walk from here",
    from: "From",
    nearestRefuge: "Nearest refuge",
    onFootRoute: (min, km) => `${min} min on foot · Amazon Location route (${km} km)`,
    openDataEstimate: (min) => `${min} according to the open-data map`,
    closerByAmazon: (name, cat, m) => `Amazon Location knows a refuge-type place closer: <strong>${name}</strong> (${cat}, ${m} m in a straight line). It is not in the open data behind the map, so from here the real walk may be shorter. This happens in about 1 in 10 hexagons.`,
    straightLine: "Straight line (demo mode): the real street route could not be calculated.",
    isolinesNote: "Dotted areas: anything inside them is within a 5, 10 or 15 min walk. If a cool place falls inside, it is an option for you (Amazon Location, standard walking speed).",
    nearbyTitle: "Cool places nearby according to Amazon Location",
    nearbyNone: "Amazon Location found no places of these types within 1.5 km.",
    meters: (m) => (m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m)} m`),
    noRefuge: "There is no refuge within a 60-minute walk of this point.",
    outside: "That point is outside the study area (the city's urban footprint).",
    notFound: "We couldn't find that address. Try street and neighborhood.",
    searching: "Calculating…",
    tooMany: "You reached this visit's search limit (we protect the free usage). Reload the page to continue.",
    apiFailed: "Amazon Location didn't answer; showing open data only.",
    locating: "Asking for your location…",
    noLocation: "Your location could not be obtained.",
    clear: "Clear",
    placeholder: (city) => `Street and neighborhood, ${city}`,
    zoneDir: (dir, km) => `${{ N: "North", NE: "Northeast", E: "East", SE: "Southeast", S: "South", SW: "Southwest", W: "West", NW: "Northwest" }[dir]} area (${km} km)`,
    nearbyCats: { shopping_mall: "Mall", department_store: "Department store", grocery: "Grocery", library: "Library",
                  museum: "Museum", "civic-community_center": "Community center", pharmacy: "Pharmacy",
                  drugstore: "Pharmacy", drugstore_or_pharmacy: "Pharmacy", convenience_store: "Convenience" },
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
  updatePlaceholder();
  if (state.stats) renderExamples(state.stats.zones.slice(0, 3));
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

// The map legend's color boxes come from RAMP, so they always match the hexagons
document.querySelectorAll("#map-legend .sw").forEach((box, i) => (box.style.background = RAMP[i]));

async function addDataLayers() {
  if (map.getSource("hexes")) return; // already added for this style
  const data = await cityData;
  state.refuges = data.refuges.features;
  state.stats = data.stats;
  const hexes = hexagonsToGeoJSON(data.hex);
  // Look-up table: H3 cell -> hexagon data, to answer "what about this exact point?" instantly
  const col = data.hex.fields.indexOf("h");
  state.hexByCell = new Map(data.hex.rows.map((row, i) => [row[col], hexes.features[i].properties]));
  renderExamples(data.stats.zones.slice(0, 3));
  updatePlaceholder();

  // Put the hexagons under the base map's labels, so street names stay readable
  const firstLabel = map.getStyle().layers.find((l) => l.type === "symbol")?.id;

  map.addSource("hexes", { type: "geojson", data: hexes });
  map.addLayer({ id: "hexes", type: "fill", source: "hexes",
                 // No edge: neighbors of the same band merge into one area. Antialiasing off, or the soft edges of two
                 // see-through cells overlap and draw a darker seam. The hexagons are still the unit of analysis.
                 paint: { "fill-color": colorBy(state.mode), "fill-opacity": HEX_OPACITY, "fill-antialias": false } },
               firstLabel);
  map.addLayer({ id: "hex-hover", type: "line", source: "hexes",
                 paint: { "line-color": "#0b0b0b", "line-width": 2,
                          "line-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 1, 0] } },
               firstLabel);
  map.addLayer({ id: "hex-selected", type: "line", source: "hexes",
                 paint: { "line-color": "#0b0b0b", "line-width": 3,
                          "line-opacity": ["case", ["boolean", ["feature-state", "selected"], false], 1, 0] } },
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

function hexHtml(p, lngLat = null) {
  const minutes = state.mode === "ref" ? p.ref : p.any;
  const idx = state.mode === "ref" ? p.iref : p.iany;
  const place = idx >= 0 ? state.refuges[idx]?.properties : null;
  const where = place ? `<p>${escapeHtml(place.n)} · ${t().types[place.t] || place.t}</p>` : "";
  const button = lngLat ? `<button type="button" class="search-here" data-lon="${lngLat.lng}" data-lat="${lngLat.lat}">${t().searchHere}</button>` : "";
  return `<p class="pop-title">${t().minutes(minutes)} <span class="muted">${state.mode === "ref" ? t().toNearest : t().toNearestAny}</span></p>` +
         where + `<p class="muted">${t().olderHere(fmt(p.pop60), fmt(p.pop))}</p>` + button;
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

// The tapped hexagon gets a dark outline until its popup closes or another one is tapped
let selectedId = null;
let selectToken = 0; // tells an old popup's "close" apart from the newest selection
function selectHex(id) {
  if (!map.getSource("hexes")) return;
  if (selectedId !== null) map.setFeatureState({ source: "hexes", id: selectedId }, { selected: false });
  selectedId = id;
  if (id !== null) map.setFeatureState({ source: "hexes", id }, { selected: true });
  return ++selectToken;
}

// Click (and tap on phones): a place if there is one under the finger, otherwise the hexagon
map.on("click", (e) => {
  if (!map.getLayer("hexes")) return;
  const place = map.queryRenderedFeatures(e.point, { layers: ["refugios", "alivio"] })[0];
  if (place) {
    selectHex(null);
    const p = place.properties;
    new maplibregl.Popup({ offset: 8 }).setLngLat(place.geometry.coordinates)
      .setHTML(`<p class="pop-title">${escapeHtml(p.n)}</p><p class="muted">${t().types[p.t] || p.t}</p>`).addTo(map);
    return;
  }
  const hex = map.queryRenderedFeatures(e.point, { layers: ["hexes"] })[0];
  if (hex) {
    hoverPopup.remove();
    const token = selectHex(hex.id);
    new maplibregl.Popup({ offset: 8 }).setLngLat(e.lngLat).setHTML(hexHtml(hex.properties, e.lngLat)).addTo(map)
      .on("close", () => { if (token === selectToken) selectHex(null); });
  }
});

// The "Calculate my walk from here" button inside a hexagon's popup
document.getElementById("map").addEventListener("click", (e) => {
  const b = e.target.closest(".search-here");
  if (!b) return;
  document.querySelectorAll(".maplibregl-popup").forEach((p) => p.remove());
  searchFrom([Number(b.dataset.lon), Number(b.dataset.lat)], null);
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
  map.setFilter("hex-selected", filter);
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

// The panel text of a city (written by render_html.py). index.html already contains Culiacán's.
async function loadPanel(city) {
  const html = await fetch(`data/${city}/panel.html`).then((r) => r.text());
  document.getElementById("city-panel").innerHTML = html;
  applyFilters(); // show the stacked bar that matches the current mode
}
if (state.city !== "culiacan") loadPanel(state.city); // opened with a ?city= link

async function switchCity(city) {
  state.city = city;
  updateUrl({ city: city === "culiacan" ? null : city });
  await loadPanel(city);
  cityData = loadCity(city);
  clearSearch();
  if (originMarker) originMarker.remove();
  document.getElementById("search-result").hidden = true;
  // Every layer that reads the "hexes" or "refuges" source must go before the source itself
  selectedId = null;
  for (const id of ["hex-selected", "hex-hover", "hexes", "refugios", "alivio"]) if (map.getLayer(id)) map.removeLayer(id);
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

// ---------------------------------------------------------------- 6. Personal search (Amazon Location, live)
//
// "Open data finds the gaps; Amazon Location guides the person."
// From one origin, three calls run at the same time:
//   CalculateIsolines -> the area reachable on foot in 5, 10 and 15 minutes
//   CalculateRoutes   -> the walking route to the nearest refuge in OUR data (the hexagon's "iref")
//   SearchNearby      -> cool places Amazon Location knows within 1.5 km
// Results are drawn and then forgotten: nothing is stored (IntendedUse "SingleUse").

const PLACES_API = `https://places.geo.${REGION}.amazonaws.com/v2`;
const ROUTES_API = `https://routes.geo.${REGION}.amazonaws.com/v2`;
const NEARBY_CATEGORIES = ["shopping_mall", "department_store", "grocery", "library", "museum",
  "civic-community_center", "drugstore_or_pharmacy", "pharmacy", "drugstore", "convenience_store"];
// Amazon Location categories that match our "refuge" (stay without buying). Groceries, pharmacies and
// convenience stores are not refuges, so they never trigger the "closer place" note.
const REFUGE_LIKE = ["shopping_mall", "department_store", "library", "museum", "civic-community_center"];
const CLOSER_BY_M = 150; // same threshold as the validation in docs/validation.md

// Straight-line distance in meters between two [lon, lat] points
function metersBetween([lon1, lat1], [lon2, lat2]) {
  const rad = Math.PI / 180, R = 6371000;
  const a = Math.sin((lat2 - lat1) * rad / 2) ** 2 +
            Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin((lon2 - lon1) * rad / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

const MAX_SEARCHES = 30; // per page visit: a guard against accidental loops eating the free tier
const DEBUG = params.has("debug"); // ?debug=1 shows how long each call took
let searchCount = 0;
let originMarker = null;
let timings = [];

// One Amazon Location call, timed. The API key goes in the URL, as the service expects.
async function locationApi(base, path, body, label) {
  const start = performance.now();
  const response = await fetch(`${base}/${path}?key=${encodeURIComponent(API_KEY)}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  timings.push({ call: label, ms: Math.round(performance.now() - start), status: response.status });
  if (!response.ok) throw new Error(`${label}: HTTP ${response.status}`);
  return response.json();
}

const canUseApi = () => API_KEY && !usingDemo;

async function geocode(text) {
  const data = await locationApi(PLACES_API, "geocode", {
    QueryText: text, BiasPosition: state.stats.center, Filter: { IncludeCountries: ["MEX"] },
    Language: state.lang, MaxResults: 1,
  }, "Geocode");
  const item = data.ResultItems?.[0];
  return item ? { position: item.Position, label: item.Address?.Label || item.Title } : null; // Position = [lon, lat]
}

// The main flow: from one point, show the walk to the nearest refuge
async function searchFrom(lngLat, label, { afterGeocode = false } = {}) {
  if (!state.hexByCell) return;
  const [lon, lat] = lngLat;
  const geocodeTiming = afterGeocode ? timings : []; // keep the Geocode time for ?debug=1
  clearSearch();
  timings = geocodeTiming;
  if (originMarker) originMarker.remove();
  originMarker = new maplibregl.Marker({ color: "#0b0b0b" }).setLngLat(lngLat).addTo(map);

  // 1) Our open-data answer, instantly: which hexagon is this, and which refuge is nearest?
  const hex = state.hexByCell.get(h3.latLngToCell(lat, lon, 10));
  if (!hex) return showResult(`<p>${t().outside}</p>`);
  const refuge = hex.iref >= 0 ? state.refuges[hex.iref] : null;
  if (!refuge) return showResult(`<p>${t().noRefuge}</p>`);
  const destination = refuge.geometry.coordinates;

  if (!canUseApi() || searchCount >= MAX_SEARCHES) {
    drawRoute([lngLat, destination], true);
    fitTo([lngLat, destination]);
    return showResult(resultHtml({ label, refuge, hex, route: null, nearby: null,
                                   note: searchCount >= MAX_SEARCHES ? t().tooMany : t().straightLine }));
  }

  // 2) Amazon Location, three calls in parallel
  searchCount++;
  showResult(`<p class="muted">${t().searching}</p>`);
  const [iso, route, nearby] = await Promise.allSettled([
    locationApi(ROUTES_API, "isolines", { Origin: lngLat, Thresholds: { Time: [300, 600, 900] },
      TravelMode: "Pedestrian", IsolineGeometryFormat: "Simple" }, "CalculateIsolines"),
    locationApi(ROUTES_API, "routes", { Origin: lngLat, Destination: destination, TravelMode: "Pedestrian",
      TravelModeOptions: { Pedestrian: { Speed: 3.6 } }, LegGeometryFormat: "Simple" }, "CalculateRoutes"),
    locationApi(PLACES_API, "search-nearby", { QueryPosition: lngLat, QueryRadius: 1500, MaxResults: 20,
      Filter: { IncludeCategories: NEARBY_CATEGORIES }, Language: state.lang }, "SearchNearby"),
  ]);

  const points = [lngLat, destination];
  if (iso.status === "fulfilled") points.push(...drawIsolines(iso.value));
  let routeInfo = null;
  if (route.status === "fulfilled") {
    const legs = route.value.Routes?.[0]?.Legs || [];
    const line = legs.flatMap((leg) => leg.Geometry?.LineString || []);
    const sum = (key) => legs.reduce((s, leg) => s + (leg.PedestrianLegDetails?.Summary?.Overview?.[key] || 0), 0);
    drawRoute(line.length ? line : [lngLat, destination], !line.length);
    routeInfo = { seconds: sum("Duration"), meters: sum("Distance") };
  } else {
    drawRoute([lngLat, destination], true);
  }
  const places = nearby.status === "fulfilled" ? (nearby.value.ResultItems || []) : null;
  if (places) drawNearby(places);
  const failed = [iso, route, nearby].some((r) => r.status === "rejected");
  fitTo(points);
  showResult(resultHtml({ label, refuge, hex, route: routeInfo, nearby: places, note: failed ? t().apiFailed : "", origin: lngLat }));
  if (DEBUG) console.table(timings);
}

function resultHtml({ label, refuge, hex, route, nearby, note, origin = null }) {
  const p = refuge.properties;
  const lines = [];
  if (label) lines.push(`<p class="pop-kicker">${t().from}: ${escapeHtml(label)}</p>`);
  lines.push(`<p class="muted small">${t().nearestRefuge}</p><p class="result-main">${escapeHtml(p.n)} <span class="muted">· ${t().types[p.t] || p.t}</span></p>`);
  if (route) lines.push(`<p><strong>${t().onFootRoute(Math.round(route.seconds / 60), (route.meters / 1000).toFixed(1))}</strong></p>`);
  lines.push(`<p class="muted">${t().openDataEstimate(t().minutes(hex.ref))}</p>`);
  // Honest about the gaps in the open data: say so when Amazon Location knows a closer refuge-type place
  if (nearby && origin) {
    const ours = metersBetween(origin, refuge.geometry.coordinates);
    const closer = nearby.find((it) => REFUGE_LIKE.includes(it.Categories?.[0]?.Id) && it.Distance < ours - CLOSER_BY_M);
    if (closer) {
      const cat = closer.Categories[0].Id;
      lines.push(`<p class="note">${t().closerByAmazon(escapeHtml(closer.Title), t().nearbyCats[cat] || cat, Math.round(closer.Distance))}</p>`);
    }
  }
  if (note) lines.push(`<p class="note">${note}</p>`);
  if (route) lines.push(`<p class="small">${t().isolinesNote}</p>`);
  if (nearby) {
    const items = nearby.slice(0, 5).map((it) => {
      const cat = it.Categories?.[0]?.Id;
      return `<li>${escapeHtml(it.Title)} <span class="muted">· ${t().nearbyCats[cat] || cat || ""} · ${t().meters(it.Distance)}</span></li>`;
    }).join("");
    lines.push(`<h3>${t().nearbyTitle}</h3>` + (items ? `<ul class="nearby">${items}</ul>` : `<p class="muted">${t().nearbyNone}</p>`));
  }
  if (DEBUG && timings.length) {
    lines.push(`<p class="small muted">${timings.map((x) => `${x.call} ${x.ms} ms (${x.status})`).join(" · ")}</p>`);
  }
  lines.push(`<button type="button" id="search-clear" class="link-button">${t().clear}</button>`);
  return lines.join("");
}

// ---- drawing helpers (each search replaces the previous drawing)

function setGeoJSON(id, features, addLayers) {
  const data = { type: "FeatureCollection", features };
  if (map.getSource(id)) map.getSource(id).setData(data);
  else { map.addSource(id, { type: "geojson", data }); addLayers(); }
}

function drawIsolines(response) {
  const features = (response.Isolines || []).map((iso) => ({
    type: "Feature", properties: { minutes: Math.round((iso.TimeThreshold || 0) / 60) },
    geometry: { type: "MultiPolygon", coordinates: (iso.Geometries || []).map((g) => g.Polygon) },
  }));
  setGeoJSON("isolines", features, () => {
    // Below the refuge dots and the route, whichever answer arrives first
    const below = map.getLayer("refugios") ? "alivio" : undefined;
    // A white wash per area: the three overlap, so the 5-min area (inside all three) is the brightest
    for (const minutes of [15, 10, 5]) {
      map.addLayer({ id: `isoline-fill-${minutes}`, type: "fill", source: "isolines",
                     filter: ["==", ["get", "minutes"], minutes], paint: { "fill-color": "#ffffff", "fill-opacity": 0.2 } }, below);
    }
    // One line style per threshold: 5 min solid, 10 min dashed, 15 min dotted (same as the map legend)
    const styles = { 5: { width: 2.5, dash: null }, 10: { width: 2, dash: [3, 2] }, 15: { width: 1.6, dash: [1, 2] } };
    for (const [minutes, s] of Object.entries(styles)) {
      const paint = { "line-color": "#0b0b0b", "line-width": s.width };
      if (s.dash) paint["line-dasharray"] = s.dash;
      map.addLayer({ id: `isoline-${minutes}`, type: "line", source: "isolines",
                     filter: ["==", ["get", "minutes"], Number(minutes)], paint }, below);
    }
  });
  document.body.classList.add("has-walk"); // shows the walking-area rows of the map legend
  map.setPaintProperty("hexes", "fill-opacity", 0.45); // dim the grid so the walk stands out
  return features.flatMap((f) => f.geometry.coordinates.flat(2)).filter((_, i) => i % 10 === 0);
}

function drawRoute(line, straight) {
  const feature = { type: "Feature", properties: { straight }, geometry: { type: "LineString", coordinates: line } };
  setGeoJSON("route", [feature], () => {
    map.addLayer({ id: "route-casing", type: "line", source: "route", layout: { "line-cap": "round", "line-join": "round" },
                   paint: { "line-color": "#ffffff", "line-width": 7 } });
    map.addLayer({ id: "route", type: "line", source: "route", layout: { "line-cap": "round", "line-join": "round" },
                   paint: { "line-color": "#eb6834", "line-width": 4 } });
  });
  // A straight line (demo mode) is dashed so nobody mistakes it for a real street route
  map.setPaintProperty("route", "line-dasharray", straight ? [2, 2] : null);
  document.body.classList.add("has-route");
  document.body.classList.toggle("straight-route", straight); // the legend then says "straight line", not "route"
}

function drawNearby(items) {
  const features = items.map((it) => ({ type: "Feature", properties: { title: it.Title, cat: it.Categories?.[0]?.Id || "" },
                                        geometry: { type: "Point", coordinates: it.Position } }));
  setGeoJSON("nearby", features, () => {
    map.addLayer({ id: "nearby", type: "circle", source: "nearby",
      paint: { "circle-radius": 5, "circle-color": "#1baf7a", "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.5 } });
    map.on("click", "nearby", (e) => {
      const p = e.features[0].properties;
      new maplibregl.Popup({ offset: 8 }).setLngLat(e.lngLat)
        .setHTML(`<p class="pop-kicker">Amazon Location</p><p class="pop-title">${escapeHtml(p.title)}</p><p class="muted">${t().nearbyCats[p.cat] || p.cat}</p>`).addTo(map);
    });
  });
}

function fitTo(points) {
  const bounds = points.reduce((b, p) => b.extend(p), new maplibregl.LngLatBounds(points[0], points[0]));
  map.fitBounds(bounds, { padding: 60, maxZoom: 16, duration: 900 });
}

function clearSearch() {
  timings = [];
  for (const id of ["isolines", "route", "nearby"]) {
    if (map.getSource(id)) map.getSource(id).setData({ type: "FeatureCollection", features: [] });
  }
  if (map.getLayer("hexes")) map.setPaintProperty("hexes", "fill-opacity", HEX_OPACITY);
  document.body.classList.remove("has-walk", "has-route", "straight-route");
}

function showResult(html) {
  const box = document.getElementById("search-result");
  box.innerHTML = html;
  box.hidden = false;
}

// ---- the three ways to start a search

document.getElementById("search-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = document.getElementById("address").value.trim();
  if (!text) return;
  if (!canUseApi() || searchCount >= MAX_SEARCHES) return showResult(`<p class="note">${canUseApi() ? t().tooMany : t().demo}</p>`);
  showResult(`<p class="muted">${t().searching}</p>`);
  searchCount++;
  timings = []; // a new search: start timing from the Geocode call
  try {
    const found = await geocode(text);
    if (!found) return showResult(`<p>${t().notFound}</p>`);
    await searchFrom(found.position, found.label, { afterGeocode: true });
  } catch (err) {
    console.warn(err);
    showResult(`<p class="note">${t().apiFailed}</p>`);
  }
});

document.getElementById("locate").addEventListener("click", () => {
  if (!navigator.geolocation) return showResult(`<p>${t().noLocation}</p>`);
  showResult(`<p class="muted">${t().locating}</p>`);
  navigator.geolocation.getCurrentPosition( // only when the button is pressed; never stored
    (pos) => searchFrom([pos.coords.longitude, pos.coords.latitude], null),
    () => showResult(`<p>${t().noLocation}</p>`),
    { enableHighAccuracy: true, timeout: 10000 });
});

function renderExamples(zones) {
  document.getElementById("examples").innerHTML = zones.map((z) =>
    `<button type="button" class="chip" data-lon="${z.lon}" data-lat="${z.lat}">${escapeHtml(z.name ? z.name.split(" / ")[0] : t().zoneDir(z.dir, z.km))}</button>`).join("");
}
document.getElementById("examples").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-lon]");
  if (b) searchFrom([Number(b.dataset.lon), Number(b.dataset.lat)], b.textContent);
});
document.getElementById("search-result").addEventListener("click", (e) => {
  if (e.target.id !== "search-clear") return;
  clearSearch();
  if (originMarker) originMarker.remove();
  document.getElementById("search-result").hidden = true;
});

// ---------------------------------------------------------------- 7. Helpers

// The address box hint names the current city, in the current language
function updatePlaceholder() {
  if (state.stats) document.getElementById("address").placeholder = t().placeholder(state.stats.city);
}

function showNotice(text) {
  const el = document.getElementById("notice");
  el.textContent = text;
  el.hidden = false;
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

setLanguage(state.lang);
