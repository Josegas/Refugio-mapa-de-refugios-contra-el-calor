# Diario de desarrollo — Refugio

Formato: fecha y hora (Culiacán) · qué intenté · qué pasó · cómo lo supe · qué decidí.
Este diario se convierte casi sin esfuerzo en la sección "Retos y errores" de la entrega. Agrega una entrada cada vez que algo falle o tomes una decisión.

---

**2026-10-31 13:05 · Elegir el problema**
- Intenté: investigar en noticias recientes problemas de Culiacán que se resuelvan con un mapa: calor, cortes de agua (JAPAC), inundaciones, dengue y transporte.
- Pasó: el calor es el único con (a) impacto alto y medible (Sinaloa en el top 2 nacional de enfermos por calor en 2026), (b) datos abiertos finos disponibles en AWS y (c) poca solución existente. Agua: solo ~328 polígonos de colonias en Overture y los avisos se capturarían a mano. Inundaciones: IMPLAN ya tiene un atlas. Dengue: solo hay datos por municipio. Transporte: no hay datos abiertos de rutas.
- Decidí: Refugio = acceso a pie a lugares frescos + población 60+. Culiacán a fondo; Hermosillo y Mexicali si da tiempo.

**2026-10-31 14:05 · Leer Overture desde S3**
- Intenté: consultar Overture con DuckDB directo en S3.
- Pasó: `HTTP 403 InvalidAccessKeyId`. El entorno tenía credenciales AWS que no servían para ese bucket. Además, la consulta `categories.primary` falló: en el release 2026-10-21.0 el campo ahora es `taxonomy.primary`.
- Cómo lo supe: mensaje de error de DuckDB y `DESCRIBE` del esquema.
- Decidí: crear un secreto S3 anónimo en DuckDB y usar `taxonomy.primary`. Los 28,002 lugares de Culiacán bajan en ~4 s.

**2026-10-31 14:15 · Categorías ruidosas**
- Pasó: Overture etiqueta "BanCoppel" como `shopping_mall`, un centro penitenciario como `government_office` y panteones como `community_and_government`.
- Decidí: reglas de exclusión por nombre (regex `EXCLUDE` en `build.py`) y supermercados identificados por marca, no por categoría.

**2026-10-31 14:29 · Validar la red peatonal**
- Intenté: comparar la distancia por la red contra la línea recta en ~1,200 pares de puntos al azar.
- Pasó: el factor de rodeo tiene mediana 1.25 (p5 1.09, p95 1.77). 39,069 nodos, 57,276 aristas, 99.3% de los nodos en el componente principal.
- Decidí: la red es plausible; se usa tal cual (solo se excluye `motorway`).

**2026-10-31 14:29 · Primera corrida de la optimización**
- Pasó: el algoritmo propuso como nuevos refugios una escuela privada (Instituto Cumbres), una estancia infantil privada y varios templos.
- Cómo lo supe: revisando a mano la lista de los 10 sitios propuestos.
- Decidí: los candidatos deben ser **edificios públicos** (escuelas públicas, delegaciones y sindicaturas, centros comunitarios, unidades deportivas). Una propuesta de política pública no puede depender de propiedades privadas o religiosas. *Pendiente de implementar.*

**2026-10-31 14:30 · Velocidad al caminar**
- Pasó: `CalculateIsolines` de Amazon Location no acepta velocidad peatonal (`TravelModeOptions` no tiene `Pedestrian`); `CalculateRoutes` sí (`Pedestrian.Speed`, en km/h, de 1.8 a 7.2).
- Decidí: el pipeline usa 3.6 km/h; las rutas en vivo también. Las isolíneas usan la velocidad por defecto del servicio. Hay que medir la diferencia y declararla.

**2026-10-31 15:33 · Infraestructura: Terraform + GitHub Actions, separada de otros proyectos y en $0**
- Intenté: revisar la cuenta de AWS antes de crear nada (solo lectura).
- Pasó:
  - La cuenta está en el plan gratuito, activo hasta el 28 mar 2027, con $139.97 de créditos.
  - Amazon Location, Amplify, Budgets e IAM entran en ese plan.
  - Las credenciales por defecto de esta máquina eran de otro proyecto y tenían más permisos de los necesarios.
  - El provider `hashicorp/aws` de Terraform no tiene recurso para las API keys de Amazon Location; `awscc_location_api_key` sí, aunque no devuelve el valor de la key.
