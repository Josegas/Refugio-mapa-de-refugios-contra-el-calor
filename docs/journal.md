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
