/* Refugio guided tour: six stops that explain the map in about a minute.
 *
 * Opens with the "Guided tour" button in the panel, or by itself with ?tour=1 in the URL.
 * It only drives what app.js already does (fly the map, switch the layer, run one search);
 * it adds no data and no new Amazon Location calls besides that one search (6 billable requests).
 * Every number comes from the city's stats.json (state.stats), so it always matches the panel.
 */

const TOUR_TEXT = {
  es: {
    start: "Recorrido guiado (1 min)",
    prev: "Anterior", next: "Siguiente", done: "Terminar", close: "Salir del recorrido",
    of: (i, n) => `${i} de ${n}`,
    steps: [
      { title: "El problema", body: (s) =>
        `En Culiacán, <strong>${fmt(s.far)} adultos mayores</strong> (${s.pctFar}) viven a más de 15 minutos a pie de un lugar ` +
        `con aire acondicionado donde pueden quedarse sin comprar nada. Cada hexágono es una manzana: entre más oscuro, más lejos.` },
      { title: "El hueco más grande", body: (s) =>
        `<strong>${s.zone.name}</strong>: ${fmt(s.zone.pop60)} adultos mayores viven aquí, a una mediana de ` +
        `${s.zone.median_min} min a pie del refugio más cercano. Es la zona con más adultos mayores lejos de un refugio.` },
      { title: "Desde una casa", body: () =>
        `Amazon Location calcula en vivo hasta dónde llegas en 5, 10 y 15 min y la ruta a pie al refugio que dice el mapa. ` +
        `Si conoce un lugar tipo refugio más cerca que nuestros datos abiertos, la app lo avisa: así ves dónde fallan los datos. ` +
        (isPhone() ? `Abre el panel de abajo para ver el resultado.` : `El resultado aparece en el panel.`) + (usingDemo ? " <em>Ahora está en modo demo: verás una línea recta, no una ruta.</em>" : "") },
      { title: "Una parada rápida también ayuda", body: (s) =>
        `Si cuentan las farmacias y tiendas de conveniencia, donde entras un momento a comprar agua, solo ` +
        `<strong>${fmt(s.farAny)}</strong> (${s.pctFarAny}) quedan a más de 15 min. Pero ahí no te puedes quedar toda la tarde.` },
      { title: "Dónde abrir refugios", body: (s) =>
        `Hoy, ${Math.round(s.before / 10)} de cada 10 adultos mayores (${s.before}%) tienen un lugar fresco a 10 min o menos ` +
        `caminando. Los 10 círculos dorados son escuelas públicas: abiertas como refugio en vacaciones de verano y fines de ` +
        `semana, cuando no hay clases, serían <strong>${Math.round(s.after / 10)} de cada 10 (${s.after}%)</strong>: ` +
        `${fmt(s.gain)} personas más que llegan caminando a un lugar fresco en 10 min o menos.` },
      { title: "Ahora tú", body: () =>
        `Escribe una dirección, toca cualquier hexágono o cambia a Hermosillo o Mexicali en el selector de ciudad: ` +
        `el mismo método corre en las tres ciudades.` },
    ],
  },
  en: {
    start: "Guided tour (1 min)",
    prev: "Back", next: "Next", done: "Finish", close: "Leave the tour",
    of: (i, n) => `${i} of ${n}`,
    steps: [
      { title: "The problem", body: (s) =>
        `In Culiacán, <strong>${fmt(s.far)} older adults</strong> (${s.pctFar}) live more than a 15-minute walk from an ` +
        `air-conditioned place where they can stay without buying anything. Each hexagon is about a block: the darker, the farther.` },
      { title: "The biggest gap", body: (s) =>
        `<strong>${s.zone.name}</strong>: ${fmt(s.zone.pop60)} older adults live here, a median ${s.zone.median_min}-minute ` +
        `walk from the nearest refuge. No other area has more older adults far from a refuge.` },
      { title: "From one home", body: () =>
        `Amazon Location works out, live, how far you get in 5, 10 and 15 minutes and the walking route to the refuge the map ` +
        `points to. If it knows a refuge-type place closer than our open data, the app says so: you see where the data falls short. ` +
        (isPhone() ? `Open the panel below to see the result.` : `The result shows in the panel.`) + (usingDemo ? " <em>Demo mode is on: you'll see a straight line, not a route.</em>" : "") },
      { title: "A quick stop helps too", body: (s) =>
        `Counting pharmacies and convenience stores, where you step in to buy water, only <strong>${fmt(s.farAny)}</strong> ` +
        `(${s.pctFarAny}) are more than 15 minutes away. But you can't stay there all afternoon.` },
      { title: "Where to open refuges", body: (s) =>
        `Today, ${Math.round(s.before / 10)} in 10 older adults (${s.before}%) have a cool place within a 10-minute walk. ` +
        `The 10 gold circles are public schools: opened as refuges during summer break and on weekends, when there are no ` +
        `classes, it would be <strong>${Math.round(s.after / 10)} in 10 (${s.after}%)</strong>: ${fmt(s.gain)} more people ` +
        `who can walk to a cool place in 10 minutes or less.` },
      { title: "Your turn", body: () =>
        `Type an address, tap any hexagon, or switch to Hermosillo or Mexicali in the city selector: ` +
        `the same method runs in all three cities.` },
    ],
  },
};
const tt = () => TOUR_TEXT[state.lang];