- Cómo lo supe: `aws freetier get-account-plan-state`, `aws iam list-attached-user-policies` y la documentación de los providers.
- Decidí:
  - Todo separado de otros proyectos: un usuario IAM nuevo, `refugio-dev`, con MFA y credenciales temporales (`aws login`, perfil `refugio`); recursos con nombre `refugio-*` y etiqueta `Project=refugio`.
  - Toda la infraestructura en Terraform: Budget, API key, Amplify y el rol para GitHub Actions.
  - Amplify sin conexión a Git: GitHub Actions corre los tests y despliega con OIDC, sin llaves guardadas. La API key se lee de AWS durante el deploy, así que no queda ni en GitHub ni en el estado de Terraform. Reemplaza al `amplify.yml` de CLAUDE.md §5.
  - Costo objetivo: $0 (estado de Terraform local, GitHub Actions gratis por ser repo público).

**2026-10-31 15:52 · Entorno local y descarga**
- Intenté: crear un `.venv` con Python 3.12 (el prototipo se probó en 3.13) y correr `fetch.py culiacan` sin credenciales de AWS.
- Pasó: todas las librerías instalaron sin problema (duckdb 2.0.0, rasterio 1.5.2, h3 4.5.0). La descarga tardó 45 s; en la sesión de planeación tardó ~16 s, por la diferencia de internet.
- Decidí: correr `fetch.py` siempre sin credenciales (los buckets son públicos), para no depender de ninguna cuenta.

**2026-10-31 15:55 · Candidatos solo públicos (dos vueltas)**
- Intenté: quitar los templos y exigir nombre de escuela pública.
- Pasó: las escuelas quedaron bien, pero 3 de las 10 propuestas seguían sin cuadrar: "Udeci, A.C." (asociación civil), "CAIMF Medicina y Psicologia" (clínica) e "INE Sinaloa". Las categorías de Overture `government_office`, `social_or_community_service` y `sports_and_recreation` mezclan oficinas públicas con bancos, gimnasios, ONG, un partido político y el penal.
- Cómo lo supe: revisando a mano las 10 propuestas y la lista completa de candidatos por tipo.
- Decidí:
  - Fuera de las escuelas, un candidato solo entra si su nombre dice que es un edificio de la definición: sindicatura, delegación municipal, centro comunitario, casa de la cultura, unidad deportiva o ayuntamiento.
  - Se excluyen A.C., I.A.P., fundaciones, sindicatos, partidos y gimnasios, y "penal" se agregó a `EXCLUDE`.
  - Quedan 197 candidatos (186 escuelas). Las 10 propuestas son escuelas públicas por nombre y suben la cobertura a ≤10 min de 41.6% a 52.6% de los adultos 60+ (+6,091).
  - Limitación: "público" se deduce del nombre, no del catálogo de la SEP. "Primaria Ovidio Decroly" podría ser privada; hay que verificarla.

**2026-10-31 16:05 · Un test encontró un bug en el cálculo de distancias**
- Intenté: el test "agregar tiendas de alivio nunca empeora el acceso" (`any ≤ ref`).
- Pasó: falló en 28 hexágonos. El Dijkstra multi-origen elegía el refugio con la esquina más cercana sin contar los metros de la puerta a la esquina (hasta 300 m), y esos metros se sumaban después. Al agregar más lugares, a veces ganaba uno con la esquina cerca pero la puerta lejos.
- Cómo lo supe: el test `test_relief_never_makes_access_worse` en `pipeline/tests/test_outputs.py`.
- Decidí: un nodo virtual conectado a la esquina de cada refugio, con una arista del largo de esa caminata puerta–esquina. Un solo Dijkstra desde ahí da la distancia a la puerta realmente más cercana. Los 30 tests pasan. Las cifras casi no cambian: siguen siendo 17,039 adultos 60+ (30.7%) a más de 15 min.

**2026-10-31 16:20 · App web (MVP) y colores del mapa**
- Intenté: 6 rangos de color para los minutos a pie (≤5, 5–10, 10–15, 15–20, 20–30, >30), como decía el plan.
- Pasó: el validador de paletas mostró que en una rampa de un solo tono (azul) los dos rangos más oscuros no se distinguen (ΔL 0.047, el mínimo es 0.06).
- Cómo lo supe: `validate_palette.js --ordinal`.
- Decidí:
  - **5 rangos** (≤5, 5–10, 10–15, 15–20, >20 min) con azules que pasan todas las pruebas de contraste y daltonismo. El minuto exacto aparece en el tooltip.
  - El filtro "dónde viven adultos mayores" oculta los hexágonos con menos de 10 personas de 60+, en lugar de cambiar la transparencia: así los colores no mienten. Ese filtro deja el 29% de los hexágonos, donde vive el 69% de los adultos mayores.
  - El texto del panel (cifras, zonas, propuestas) lo escribe `pipeline/render_html.py` desde `stats.json`, en español e inglés, para que se lea sin JavaScript.
  - Librerías fijadas con hash de integridad (SRI): MapLibre GL JS 5.24.0 y h3-js 4.5.0. MapLibre 6 ya solo se distribuye como módulo ES y no tiene archivo único, así que se descartó por esta noche.
  - Un solo nombre para la key en el navegador: `web/config.js`, ignorado por git. En la laptop lleva la key local y en el deploy la de producción.
