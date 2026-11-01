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

**2026-10-31 15:33 · Infraestructura: Terraform + GitHub Actions, separada de Kupi y en $0**
- Intenté: revisar la cuenta de AWS antes de crear nada (solo lectura).
- Pasó:
  - La cuenta está en el plan gratuito, activo hasta el 28 mar 2027, con $139.97 de créditos.
  - Amazon Location, Amplify, Budgets e IAM entran en ese plan.
  - Las credenciales por defecto de esta máquina son las del usuario `kupi-deploy`, de otro proyecto: administrador y con llaves permanentes.
  - El provider `hashicorp/aws` de Terraform no tiene recurso para las API keys de Amazon Location; `awscc_location_api_key` sí, aunque no devuelve el valor de la key.
- Cómo lo supe: `aws freetier get-account-plan-state`, `aws iam list-attached-user-policies` y la documentación de los providers.
- Decidí:
  - Todo separado de Kupi: un usuario IAM nuevo, `refugio-dev`, con MFA y credenciales temporales (`aws login`, perfil `refugio`); recursos con nombre `refugio-*` y etiqueta `Project=refugio`.
  - Toda la infraestructura en Terraform: Budget, API key, Amplify y el rol para GitHub Actions.
  - Amplify sin conexión a Git: GitHub Actions corre los tests y despliega con OIDC, sin llaves guardadas. La API key se lee de AWS durante el deploy, así que no queda ni en GitHub ni en el estado de Terraform. Reemplaza al `amplify.yml` de CLAUDE.md §5.
  - Costo objetivo: $0 (estado de Terraform local, GitHub Actions gratis por ser repo público).

**2026-10-31 15:52 · Entorno local y descarga**
- Intenté: crear un `.venv` con Python 3.12 (el prototipo se probó en 3.13) y correr `fetch.py culiacan` sin credenciales de AWS.
- Pasó: todas las librerías instalaron sin problema (duckdb 2.0.0, rasterio 1.5.2, h3 4.5.0). La descarga tardó 45 s; en la sesión de planeación tardó ~16 s, por la diferencia de internet.
- Decidí: correr `fetch.py` siempre sin credenciales (los buckets son públicos), para no depender de ninguna cuenta.

**2026-10-31 15:55 · Candidatos solo públicos (dos vueltas)**
- Intenté: quitar los templos y exigir nombre de escuela pública (CLAUDE.md §6.1).
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
- Pendiente: el refugio "Maxi Tours" aparece como plaza comercial; parece un error de categoría en Overture. Va al spot-check (§6.5).

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
- Pendiente: volver a correr las pruebas 1 y 2 sobre los datos finales antes de escribir el artículo.

**2026-10-31 19:45 · Monitoreo de disponibilidad**
- Hice: `.github/workflows/uptime.yml`. Cada 3 horas revisa tres cosas: que la página muestre la cifra sin JavaScript, que carguen los datos del mapa y que la API key funcione desde el dominio. Pide el descriptor de estilo, que es una llamada que no se cobra.
- Pasó:
  - actionlint marcó la línea 3, pero el error real estaba en la línea 1: `name Uptime`, sin los dos puntos.
  - Había un typo en la URL de respaldo (`dr63` en lugar de `d6r3`) que ningún linter podía ver. La prueba manual habría salido verde, porque usaba otra copia de la URL, y las corridas automáticas habrían mandado una falsa alarma cada 3 horas.
- Decidí: la URL vive en un solo lugar. La alerta se probó a propósito con una URL que no existe: el run salió rojo con 404 y llegó el correo.

**2026-10-31 20:30 · Hermosillo y Mexicali**
- Intenté: correr el mismo pipeline en las dos ciudades (§6.3).
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