// What each stop does on the map. Each one sets everything it needs, so "Back" works too.
const TOUR_ACTIONS = [
  async (s) => { resetTourSearch(); setTourMode("ref"); map.flyTo({ center: s.center, zoom: s.zoom, essential: true }); },
  async (s) => { resetTourSearch(); setTourMode("ref"); map.flyTo({ center: [s.zone.lon, s.zone.lat], zoom: 14, essential: true }); },
  async (s) => {
    setTourMode("ref");
    await searchFrom([s.zone.lon, s.zone.lat], s.zone.name.split(" / ")[0]);
    if (!isPhone()) document.getElementById("search-result").scrollIntoView({ block: "start", behavior: "smooth" });
  },
  async (s) => { resetTourSearch(); setTourMode("any"); map.flyTo({ center: s.center, zoom: s.zoom, essential: true }); },
  async (s) => {
    resetTourSearch(); setTourMode("ref");
    const points = (await cityData).proposals.features.map((f) => f.geometry.coordinates);
    fitTo(points);
  },
  async (s) => { resetTourSearch(); setTourMode("ref"); map.flyTo({ center: s.center, zoom: s.zoom, essential: true }); },
];

let tourStep = -1;  // -1 = tour closed
let tourBusy = false;

// The numbers the texts need, from the current city's stats.json
function tourNumbers() {
  const s = state.stats;
  const pct = (a, b) => `${(100 * a / b).toFixed(1)}%`;
  return {
    center: s.center, zoom: s.zoom, zone: s.zones[0],
    far: s.access_refugio.gt15.pop60, farAny: s.access_any.gt15.pop60,
    pctFar: pct(s.access_refugio.gt15.pop60, s.population.pop60),
    pctFarAny: pct(s.access_any.gt15.pop60, s.population.pop60),
    before: s.proposals.pct60_le10_before, after: s.proposals.pct60_le10_after, gain: s.proposals.new_pop60,
  };
}

function setTourMode(mode) {
  document.querySelector(`input[name="mode"][value="${mode}"]`).checked = true;
  state.mode = mode;
  applyFilters();
}

function resetTourSearch() {
  clearSearch();
  if (originMarker) originMarker.remove();
  document.getElementById("search-result").hidden = true;
  document.querySelectorAll(".maplibregl-popup").forEach((p) => p.remove());
}