- Quedó para revisar: el refugio "Maxi Tours" aparece como plaza comercial; parece un error de categoría en Overture. Se confirmó y se quitó en la revisión de las 19:30.

**2026-10-31 16:40 · CI/CD**
- Decidí:
  - `ci.yml` corre tests, gitleaks y Terraform fmt/validate en cada pull request.
  - `deploy.yml` reutiliza `ci.yml` y solo publica si todo pasa. El deploy usa OIDC (rol `refugio-github-deploy`), lee la key de producción en el momento y termina con un smoke test con `curl`.
  - Regla propia de gitleaks para keys `v1.public.`: el historial está limpio y la regla detecta una key falsa.
  - actionlint: sin errores.

**2026-10-31 17:20 · Primer deploy: dos errores y lo que enseñaron**
- **Error 1, el workflow no arrancó** (0 s, "workflow file issue"):
  - Pasó: en `ci.yml` los jobs `secrets` y `terraform` quedaron sin sangría, así que YAML los leyó como secciones del archivo y no como jobs. Además había un typo (`pyhton-version`) y una ruta mal escrita (`pipeline/test`).
  - Cómo lo supe: `gh run view` y `actionlint` corrido con Docker, que da el número de línea.
  - Decidí: correr actionlint antes de cada push.
- **Error 2, `Not authorized to perform sts:AssumeRoleWithWebIdentity`:**
  - Pasó: los 3 checks pasaron, pero AWS rechazó el token de GitHub. El repo usa el formato *immutable subject* de GitHub, donde el `sub` es `repo:Josegas@80491054/Refugio-...@1441297459:environment:production`, con los IDs del dueño y del repo. La política de confianza esperaba el formato viejo, solo con nombres.
  - Cómo lo supe: `gh api repos/{owner}/{repo}/actions/oidc/customization/sub`.
  - Decidí: la política de confianza usa el formato con IDs, que es más seguro: un repo borrado y recreado con el mismo nombre no podría desplegar.
- **Hallazgo extra, un "perpetual diff" en Amplify:**
  - Pasó: el plan también quería "cambiar" los headers de seguridad de Amplify sin que hubieran cambiado.
  - Cómo lo supe: Terraform lo marcaba como `# whitespace changes`. AWS guarda los headers como JSON compacto con `pattern` antes de `headers`, y el código los tenía en YAML.
  - Decidí: escribirlos en Terraform exactamente como AWS los guarda. Ahora el plan solo muestra el cambio real.
- **Error 3, `AccessDeniedException` en `amplify:CreateDeployment`:**
  - Pasó: OIDC y la lectura de la key ya funcionaban, pero AWS revisó `CreateDeployment` sobre `.../branches/main/deployments/*`. La documentación del servicio solo menciona la rama, así que la política solo daba permiso sobre la rama.
  - Cómo lo supe: el mensaje de AccessDenied dice la acción y el recurso exactos.
  - Decidí: agregar solo esas rutas (`deployments/*` y `jobs/*` de la rama main). El mínimo privilegio se ajusta con evidencia, no dando permisos de más.

**2026-10-31 18:40 · App en vivo y búsqueda personal con Amazon Location**
- Pasó: el deploy salió en verde en 45 s. El sitio carga en 0.11 s desde CloudFront, `hex.json` viaja comprimido (83 KB en vez de 326 KB) y los 3 headers de seguridad están activos. `curl` del sitio muestra la cifra principal sin JavaScript.
- Primero verifiqué con llamadas reales la forma de las respuestas:
  - Geocode devuelve `Position` como `[lon, lat]`.
  - Las isolíneas vienen en `Isolines[].Geometries[].Polygon`.
  - La ruta viene en `Legs[].Geometry.LineString`, con duración y distancia en `PedestrianLegDetails.Summary.Overview`. La velocidad de 3.6 km/h sí se respeta: 1,626 m en 1,641 s.
- Latencias medidas (`?debug=1`): SearchNearby 486 ms, CalculateIsolines 810 ms, CalculateRoutes 986 ms. Las tres corren en paralelo, así que una búsqueda tarda alrededor de 1 s. Geocode tarda 383 ms.
- Primeras comparaciones contra la ruta real de Amazon Location:

  | Zona | Datos abiertos | Amazon Location |
  |---|---|---|
  | Díaz Ordaz | 30 min | 27 min |
  | Alturas del Sur | 12 min | 10 min |

  En los dos casos nuestro mapa es algo conservador, porque se mide hasta la esquina más cercana. La validación de 50 puntos dará la cifra completa.
