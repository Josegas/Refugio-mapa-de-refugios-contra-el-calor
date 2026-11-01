# Guion del video (meta: 2:50, máximo 3:00)

Narración en español con subtítulos en inglés (`docs/video-subtitles.en.srt`, para subir a YouTube).
~330 palabras: a ritmo tranquilo caben en 2:40 y quedan 10 s de aire.

## Antes de grabar (checklist de las reglas)

- [ ] Ventana de **incógnito**, a pantalla completa, con la **barra de direcciones visible** (la URL en pantalla es requisito).
      Sin barra de marcadores, sin otras pestañas y con las notificaciones del sistema apagadas.
- [ ] App en **inglés**: `https://main.d6r3007drgrwp.amplifyapp.com/?lang=en`.
- [ ] Zoom del navegador al 100%, en una pantalla de 1440×900 o más.
- [ ] **No mostrar otras apps**: ni editor de código, ni GitHub, ni herramientas de IA. La consola de AWS sí se permite.
- [ ] **Sin música.** Solo tu voz.
- [ ] **Sin marcas:** la demo usa "Colonia Libertad, Culiacán", cuyo refugio más cercano es el Museo de Ciencias.
      Al terminar la búsqueda, la lista "Cool places nearby" muestra nombres de tiendas: **no te detengas en ella**
      y deja visible solo la parte de arriba del resultado (el museo y los minutos).
- [ ] Ensaya una vez completa con cronómetro. Si pasas de 2:55, recorta el segmento 4.
- [ ] Al subirlo a YouTube: visibilidad **Pública** (no "No listado"), título en inglés y los subtítulos `.srt`.
      Título sugerido: *Refugio: walking time to a cool place for older adults in 45 °C heat (Culiacán, Mexico)*.

## Guion

| Tiempo | En pantalla | Narración (ES) |
|---|---|---|
| **0:00–0:12** Gancho | El mapa de Culiacán completo, quieto. | "Culiacán llega a 45 grados. Si tienes 72 años y no tienes coche, ¿qué tan lejos está, caminando, el lugar fresco más cercano?" |
| **0:12–0:30** Qué muestra | Pasa el mouse sobre varios hexágonos (aparece el tooltip con los minutos). Señala la barra de colores del panel y la cifra 17,441. | "Esto es Refugio. Cada hexágono es más o menos una cuadra, y su color dice cuántos minutos caminas, por las calles reales y a paso lento, hasta un lugar con aire acondicionado donde puedes quedarte sin comprar nada. En Culiacán, 17,441 adultos mayores viven a más de 15 minutos." |
| **0:30–1:05** Búsqueda personal | Escribe `Colonia Libertad, Culiacán` y presiona *Search*. Espera a que se dibujen las áreas y la ruta. Señala con el mouse la ruta naranja y el museo; luego las líneas de 5, 10 y 15 min. | "Busquemos desde una casa en la colonia Libertad. Amazon Location convierte la dirección en un punto y, al mismo tiempo, dibuja hasta dónde llego caminando en 5, 10 y 15 minutos, y la ruta a pie al refugio más cercano: el Museo de Ciencias, a 26 minutos. Mi mapa de datos abiertos da lo mismo: 26. Ni la zona de 15 minutos lo alcanza." |
| **1:05–1:35** Lo que se puede explorar | Presiona *Clear*. Cambia a "Refuges + pharmacies and stores" y regresa. Activa "Only show hexagons where 10 or more older adults live". Baja en el panel: toca la zona "Díaz Ordaz / Libertad" (el mapa vuela) y luego la propuesta 1. | "Si cuentas farmacias y tiendas, donde entras un momento a comprar agua, casi todos quedan cerca. Este filtro deja solo donde viven adultos mayores. La lista de zonas muestra dónde faltan refugios, y estas son diez escuelas públicas que, abiertas como refugio, subirían a los adultos mayores a 10 minutos o menos del 40.7 al 51.4 por ciento." |
| **1:35–1:45** Otras ciudades | Selector *City*: Hermosillo, luego Mexicali. | "Y el mismo pipeline corre en Hermosillo y en Mexicali." |
| **1:45–2:20** Cómo funciona | Abre `.../about.html` en la misma pestaña y baja al diagrama de arquitectura. Recorre con el mouse los pasos 1 a 7. | "¿Cómo funciona? Los datos vienen del Registry of Open Data on AWS, en Amazon S3: lugares y calles de Overture Maps, y la población de 60 años o más de Meta. Solo leo el área de cada ciudad: Culiacán baja en 34 segundos. Con 57 mil tramos de calle armo una red peatonal y calculo los minutos de cada hexágono. El sitio es estático, en AWS Amplify, y la búsqueda personal llama a Amazon Location: mapa, lugares y rutas." |
| **2:20–2:45** Evidencia | Baja a "Evidence": la tabla y la gráfica de puntos sobre la diagonal. | "¿Es confiable? Comparé 50 puntos al azar contra las rutas de Amazon Location: la diferencia mediana es de medio minuto, y el 94 por ciento queda a menos de 2 minutos. Donde Overture no tiene un lugar, Amazon Location a veces sí; por eso la cifra principal es un máximo." |
| **2:45–2:55** Cierre | Regresa al mapa. Deja la barra de direcciones a la vista unos segundos. | "Lo que sigue es una red oficial de refugios con el municipio. Pruébalo en esta dirección." |

## Si te sobra o te falta tiempo

- **Te pasas:** quita la frase del filtro de adultos mayores (1:05) y la de "Culiacán baja en 34 segundos" (1:45).
- **Te sobra:** en 1:35, presiona el botón **ES/EN** para mostrar que la app está en dos idiomas.
- Si una llamada a Amazon Location falla en vivo, la app pasa a modo demo y dibuja una línea recta. Vuelve a
  grabar ese segmento; no lo expliques en el video.

## Después de grabar

- Revisa que no se vea ningún logo y que la lista de tiendas no quede legible más de un segundo.
- Ajusta los tiempos del `.srt` a tu grabación real: en YouTube Studio, *Subtítulos → Subir archivo → Con tiempos*,
  y luego mueve los bloques si hace falta.
- Pega el link del video en `docs/writeup.md` (busca `TODO(José)`), en el README y en el formulario de la entrega.