// While the card is open, the map centers on the part of the screen the card and the panel leave free
function tourPadding() {
  const card = document.getElementById("tour").offsetHeight;
  return isPhone() ? { top: card + 20, right: 0, left: 0, bottom: 44 }
                   : { top: 0, right: 0, left: document.getElementById("panel").offsetWidth + 24, bottom: card + 50 };
}

// Waits until the hexagons of the current city are on the map
function mapReady() {
  return new Promise((resolve) => {
    const check = () => (map.getLayer("hexes") && state.stats ? resolve() : setTimeout(check, 200));
    check();
  });
}

async function startTour() {
  await mapReady();
  if (state.city !== "culiacan") { // the texts talk about Culiacán
    document.getElementById("city-select").value = "culiacan";
    await switchCity("culiacan");
    await mapReady();
  }
  document.body.classList.add("touring");
  if (isPhone()) setSheet(false); // the map needs the screen
  goToStep(0);
}

function closeTour() {
  tourStep = -1;
  document.getElementById("tour").hidden = true;
  document.body.classList.remove("touring");
  updateUrl({ tour: null });
  if (isPhone()) map.setPadding({ top: 0, right: 0, left: 0, bottom: 44 }); // panel still folded
  else fitPadding();
}

async function goToStep(i) {
  if (tourBusy) return;
  tourStep = i;
  tourBusy = true; // "Next" waits until the map has done this stop
  renderTour();
  map.setPadding(tourPadding());
  try {
    await TOUR_ACTIONS[i](tourNumbers());
  } catch (err) {
    console.error("Tour step failed:", err); // the card still works; the map just didn't change
  }
  tourBusy = false;
  renderTour();
}

function renderTour() {
  const box = document.getElementById("tour");
  if (tourStep < 0) return;
  const step = tt().steps[tourStep];
  const n = tt().steps.length;
  const last = tourStep === n - 1;
  box.innerHTML =
    `<div class="tour-head"><span class="tour-count">${tt().of(tourStep + 1, n)}</span>` +
    `<button type="button" class="tour-close" aria-label="${tt().close}" title="${tt().close}">×</button></div>` +
    `<h2 class="tour-title">${step.title}</h2>` +
    `<p class="tour-body">${step.body(tourNumbers())}</p>` +
    `<div class="tour-dots" aria-hidden="true">${tt().steps.map((_, k) => `<i class="${k === tourStep ? "on" : ""}"></i>`).join("")}</div>` +
    `<div class="tour-nav">` +
    `<button type="button" class="tour-prev" ${tourStep === 0 ? "disabled" : ""}>${tt().prev}</button>` +
    `<button type="button" class="tour-next" ${tourBusy ? "disabled" : ""}>${last ? tt().done : tt().next}</button></div>`;
  box.hidden = false;
}

// Buttons inside the card
document.getElementById("tour").addEventListener("click", (e) => {
  if (e.target.closest(".tour-close")) return closeTour();
  if (e.target.closest(".tour-prev") && tourStep > 0) return goToStep(tourStep - 1);
  if (e.target.closest(".tour-next")) {
    if (tourStep === tt().steps.length - 1) {
      closeTour();
      if (isPhone()) setSheet(true);
      document.getElementById("address").focus();
    } else goToStep(tourStep + 1);
  }
});

// Keyboard: arrows move, Escape leaves (only while the tour is open)
document.addEventListener("keydown", (e) => {
  if (tourStep < 0 || e.target.matches("input, select, textarea")) return;
  if (e.key === "Escape") closeTour();
  if (e.key === "ArrowRight" && tourStep < tt().steps.length - 1) goToStep(tourStep + 1);
  if (e.key === "ArrowLeft" && tourStep > 0) goToStep(tourStep - 1);
});

// The language button also re-writes the card
document.getElementById("lang-toggle").addEventListener("click", () => setTimeout(renderTour, 0));

// The button in the panel, and ?tour=1
document.getElementById("tour-start").addEventListener("click", startTour);
if (params.get("tour") === "1") startTour();