- Hallazgo: en Díaz Ordaz, Amazon Location encuentra "Plaza Sur" a 382 m, pero en Overture esa plaza no existe como `shopping_mall` (solo algunas tiendas que están dentro). Además "Maxi Tours" viene como `shopping_mall` con 93% de confianza.
- Decidí:
  - La cifra principal ahora dice "según los datos abiertos de Overture Maps".
  - Antes de la entrega: spot-check de refugios, lista documentada de falsos positivos, y medir el hueco con SearchNearby en 50 hexágonos (solo se guarda el porcentaje).

**2026-10-31 19:30 · Evidencia: validación contra Amazon Location, el hueco de Overture y limpieza de refugios**
- Intenté: `pipeline/evidence.py`, con boto3 y el perfil `refugio`. Solo se guardan las cifras agregadas; las respuestas de Amazon Location no se guardan.
- **Validación (50 hexágonos al azar, semilla 2026):**
  - Diferencia mediana: **0.5 min**. P90: 1.7 min. **94% dentro de ±2 min** y 100% dentro de ±5 min. Correlación: 0.99.
  - El mapa de datos abiertos es un poco conservador: +0.2 min de mediana.
- **El hueco de Overture:** en el **10%** de los hexágonos (donde vive el 12% de los adultos mayores de la muestra), Amazon Location conoce un lugar tipo refugio al menos 150 m más cerca. La cifra principal se lee como un máximo.
- **Spot-check, primer intento:**
  - Pasó: con SearchNearby a 150 m, solo encontró 3 de 15 refugios. Lugares que sí existen salían como "no".
  - Cómo lo supe: revisando la lista a mano. Pedía los 10 lugares más cercanos de cualquier tipo, y en zonas comerciales la plaza grande quedaba fuera; además los nombres variaban.
  - Decidí: buscar cada lugar por su nombre (SearchText) a menos de 300 m. Resultado: **10 de 15 encontrados**, 8 de ellos con categoría compatible.
- **Limpieza:** revisé a mano todos los nombres. Quité 6 falsos positivos claros con una lista documentada (`NOT_REFUGES`) y sus tests:
  - una oficina de Megacable y "Maxi Tours", que venían como plazas comerciales;
  - un temazcal y una oficina municipal, que venían como centros comunitarios;
  - un grupo gnóstico y una escuela de idiomas, que venían como centros culturales.
- Resultado: quedan 211 refugios. **17,441 adultos mayores (31.4%)** están a más de 15 min. Las 10 propuestas suben la cobertura de 40.7% a 51.6% (+6,085).
- Quedó por hacer: volver a correr las pruebas 1 y 2 sobre los datos finales. Se hizo el 1 nov a las 00:30 y dieron las mismas cifras.

**2026-10-31 19:45 · Monitoreo de disponibilidad**
- Hice: `.github/workflows/uptime.yml`. Cada 3 horas revisa tres cosas: que la página muestre la cifra sin JavaScript, que carguen los datos del mapa y que la API key funcione desde el dominio. Pide el descriptor de estilo, que es una llamada que no se cobra.
- Pasó:
  - actionlint marcó la línea 3, pero el error real estaba en la línea 1: `name Uptime`, sin los dos puntos.
  - Había un typo en la URL de respaldo (`dr63` en lugar de `d6r3`) que ningún linter podía ver. La prueba manual habría salido verde, porque usaba otra copia de la URL, y las corridas automáticas habrían mandado una falsa alarma cada 3 horas.
- Decidí: la URL vive en un solo lugar. La alerta se probó a propósito con una URL que no existe: el run salió rojo con 404 y llegó el correo.

**2026-10-31 20:30 · Hermosillo y Mexicali**
- Intenté: correr el mismo pipeline en las dos ciudades.
- Pasó: Overture no tiene polígono `locality` para ninguna de las dos; solo municipios completos (16,978 km² y 11,611 km², casi todo desierto). Además, en el área de Mexicali el único `locality` es Calexico, del lado de EE.UU.
- Cómo lo supe: consultando `division_area` por subtipo dentro del bbox.
- Decidí:
  - **Área de estudio = mancha urbana sacada de la población.** Es el grupo contiguo más grande de celdas H3 (res 9) con al menos 300 hab/km², el umbral de "urban cluster" del método *Degree of Urbanisation* (UE/OCDE/ONU), recortado al municipio, sin huecos.
  - Las calles y los lugares también se recortan al municipio, para que Mexicali no rutee por Calexico.
  - Las zonas sin colonia en Overture se nombran por dirección y distancia al centro.
- Verifiqué:
  - Culiacán no cambia (prueba de regresión); su área de 138.1 km² coincide con la del plan.
  - Ninguna mancha urbana toca el borde del bbox.
  - En Mexicali hay 0 hexágonos al norte de la frontera.
  - Las propuestas son escuelas públicas por nombre. "Ecos Preescolar y Primaria" (Mexicali) podría ser privada: hay que verificarla.
- Resultados:

  | Ciudad | Área | Adultos 60+ a más de 15 min | Cobertura ≤10 min con 10 propuestas |
  |---|---|---|---|
  | Hermosillo | 148 km² | 18,859 (29.6%) | 41.2% → 51.5% |
  | Mexicali | 178 km² | 16,242 (26.5%) | 44.1% → 51.9% |

  Cada ciudad tarda ~35 s en descargarse y ~3 s en calcularse. Pasan 45 tests: los de datos corren para las 3 ciudades.
- Bug encontrado al probar: un link con `?city=` cargaba el mapa de esa ciudad pero dejaba el panel de Culiacán. Corregido.

**2026-11-01 00:30 · Validación final, kit visual y páginas para la IA evaluadora**
- **Validación sobre los datos finales:** volví a correr las pruebas 1 y 2 de `evidence.py` con los 211 refugios (la corrida anterior tenía 217). Todas las métricas salieron iguales: 0.5 min de diferencia mediana, 94% dentro de ±2 min y hueco de Overture en el 10% de los hexágonos.
- **Volúmenes y tiempos del pipeline:** `fetch.py` ahora guarda cuánto tarda cada descarga y `build.py` escribe una sección `pipeline` en `stats.json`. Culiacán: 28,002 lugares → 211 refugios; 49,024 segmentos → 57,276 aristas; 90,767 píxeles con población → 6,932 hexágonos; 34 s de descarga y 1.8 s de cálculo. Prueba de regresión: `hex.json`, los refugios y las propuestas quedaron idénticos byte por byte.
- **`about.html` y `llms.txt`:** los genera `render_html.py` desde `stats.json` y `docs/validation.md`, así que ninguna cifra está escrita a mano. `index.html` los enlaza y tiene `og:image`.
- **Diagramas K1–K3:** son SVG generados con Python (`docs/diagrams/render.py`) y exportados a PNG a 2x.
  - La librería `diagrams` no trae el ícono de Amazon Location, así que uso el paquete oficial de AWS Architecture Icons.
  - Los íconos no van en git: son marcas de AWS y no entran en la licencia MIT. El script los descarga la primera vez.
- **Gráficas K6 y K7:** matplotlib, con la misma rampa de azules del mapa. Las 3 ciudades de K7 usan colores categóricos validados para daltonismo; el aqua tiene contraste bajo, por eso cada línea lleva su nombre al final.
- **Capturas K4, GIF K5 y latencias:** `docs/diagrams/capture.py` usa Playwright contra el sitio en vivo.
  - Error 1: las capturas de celular salían con el mapa casi en blanco. No era un bug de la app: ningún elemento tapaba el mapa y MapLibre sí reportaba 2,017 hexágonos dibujados. Era el WebGL de Chromium sin pantalla. Con `--use-angle=swiftshader` la parte casi blanca bajó de 96% a 1%.
  - Error 2, en la app: con `?debug=1` el tiempo de Geocode no aparecía, porque `searchFrom` borraba la lista de tiempos. Lo corregí, aunque solo afecta al modo debug. Para medir no dependí de la app: el script cronometra cada `fetch()` a Amazon Location desde el navegador.
  - Latencias (mediana de 5 búsquedas en vivo): Geocode 122 ms, SearchNearby 160 ms, CalculateRoutes 342 ms y CalculateIsolines 366 ms. Una búsqueda completa tarda **486 ms**. Las mediciones del 31 oct fueron más lentas (~1 s); eran las primeras llamadas.
- **Dirección de la demo:** "Colonia Libertad, Culiacán". Está en la zona con más adultos mayores lejos de un refugio, el refugio más cercano es el Museo de Ciencias (público, sin marca) y la ruta de Amazon Location y el mapa de datos abiertos coinciden: **26 min**. La isolínea de 15 min no alcanza el museo.
- Costo de esta sesión: ~100 llamadas de validación más ~50 de capturas, dentro de la capa gratuita.

**2026-11-01 01:10 · Factor de rodeo, README, borrador del artículo y guion del video**
- **Factor de rodeo en `stats.json`:** el test de la red ya lo calculaba, pero no lo guardaba. Ahora `build.py` lo escribe con el mismo método (semilla 42, pares de 0.5 a 5 km): Culiacán 1.24 (p5 1.09, p95 1.71), Hermosillo 1.27 y Mexicali 1.27. Es la evidencia de la decisión "red de calles en lugar de radios".
- Nota: `build_seconds` cambia un poco en cada corrida (ahora 2.1 s en Culiacán, porque incluye ese cálculo). Los diagramas y los textos usan el valor actual, así que después de correr `build.py` hay que volver a generar los diagramas.
- **`about.html`** ahora muestra el diagrama de arquitectura (K1) y la gráfica de validación (K8). `render_html.py` los copia a `web/img/`. Sirven para el segmento "cómo funciona" del video, que no puede mostrar GitHub.
- **README en inglés:** refleja el artículo, con dos diagramas Mermaid (arquitectura y secuencia de una búsqueda). Los dibujé con mermaid 11 antes de subirlos para comprobar que no salen rotos en GitHub.
- **Artículo para AWS Builder Center:** borrador de ~2,000 palabras más tablas, con la caja "Try it in 1 minute" al inicio. El README tiene el mismo contenido; los borradores se trabajan fuera del repo.
- **Video:** guion de 2:55 con narración en español y subtítulos en inglés, cuidando las reglas del concurso (URL visible, sin marcas de terceros, sin otras apps, sin música).

**2026-11-01 02:00 · Población 60+ contra el censo y dos propuestas dudosas**
- **60+ contra INEGI:** HRSL da 7.7% de población de 60+ en Culiacán (7.8% en Hermosillo y 7.9% en Mexicali). Parecía bajo, así que lo comparé con el censo 2020.
  - Cómo lo supe: el archivo ITER 2020 de INEGI (resultados por localidad, columnas `POBTOT` y `P_60YMAS`) da 10.9% en la ciudad de Culiacán, 11.4% en Hermosillo y 11.4% en Mexicali. HRSL cuenta unos 30% menos adultos mayores en las tres.
  - Decidí: mantener HRSL, porque es el que dice *dónde* vive la gente, y reportar la diferencia con números. `pipeline/census.py` escribe la comparación en `stats.json` y en `docs/validation.md` (sección 4). Si el faltante es parejo, los porcentajes del mapa no cambian, pero el conteo sí: los 17,441 serían unos 24,700 con la proporción del censo.
  - Matiz: esto empuja en sentido contrario al hueco de Overture. Los lugares que le faltan a Overture hacen que el *porcentaje* lejos de un refugio se vea más alto de lo real; el censo dice que el *número* de adultos mayores es mayor.
  - Hay que correr `census.py` después de `build.py`, porque `build.py` reescribe `stats.json`.
- **Dos propuestas dudosas:** "Primaria Ovidio Decroly" (Culiacán) y "Ecos Preescolar y Primaria" (Mexicali).
  - Cómo lo supe: ni en la web ni en Overture encontré si son públicas; solo hay páginas de Facebook y, en el caso de Ecos, un correo de Hotmail. Las señales apuntan a privadas: Ecos tiene nombre de marca y junta preescolar y primaria en un solo plantel, y "Decroly" es el nombre de un método pedagógico que usan colegios privados.
  - Decidí: excluirlas con una lista documentada (`NOT_CANDIDATES`) y dos tests nuevos (ahora son 47). Es preferible perder una escuela pública por error que proponer una privada como edificio público.
  - Resultado: en Culiacán la cobertura a ≤10 min con 10 propuestas pasa de 40.7% a **51.4%** (+5,959); antes 51.6%. Mexicali queda en 51.9%. Regeneré los diagramas, las gráficas y los textos.
  - Las capturas mostraban las propuestas viejas; se volvieron a tomar después del deploy (entrada de las 02:55).

**2026-11-01 02:55 · Capturas nuevas y tiempo de carga**
- Volví a tomar K4, K5 y `og.png` desde el sitio en vivo, ya con las propuestas nuevas (51.4%).
- **Tiempo hasta ver el mapa con hexágonos** (la meta era menos de 3 s): mediana de **2.1 s en escritorio** y **1.7 s en celular**, en 3 visitas cada uno con caché vacía. La primera visita de todas tardó 3.6 s (conexión en frío al CDN). Lo medí con Playwright y WebGL por software; en un equipo real con GPU debería ser igual o más rápido.

**2026-11-01 16:45 · Pulido visual del mapa y del panel**
- Hice: cambios solo de estilo (CSS, propiedades de MapLibre y una leyenda en HTML), sin tocar datos, pipeline ni llamadas a Amazon Location.
  - **Hexágonos sin borde blanco.** Las celdas vecinas con el mismo tiempo se leen como una zona y no como un panal. H3 sigue siendo la unidad de análisis: quitar el borde es solo una decisión visual.
  - **Leyenda sobre el mapa** con los 5 intervalos, refugios, alivio (solo si está activo) y propuestas. Después de una búsqueda agrega las áreas de 5/10/15 min y la ruta. En modo demo dice "línea recta, no es una ruta". En celular va arriba a la izquierda, solo con los colores, y se oculta mientras hay un popup abierto.
  - **Celda seleccionada** con contorno oscuro al tocarla. En celular no hay hover, así que antes no se veía qué hexágono se había tocado.
  - **Áreas caminables** con un relleno blanco suave debajo de cada línea: el área de 5 min, que está dentro de las tres, queda como la más clara.
  - **Panel:** la cifra principal va primero, en una tarjeta cálida, y la explicación pasa después de la búsqueda. Botones de al menos 44 px de alto, popups como fichas con el tiempo en grande y transiciones apagadas si el sistema pide menos movimiento.
- Pasó: al quitar el borde, las orillas seguían viéndose como costuras más oscuras.
- Cómo lo supe: en las capturas de antes y después con Playwright. El suavizado de bordes de dos celdas semitransparentes se encima justo en la orilla compartida.
- Decidí: `fill-antialias: false` en la capa de hexágonos. Las costuras desaparecieron y a ese tamaño de celda no se notan bordes dentados.
- Verifiqué: 47 tests pasan, sin errores en la consola, la página sin JavaScript sigue mostrando la cifra (`hero-num`, que es lo que revisa el monitoreo) y la búsqueda real dibuja isolíneas, ruta y lugares cercanos (una búsqueda, 6 llamadas).
- Pendiente: volver a tomar K4, K5 y `og.png` desde el sitio en vivo después del deploy.

**2026-11-01 17:20 · Aviso de lugares que le faltan a Overture y correcciones de texto (revisión externa)**
- Pasó: una revisión externa de la app en vivo notó que en el ejemplo de Díaz Ordaz el refugio más cercano está a 31 min, pero Amazon Location lista "Plaza Sur" a 363 m sin ninguna nota. Es el hueco de Overture que ya medimos en la validación (10% de los hexágonos), pero la app no lo decía.
- Decidí: cuando SearchNearby encuentra un lugar tipo refugio (plaza, departamental, biblioteca, museo o centro comunitario) al menos 150 m más cerca en línea recta que nuestro refugio, la app muestra un aviso. Es el mismo umbral de la validación. Súper, farmacias y tiendas no cuentan, porque no son refugios. No se guarda nada: es la misma respuesta `SingleUse`.
- Otras correcciones de la misma revisión:
  - "Según los datos abiertos de Overture Maps" en la cifra principal: la población viene de Meta HRSL, no de Overture. Ahora dice las dos fuentes, en el panel y en `about.html`.
  - El encabezado de una columna de `about.html` empezaba con "...". Ahora se entiende solo.
  - Los botones de ejemplo ahora dicen qué son: las 3 zonas con más adultos mayores lejos de un refugio.
- No apliqué tres sugerencias:
  - Decir "al menos 17,441": los dos sesgos van en sentidos contrarios (HRSL cuenta menos adultos mayores, Overture tiene menos lugares), así que la cifra no es un mínimo.
  - Usar Las Quintas como contraejemplo "porque la mayoría tiene coche": no tenemos datos de coches; sería inventarlo.
  - Las cifras ajustadas por el censo de Hermosillo y Mexicali sí cuadran: se calculan con las proporciones sin redondear, no con los porcentajes de la tabla.
- Verifiqué: el ejemplo de Díaz Ordaz muestra el aviso de Plaza Sur en ES y EN, sin errores en la consola, y pasan los 47 tests.

**2026-11-01 17:40 · Bug: cambiar de ciudad dejó de funcionar con el rediseño**
- Pasó: al elegir Hermosillo en el selector, la consola mostraba `Source "hexes" cannot be removed while layer "hex-selected" is using it` y el mapa caía en modo demo.
- Cómo lo supe: revisando el código de `switchCity` antes de empezar el tour, y después reproduciéndolo con Playwright. Las pruebas del rediseño no cubrieron el cambio de ciudad.
- Causa: el rediseño agregó la capa `hex-selected` (el contorno de la celda tocada), pero no se agregó a la lista de capas que se borran antes de cambiar los datos.
- Decidí: borrarla junto con las demás y reiniciar la selección. Verificado: Hermosillo carga sin errores. Lección: cada capa nueva va a esa lista, y el cambio de ciudad entra en la revisión de cada cambio visual.

**2026-11-01 17:35 · Recorrido guiado (rama `feature/tour`)**
- Por qué: los proyectos mejor hechos del reto tienen un recorrido guiado, y un juez entiende el mapa en un minuto sin tener que explorarlo.
- Hice: `web/tour.js`, aparte de `app.js`, que solo usa lo que la app ya hace (volar el mapa, cambiar la capa y una búsqueda). Se abre con el botón "Recorrido guiado" del panel o con `?tour=1`. Tiene 6 paradas en ES y EN: el problema, el hueco más grande, una búsqueda desde una casa (con el aviso de Plaza Sur, que es la parada honesta: muestra dónde fallan nuestros datos), el modo con farmacias y tiendas, las 10 propuestas y "ahora tú". Todas las cifras salen de `stats.json`.
- Costo: la parada 3 hace una búsqueda real, es decir 6 llamadas facturables por recorrido. Entra en el límite de 30 búsquedas por visita.
- Pasó en las pruebas: en la parada 3 el resultado quedaba fuera de la vista del panel, y en celular el panel está doblado. Ahora el panel se desplaza al resultado en escritorio, y en celular el texto dice que lo abras. Además, mientras la tarjeta está abierta, el mapa se centra en la parte de la pantalla que la tarjeta no tapa.
- Verifiqué con Playwright: las 6 paradas en escritorio (1440×900), celular (390×844) y pantalla angosta (1024×768); los botones Anterior y Salir; el cambio de idioma con la tarjeta abierta; y que, abierto desde Hermosillo, regresa a Culiacán. Sin errores en la consola y pasan los 47 tests.
- **Ajuste (17:50):** el texto de las propuestas no decía a qué se refieren los porcentajes, y no explicaba cómo abriría una escuela sin dejar de ser escuela. Ahora dice "los adultos mayores de la ciudad con un refugio a 10 min o menos a pie" y aclara que la idea es abrirlas en vacaciones de verano y fines de semana, cuando no hay clases, y solo las que tengan aire acondicionado. Primero escribí "por la tarde", pero la mayoría de las escuelas públicas en México también tiene turno vespertino; para los días de clases el siguiente paso es buscar otros edificios públicos. Va en el tour, en el panel (`render_html.py`) y en `about.html`, que además lista lo que habría que verificar: aire acondicionado, personal, baños y el acuerdo de la escuela. Las 10 propuestas de las tres ciudades son escuelas porque el algoritmo solo mira la ubicación.
- **¿Por qué las 10 propuestas son escuelas? (18:00):** conté los candidatos por tipo con `load_places` de `build.py`. Culiacán tiene 196 candidatos: 183 escuelas, 8 oficinas de gobierno, 3 deportivos y 2 centros comunitarios. En Hermosillo son 238 escuelas de 243 y en Mexicali 327 de 336. El algoritmo no prefiere escuelas; es que casi todos los candidatos lo son. Hay escuelas en todas las colonias, y los otros edificios públicos solo cuentan si su nombre confirma qué son, porque esas categorías de Overture traen mucho ruido (bancos, gimnasios, el penal). Va en las limitaciones del artículo.

**2026-11-01 22:30 · Resultados como tabla Apache Iceberg en S3, consultada con Athena (rama `feature/iceberg`)**
- Por qué: el reto sugiere tablas Iceberg en S3, y así cualquiera con permiso puede hacerle preguntas en SQL a los resultados de las tres ciudades sin servidores encendidos. La app en vivo no usa nada de esto.
- Hice: `infra/analytics.tf` crea un bucket privado, una regla que borra los resultados de Athena a los 7 días, la base de datos `refugio` en Glue y el workgroup `refugio` de Athena (motor v3, carpeta de resultados fija y tope de 1 GB por consulta). `pipeline/iceberg.py` sube un Parquet por ciudad, crea la tabla `refugio.hexagons` y la llena con un `INSERT` por ciudad, así que la tabla queda con 3 snapshots. Después corre 4 consultas de ejemplo y escribe `docs/iceberg.md`. Todo tardó 26 s.
- Decidí: Iceberg en un bucket normal con Glue y Athena, no S3 Tables. Para consultar S3 Tables desde Athena hay que activar una integración con Lake Formation que tiene varios pasos manuales de permisos, y con el tiempo que queda era riesgoso. El siguiente paso sería migrar a S3 Tables para que AWS se encargue del mantenimiento.
- Solo guardamos nuestros resultados de datos abiertos. Nada de Amazon Location Places.
- Pasó: en la consola de Athena salió "Antes de ejecutar la primera consulta, debe configurar una ubicación del resultado de la consulta en Amazon S3". La consola abre en el workgroup `primary`, que no tiene carpeta de resultados. La solución es elegir el workgroup `refugio`. No configuré una carpeta en `primary`, porque ahí las consultas no tendrían el tope de 1 GB ni la limpieza a los 7 días.
- Diferencia con `stats.json`: la tabla guarda los valores redondeados que publica el mapa (minutos a 0.1), así que "más de 15 min" da un poco menos: Culiacán 17,368 contra 17,441, Hermosillo 18,715 contra 18,859 y Mexicali 16,104 contra 16,241, menos de 1% en las tres. Las cifras de la entrega siguen saliendo de `stats.json`. Está explicado en `docs/iceberg.md`.
- La fila sin tipo de la segunda consulta son 52 hexágonos de Culiacán con 24 adultos mayores que no tienen ningún refugio a menos de 60 min, el límite de búsqueda.
- Costo: unas 15 consultas de Athena, cada una cobrada como 10 MB. Menos de un centavo de dólar.
