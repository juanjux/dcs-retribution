# Realistic CAS — plan de implementación

Estado: plan aprobado; núcleo y controles de sensores validados in-engine en
pruebas 31–37. Primer exportador de registro de campaña implementado y probado,
todavía sin inyección/activación de campaña. Entorno y adaptadores pendientes.
Batería de pruebas aisladas en `tools/realistic_cas_tests`.
Primera tanda in-engine analizada: `realistic-cas-results-20260909.md`.
Segunda tanda analizada: `realistic-cas-results-round2-20260909.md`.
SetInvisible efectivo por grupo en prueba terrestre, bloqueo de tiro acreditado en
CAS/AttackUnit ensayados; granularidad por grupo aceptada por el usuario.
Fecha: 2026-09-09. Base inspeccionada: origin/master, 0867de9eb.
Worktree: `dcs-retribution-codex-worktrees/realistic-cas`.
Rama: `codex/realistic-cas-plan`.

## 1. Objetivo y decisiones del usuario

Mission Plugin opcional que sustituya el conocimiento perfecto de posiciones
terrestres por detecciones y contactos con caducidad. Simétrico para rojo y azul,
independiente de la niebla de guerra general. Desactivado debe conservar exactamente
la generación y comportamiento actuales.

- CAS, BAI, Armed Recon y JTAC consumen la información del plugin.
- Aclaración posterior del usuario: las unidades ocultas también quedan ocultas a
  los enemigos terrestres. Los vehículos e infantes serán observadores con un modelo
  propio de detección terrestre. Esto amplía la propuesta inicial de no afectar al
  combate entre unidades terrestres.
- Disparar desvela automáticamente al tirador, aunque no haya observadores en alcance.
- Posición antigua si se puede imponer de verdad a la IA; alternativamente, exposición
  temporal renovable, inicialmente 600 segundos configurables.
- Drones y helicópteros JTAC vulnerables, sin invisibilidad ni inmortalidad artificial.
- Decisión posterior a pruebas: ocultación F10 fuera de alcance; no modificar sus
  iconos/settings. Debug opcional; satélites para una segunda iteración.
- Prioridad explícita del usuario: aproximaciones de bajo coste. No modelar sensores
  ni atmósfera al detalle a costa del rendimiento. No asumir fuego continuo en el
  frente vanilla: medir por separado Retribution normal y TIC.
- No modificar todavía el planificador estratégico, la economía ni las posiciones
  conocidas en el mapa de campaña. El ámbito es la misión DCS.

Prioridad de aceptación reiterada por el usuario tras la prueba 37: que el CAS no
extermine automáticamente todo el frente y sustituya el combate terrestre. Validar
la búsqueda y el combate, no únicamente que SetInvisible y cada canal funcionen.
No reducir por decreto precisión, munición o letalidad de las armas: el límite es
el descubrimiento de blancos. Un radio amplio con revelado instantáneo no basta.
Se añadió adquisición gradual configurable, una búsqueda de grupo desconocido
por observador; su balance en combate aún no está validado in-engine.

Decisión confirmada tras la prueba 37: excluir de la ocultación los emplazamientos
SAM que son objetivos identificados en el mapa de campaña (SamGroundObject,
categoría `aa`), incluidos sus grupos de apoyo. La excepción es por pertenencia al
objetivo, no por arma de ataque, tipo de vehículo, inmovilidad ni nombre del grupo.
Los SAM del frente SÍ participan en la niebla. Los edificios STRIKE siguen fuera.
BAI no concede revelado previo gratuito, sea grupo fijo o convoy; conserva tareas y
rutas nativas y puede adquirir por proximidad/sensores. No se implementa un TTL
inicial ni un seguimiento GPS ficticio para los emplazamientos excluidos.

## 2. Evidencia del código y del motor

### Integraciones ya localizadas

- `game/missiongenerator/aircraft/waypoints/casingress.py`: añade búsqueda y ataque
  genéricos mediante EngageTargetsInZone/EngageTargets.
- `.../armedreconingress.py`: búsqueda genérica de unidades terrestres y helicópteros.
- `.../baiingress.py`: AttackGroup directo por ID, posible fuente de conocimiento
  previo y de exposición accidental de compañeros del mismo grupo.
- `game/missiongenerator/flotgenerator.py`: JTAC azul con FAC genérico, vuelo a
  5.000 m y órdenes explícitas SetInvisible y SetImmortal.
- `resources/plugins/MooseAutolase/Plugin_Autolase_JTAC.lua`: vuelve a establecer
  invisibilidad e inmortalidad por defecto en Alpha/Bravo y desplaza sus órbitas.
- MOOSE incluido: AUTOLASE tiene CanLase y una mejora opcional de conocimiento de
  unidades terrestres (_Prescient). Filtrar solo el mensaje de contacto sería tarde:
  hay que filtrar adquisición, designación, seguimiento y selección del siguiente blanco.
- `resources/plugins/tic/TIC_v1.1.lua`: tiene Cloak/Decloak, un spotter, un tracker
  geométrico y control propio de invisibilidad. Necesita un adaptador, no dos scripts
  alternando el mismo estado. Su fuego simulado/ambiental también puede generar revelados.
- `game/missiongenerator/luagenerator.py` y MissionData: punto de exportación de datos
  Python → Lua e inyección ordenada de plugins. Ya existen adaptadores independientes
  para GPS jamming y otros plugins: seguir ese patrón.
- Pydcs instalado serializa hidden, hiddenOnPlanner y hiddenOnMFD por grupo. Esto no
  demuestra que puedan alternarse por script sobre una unidad ya existente.

### Capacidades y límites comprobados en documentación oficial

- SetInvisible oculta una unidad/grupo a la IA enemiga; no es invisibilidad visual
  para el humano ni se documenta un filtro por clase de observador.
- isTargetDetected permite leer lastTime, lastPos y lastVel cuando deja de verse.
  knowTarget recibe un objeto real y dos booleanos, no una posición ficticia.
  No se ha encontrado una API documentada para sustituir o borrar selectivamente
  la memoria nativa. No confundir memoria del plugin con memoria del motor.
- Unit.getSensors publica ópticas y capacidades de radar, incluyendo RBM/HRM;
  getRadar informa encendido/objeto seguido, no el modo GMT ni el barrido real del pod.
- land.getSurfaceType solo distingue LAND, SHALLOW_WATER, WATER, ROAD y RUNWAY.
  No identifica por sí sola desierto, pradera, tundra, bosque o ciudad.
- Las funciones de terreno y sensores son datos aprovechables, no una garantía de
  modelar árboles individuales, edificios, nubes volumétricas o daño del sensor.

Fuentes primarias consultadas:

- [ED: Controller, tareas y SetInvisible](https://www.digitalcombatsimulator.com/en/support/faq/1267/).
- [ED: Detection y memoria](https://www.digitalcombatsimulator.com/en/support/faq/1268/).
- [ED: Unit y sensores](https://www.digitalcombatsimulator.com/en/support/faq/1262/).
- [ED: Singletons y terreno](https://www.digitalcombatsimulator.com/en/support/faq/1257/).
- [USAF: E-8C y vigilancia terrestre](https://www.af.mil/News/Article/104507/e-8c-joint-stars/).

## 3. Fase cero: demostrar la mecánica en DCS

Antes del modelo completo, misiones pequeñas, reproducibles y con arranque en vuelo.
Cada una compara control y variante; sin cazas/SAM ajenos a la hipótesis. Instrumentar
disparos, detección nativa, estado del plugin y tarea asignada. Repetir para distinguir
azar/skill de una limitación real. No extrapolar Lupa al comportamiento del simulador.

1. **Granularidad de invisibilidad.** Dos vehículos en un grupo: ocultar solo uno
   mediante controlador de unidad, después mediante controlador de grupo. Verificar
   contra tanque, CAS y FAC; añadir grupo SAM compuesto. Si solo funciona por grupo,
   no desvelar silenciosamente una batería entera ni dividir baterías/convoyes:
   documentar la limitación y acordar granularidad o cambiar el mecanismo.
2. **Detección y tiro.** Oculto → visible → oculto, tanto sin adquirir como ya adquirido.
   Comparar EngageTargetsInZone, AttackGroup, AttackUnit y EngageUnit. Comprobar si
   knowTarget atraviesa invisibilidad, si persiste la puntería y qué sucede con las
   armas ya en vuelo. DCS seguirá resolviendo impactos y daños normalmente.
3. **Posición obsoleta.** Adquirir vehículo, perderlo y moverlo. Comprobar si el ataque
   sigue coordenadas antiguas o al objeto actual. No usar Bombing como sustitución
   universal de un ataque con Maverick/Hellfire: cambiaría el arma y la misión.
4. **Lista autorizada de ataque.** Con varios vehículos próximos, un vuelo solo recibe
   permiso/tarea de atacar uno. Comprobar líderes, puntas y retorno a la ruta; después
   caducar ese permiso. Prueba de aceptación: cero ataques nuevos a blancos ocultos.
5. **FAC nativo y MOOSE.** Solo pueden designar blancos permitidos; no pasar al vecino
   oculto tras una muerte. Relieve y muerte del JTAC cortan la designación;
   comportamiento de nubes y canales EO/IR/láser debe medirse por separado en DCS.
   Si FAC nativo solo filtra grupos, decidir si se sustituye por un JTAC controlado
   con menú/radio script, explicando la diferencia respecto al protocolo nativo.
6. **F10: cerrado por alcance.** Prueba 13 ejecutada; el usuario no requiere ocultación
   en el mapa. No ampliar la matriz de roles ni cambiar su representación.
7. **Eventos de fuego.** Ametralladora, cañón de tanque, AAA, SAM, artillería y fuego TIC.
   No asumir que S_EVENT_SHOT cubre cada modalidad de disparo.

Salida de fase: tabla de observado/no soportado por versión DCS y decisión de backend.
Si no existe una combinación fiable, presentar la limitación antes de implementar
la parte dependiente; no entregar una niebla cosmética como si limitara a la IA.

## 4. Modelo de información

Un servicio central, con contactos separados por coalición observadora y unidad:

`UNKNOWN → FRESH → STALE → EXPIRED`, con nueva observación devolviendo a FRESH.

Datos mínimos: ID/nombre estable, bando dueño, última posición OBSERVADA, instante,
caducidad, clase conocida, fuente/observador, calidad y motivo de detección.
Los objetos del motor y sus posiciones verdaderas se mantienen en un registro interno
separado; nunca se usan para refrescar automáticamente un contacto público.

- Una observación real actualiza posición y renueva el plazo; compartir un informe
  entre unidades no lo rejuvenece. No hay realimentación infinita entre JTAC y CAS.
- La muerte de un observador detiene sus aportes inmediatamente. Lo que comunicó
  previamente conserva su caducidad; su láser se apaga.
- Una unidad muerta deja de ser atacable, pero no confirmar su destrucción al jugador
  por arte de magia si nadie la ha observado: el marcador puede quedar obsoleto.
- Con backend temporal, una unidad expuesta será localizable en su posición REAL
  durante el plazo. Esa es la aproximación consentida, no información obsoleta real.
- Mantener última posición auténtica en la memoria interna del plugin aunque la IA
  necesite el backend temporal. No modificar F10 para representar esa memoria.
- Para un contacto STALE, el vuelo puede buscar alrededor de la última posición;
  no recibir automáticamente el ID del vehículo movido para seguirlo fuera de ella.
- Al iniciar misión, registrar y ocultar antes de las primeras adquisiciones. Incluir
  nacimientos tardíos, transportes, desembarcos, respawns y clones de TIC.
- Neutrales y objetos de infraestructura requieren política explícita: la primera
  versión cubre vehículos/infantería, incluidos SAM del frente pero no los
  emplazamientos SAM identificados como objetivos en el mapa. No borrar del
  mapa aeródromos, edificios o blancos estáticos conocidos sin una necesidad acordada.

### Backend de aplicación

Preferencia tras la ampliación terrestre: SetInvisible como barrera nativa, gobernada
por el servicio central y compatible con el estado original de cada unidad.
Las detecciones se calculan externamente: no esperar que el radar nativo detecte un
objeto que hemos hecho invisible, porque eso produciría un bloqueo circular.

Si la invisibilidad no basta para caducar blancos previamente conocidos, complementar
con tareas unitarias autorizadas y ControlledTask/condiciones de parada para CAS/BAI/
Armed Recon. No limpiar y reconstruir toda la ruta en cada tick. Conservar TOT,
patrulla, combustible, munición, escoltas, evasión y vuelta a base. Sin blancos, buscar
durante la ventana asignada y luego regresar, no orbitar para siempre ni RTB inmediato.

No asignar por error roles nuevos al avión. El rol sale de FlightData, no de parsear
el nombre del grupo ni del rol CAS genérico con que DCS representa otras misiones.
Grupos mixtos humano/IA necesitan prueba propia: no cambiar órdenes del jugador ni
retomar su grupo por script sin una política explícita.

## 5. Formas de desvelado

| Fuente | Regla propuesta | Límite importante |
| --- | --- | --- |
| Disparo | Revelado inmediato y renovación del TTL | Solo el tirador; no sus vecinos por proximidad |
| Visual aéreo | Alcance base 5 NM, AGL, LOS y condiciones | No esfera omnisciente; tiempo de búsqueda y sector útil |
| EO/IR | Mejor adquisición/seguimiento según equipo | Pod montado o sensor integrado; relieve bloquea, nubes según comportamiento DCS observado, sin veto universal IR |
| Radar terrestre RBM | Alcance corto, cono y LOS | Solo plataformas con radar terrestre, en CAS/BAI/Armed Recon |
| GMTI | Mayor alcance para vehículos moviéndose | Capacidad explícita; umbral de movimiento y geometría radial |
| Observador terrestre | Visual/óptica/térmica a alcance terrestre | Tanque térmico, infantería y camión no ven igual |
| JTAC | Observa con su plataforma y comparte | Necesita observación local válida para identificar/iluminar |

Separar detectar, clasificar y localizar: ver un retorno no implica identificar
modelo, carga y tripulantes. Para la V1, sin falsos contactos ni errores de IFF,
pero el mensaje puede ser «vehículo» hasta obtener identificación de mayor calidad.

### Sensores y geometría

- Leer/cachar getSensors y combinarlos con metadatos curados por variante y carga
  real. Distinguir TV, LLTV e IR; no dar térmica a un Ka-50 por tener Shkval ni radar
  terrestre a cualquier avión que tenga radar aire-aire.
- La IRST aire-aire no equivale automáticamente a FLIR de adquisición terrestre.
- Radar: transformar vector al objetivo al sistema del detector; límites horizontal
  y vertical, distancia oblicua, terreno y perfil del radar. El cono no es todo el
  hemisferio delantero. Solo aeronaves activas y realizando el papel autorizado.
- Si no hay telemetría fiable del modo AI, representar RBM/GMT como capacidades del
  modelo: regla RBM para estacionarios y GMTI para móviles, no fingir que se ha leído
  la página del radar. No imponer al humano una exploración inexistente.
- Ópticas: sector y tiempo de búsqueda aproximados si no se publica la mirada real.
  La fase cero determina dónde usar datos nativos de detección como evidencia.
- Observadores terrestres: altura del sensor sobre terreno, distancia 3D/LOS,
  velocidad propia, ópticas instaladas y condiciones. No usar alcance de arma como
  alcance de detección.

### Entorno

- Radio efectivo visual = radio del perfil × cobertura × clima × iluminación ×
  firma/exposición. Aplicar además límites duros de LOS, AGL y sensor.
- Tabla de cobertura solicitada: desierto > pradera > tundra > bosque > ciudad.
  Son parámetros de balance, no constantes físicas universales.
- El proveedor de cobertura acepta zonas/polígonos y perfiles del teatro. Se puede
  estimar ciudad con densidad de scenery local cacheada; bosque solo con datos
  verificables. Si falta información, usar «desconocido» y mostrar el fallback en
  debug, no clasificar todo Iraq como desierto ni toda Europa como bosque.
- Comenzar con zonas de prueba conocidas para calibración. La cobertura automática
  detallada de todos los mapas puede requerir un conjunto de datos posterior.
- Nubes: base/espesor/preset, diferenciar capa opaca de cobertura fragmentada.
  El usuario observa que el FLIR del F-18 en DCS atraviesa muchas nubes salvo capas
  muy densas/espesas. No imponer bloqueo universal a IR: medir IA por separado,
  distinguir visual/EO/IR y usar penalizaciones aproximadas acordes a lo observado.
  Sin consulta volumétrica, no afirmar que se conoce cada intersección con una nube.
- Visibilidad, niebla, precipitación y polvo reducen adquisición visual/IR; radar
  tiene factores propios. Revisar niebla dinámica y presets externos.
- Luz a partir de fecha, latitud y hora de misión, con transiciones graduales; no
  mantener «amanecer» durante dos horas ni reutilizar franjas redondeadas de campaña.
- Factores adicionales propuestos: tamaño (infante/camión/tanque), movimiento,
  tiempo expuesto, parada bajo cubierta y velocidad/carga de trabajo del observador.
- Pod/térmica mitiga la noche, no da detección perfecta ni elimina ocultación.
- Incorporar adquisición gradual/tiempo mínimo de observación. Si hay probabilidad,
  hacerla dependiente del tiempo transcurrido y usar PRNG propio, sin alterar el
  math.random global de los otros plugins ni depender de FPS o frecuencia del tick.

Valores concretos distintos de 5 NM/600 s: ajustarlos con las misiones de aceptación,
no presentar alcances inventados como datos oficiales de cada sensor.

### Otros métodos propuestos

- Informes de tropas en contacto: derivan del modelo terrestre, no de escanear toda
  la coalición enemiga. Muy útiles para CAS sin un dron encima de cada tanque.
- Emisores radar: RWR/ESM como pista de búsqueda de SAM/EWR activos, con incertidumbre;
  no convertir un solo rumbo RWR en coordenadas perfectas de toda la batería.
- ISR dedicado GMTI/SAR: perfiles explícitos para plataformas del tipo JSTARS si
  están disponibles en la campaña/mods. La USAF documenta esa función del E-8C;
  no concedérsela automáticamente a E-3/A-50/EWR por su rol de alerta aérea.
- Radar terrestre de vigilancia y contrabatería: extensiones solo para unidades
  equipadas con ello. La contrabatería no añade mucho mientras todo disparo revele
  automáticamente, por lo que no es prioritaria en V1.
- Informe humano mediante menú/marcador validado: transmitir una posición indicada,
  no resolver secretamente la unidad más cercana fuera de su capacidad de observación.
  Propuesto para más adelante; el jugador puede detectar y atacar visualmente sin
  que el plugin interfiera con sus armas.
- Humo/iluminación/destellos pueden dar pistas, no conocimiento exacto universal.

## 6. JTAC vulnerables y coherentes

- Quitar las protecciones artificiales del generador SOLO con Realistic CAS activo.
  MOOSE debe respetar la misma decisión en sus defaults y al sustituir órbitas.
- Perfiles propios para MQ-9 y Kiowa: altitud, velocidad y órbita razonables; no
  colocar a un helicóptero automáticamente en la órbita de un dron a 5.000 m.
  Tampoco dar por válida identificación a 5.000 m para el dron: comparar detección
  nativa a 2.000/5.000 m y calibrar el modelo sin confundir contacto con identificación.
- Registro por nombres/IDs exportados, no limitado a los nombres Alpha/Bravo.
  Usar el mismo adaptador para JTAC que existan en cualquier coalición; crear
  automáticamente JTAC rojos que hoy no existen es una decisión separada.
- Adaptador MOOSE por instancia: filtrar candidatos antes del lase y durante el
  seguimiento; desactivar vías de conocimiento omnisciente cuando corresponda.
  No modificar el gran bundle de MOOSE por una personalización local.
- FAC nativo: conservar radio/callsign/código si el filtrado funciona; si no,
  alternativa script documentada antes de sustituir la interacción del jugador.
- Muerto el JTAC, cesan informes y láser. Desvelado por otro sensor no significa
  que este JTAC pueda apuntarle. Coordinar tiempos de reacquisición/cambio de blanco.
- V1: vulnerabilidad dentro de la misión. Economía/recompra/persistencia de los JTAC
  generados gratuitamente requiere decisión aparte; no inventar débitos de campaña.

## 7. F10: fuera de alcance (decisión tras pruebas)

No implementar ocultación ni sustitución de iconos. El mapa conserva su comportamiento
normal; las propuestas siguientes son solo historial de diseño, NO requisitos activos.

Primera elección: usar capacidad nativa si las pruebas demuestran control adecuado
en tiempo de misión y por coalición. No depender de una API de ocultación no comprobada.

Alternativa: ocultar los iconos terrestres nativos desde la generación y dibujar
marcadores propios por coalición. Mostrar última posición observada, edad, fuente
y estado; no arrastrar el marcador con la posición verdadera de una unidad perdida.

- Si el flag también oculta fuerzas propias, restaurar su representación con
  marcadores propios y explicar que no serán iconos nativos interactivos.
- No cambiar el setting global de F10: aire y mar conservan su configuración.
- No mostrar contactos mediante debug al adversario en MP; el modo administrador
  es explícito. Probar espectadores y clientes que entran tarde.
- Comprobar posibles filtraciones de TSD/datalink, etiquetas y vistas externas,
  pero no prometer que un Mission Plugin pueda convertirlas en una barrera completa.
- Si F10 está deshabilitado por el servidor, no reabrirlo desde el plugin.
- Nunca destruir/recrear una unidad para refrescar hidden: alteraría IDs, salud,
  munición, rutas, Skynet y debriefing.

## 8. Arquitectura e integración previstas

- `resources/plugins/realisticcas/`: plugin.json y Lua separados para núcleo,
  sensores, backend DCS y adaptadores; cada fichero sintácticamente independiente.
- `game/missiongenerator/realisticcasluadata.py`: exportar configuración, coalición,
  unidades/IDs reales, roles, equipos/payloads, zonas de búsqueda, tiempos, JTAC,
  entorno y contactos iniciales. No parsear nombres de vuelos.
- Añadir llamada en LuaGenerator y registro en plugins.json. Cargar núcleo antes de
  consumidores MOOSE/TIC, y registrar entidades tardías después de su nacimiento.
- Datos de sensores/cobertura en un esquema pequeño y validado; evitar duplicación
  entre Python y Lua. Respetar números/booleanos al serializar: LuaData existente
  convierte muchas entradas a strings y tiene particularidades con arrays/nodos.
- Cambios condicionales en CAS/BAI/Armed Recon solo si el backend los exige.
- API interna propuesta: observe, getContact, isRevealed, canEngage, canLase,
  registerObserver, registerTarget y getDiagnostics. Los consumidores acceden al
  conocimiento autorizado, no a la tabla interna de posiciones verdaderas.
- TIC: un único dueño del estado de ocultación y un adaptador para clones, listas de
  objetivos y fuego. No permitir que su tracker de 2 NM se salte el nuevo modelo.
- Skynet sigue controlando radar/defensa aérea; Realistic CAS no cambia emisiones,
  inmunidad ni reglas de evasión. Preservar lógica de HARM/SEAD, reacción al ataque,
  transportes, capturas y contabilización de pérdidas.
- API LLM: exponer configuración efectiva, capacidades y advertencias de planificación
  que también ve el humano. No inventar una conexión en vivo misión→app: diagnósticos
  por log/debrief cuando corresponda. Lectura de settings, no nuevo permiso de editarlos.

## 9. Opciones, rendimiento y diagnóstico

Opciones iniciales: activar plugin (off por defecto), memoria
(10 min), radios visual aéreo/terrestre y escalas de radar, límite AGL por perfil,
intervalo de exploración y debug (off). Satélites no incluidos en la primera UI.
No ofrecer controles que aparenten funcionar si el backend no soporta su efecto.

Implementación deliberadamente aproximada: multiplicadores de tablas, cobertura por
celda/zona, iluminación actualizada con poca frecuencia y cono geométrico sencillo.
Sin ray tracing óptico, barridos volumétricos de nubes, consultas de scenery por pareja
ni sondeo de cada proyectil. Los detalles físicos son condiciones de diseño, no una
invitación a simularlos individualmente. Empezar con detección reproducible por tiempo
de exposición; añadir aleatoriedad solo si mejora de forma demostrable el resultado.

- Registro inicial una vez + eventos de alta/baja. Índice espacial por celdas;
  actualizar móviles y consultar vecindarios, no todas las parejas del mapa.
- Un planificador reparte observadores en lotes. Primer objetivo: revisita de 5 s
  por observador y eventos de fuego procesados sin un barrido global. Medir y ajustar.
- Rechazar por bando, alcance al cuadrado y sector antes de LOS/clima más caros.
- Cachés de capacidades por tipo/carga, cobertura por celda y posiciones por lote;
  invalidación por movimiento/muerte/cambio real, no vaciar todo cada ciclo.
- Banderas de visibilidad, tareas, marcas y mensajes solo al cambiar estado.
- Presupuesto explícito de operaciones/LOS por tick; bajo carga aplazar trabajo,
  nunca ampliar gratis los radios ni desvelar todo. Acotar colas/contactos caducados.
- Debug: motivo de detección/rechazo, distancia, AGL, LOS, perfil/fallback de terreno,
  clima/luz, fuente, TTL, tarea autorizada y discrepancias con detección nativa.
- Contadores de candidatos, LOS, cambios de tarea, contactos y tamaño de colas.
  Mensajes/resúmenes limitados; detalle seleccionable por grupo, no spam por unidad.
- Fallos: proteger callbacks, aislar adaptador fallido y registrar aviso visible.
  Política explícita de recuperación: restaurar solo estados que controlaba el plugin
  y el comportamiento estándar si se desactiva, sin quitar invisibilidad ajena.

## 10. Entrega y aceptación

1. Acordar este plan y cerrar inteligencia previa/granularidad tras fase cero (cerrado).
2. Añadir harness Lua 5.1 y misiones de capacidad; ejecutar las de motor con el usuario.
3. Núcleo, exportación, revelado por fuego, memoria y backend validado.
4. Detección terrestre y visual aérea; perfiles IR, radar y entorno.
5. JTAC nativo/MOOSE, TIC, oleadas tardías y compatibilidad de campañas.
6. Debug y documentación de límites en README/howtoplay/API. Sin ocultación F10.
7. Calibración en misiones cortas y campaña grande; PR revisable con evidencias.

Pruebas automatizadas: compilar CADA Lua y el conjunto; tests puros de estados,
coaliciones, TTL, movimiento, fronteras de cono, unidades metros/NM/ft, medianoche,
equipamiento ausente, desconocidos, muerte y alta tardía. Integración Python: plugin
off conserva salida, exportación exacta de roles/payloads/IDs, orden de carga, JTAC
vulnerables solo cuando procede y ausencia de modificaciones involuntarias del ATO.

Aceptación DCS: ocultos no reciben nuevos ataques; el tirador exacto se revela;
caducidad/reacquisición funcionan; no se revela el resto de un grupo por accidente;
los tanques detectan y combaten; sensores no ven a través de obstáculos del modelo;
un radar exclusivamente aire-aire no descubre tanques por radar (sí puede hacerlo
la visión/óptica de la plataforma); JTAC muerto deja de informar/iluminar;
CAS sin contactos busca y sale a su hora; F10 conserva su funcionamiento; aviones/SAM
conservan defensa propia; no se pierden unidades ni se rompe el debrief.

Rendimiento: escenarios de 100/500/1.000 terrestres y 5/20/50 observadores, con y sin
plugin, mismos ajustes/semilla. Medir coste Lua/operaciones en harness y frametime/
tiempo de simulación en DCS; sin crecimiento indefinido durante una misión larga.
No dar por acreditado el rendimiento por pasar tests con dobles de DCS.

## 11. Iteración 2: satélites

Capacidad por bando y época de campaña. Pasadas/cadencia, límite de unidades o zonas
observadas por pasada, prioridad de búsqueda y latencia de entrega. Emitir observaciones
con la hora de captura, no con la hora de recepción, para no rejuvenecer información.
Separar ópticos (luz/nubes) y SAR (otras restricciones). Sin cobertura permanente ni
seguimiento de cada tanque; reutilizar contactos, TTL, debug y F10 existentes.
Si se abstraen sin órbitas reales, declararlo. Disponibilidad/coste/edición de esa
capacidad y persistencia entre turnos se diseñarán en esa iteración.

## 12. Revisión específica de Troops in Contact

Archivo: `resources/plugins/tic/TIC_v1.1.lua`, versión 1.1, licencia MIT de Grendel.
Si se reutiliza código, conservar aviso de copyright/licencia. El plugin nuevo no
debe requerir activar TIC: tomar patrones pequeños y ofrecer adaptador opcional.

### Piezas útiles

- **Ventanas de exposición** (Cloak/Decloak, aproximadamente líneas 1708–1805):
  acumula inicio/fin con min/max y aplica SetCommandInvisible al cambiar estado.
  Es una referencia concreta para TTL renovable sin generar un temporizador por
  cada nueva detección. Adaptar a reloj único y origen de observación.
- **Spotter** (GLSCO_SPOTTER, ~3914–4000): observador con intervalo, radio,
  duración y probabilidad; filtra coalición, distancia y LOS, y desvela con un
  pequeño retraso. Buen esqueleto conceptual para añadir perfiles y entorno.
  No se ha localizado activación de estos spotters en el puente actual de
  Retribution: su existencia no significa que la campaña ya esté usándolos.
- **Tracker** (GLSCO_TRACKER:broadcast, ~4178–4260): elimina muertos, obtiene
  coordenadas una vez, descarta por alcance antes del LOS y entrega los diez
  blancos más próximos. Reutilizar ese orden de filtros y la idea de listas
  limitadas, no el bucle completo rojo×azul de coste cuadrático.
- **Distribución de trabajo**: TIC separa sus actualizaciones temporalmente con
  intervalos variables. Aplicar el mismo principio mediante lotes acotados y
  revisitas escalonadas, con un planificador central más fácil de medir.

### Lo que no se debe copiar tal cual

- El spotter recorre todas las formaciones/combatientes por observador, usa
  distancia 2D, probabilidad fija por sondeo y no considera ópticas, hora, nubes
  o terreno. Sustituir búsqueda global por índice espacial; la probabilidad no
  debe aumentar porque subamos la frecuencia de actualización.
- El tracker usa 2 NM y posiciones verdaderas para todos, y su LOS compartido
  añade blancos a ambas listas. En Realistic CAS la geometría puede reutilizarse,
  pero la detección no es simétrica si uno tiene térmica y el otro no.
- `decloakRandomTarget` puede desvelar directamente al blanco elegido en modo
  letal; debe pasar por la autorización del servicio y no convertirse en una
  puerta trasera para descubrir unidades.
- El modo StormTrooper utiliza invisibilidad + fuego a coordenadas para reducir
  letalidad. El adaptador debe conservar ese modo de fuego: quitar invisibilidad
  sin más puede cambiar la precisión, no solo el conocimiento.
- `tic_414_init.lua` permite fuego ambiental sin LOS hacia posiciones enemigas
  reales. Con Realistic CAS no debe consultar unidades UNKNOWN como si fueran
  conocidas: usar una zona de supresión/último informe, no su posición secreta.
  El tirador sí queda desvelado cuando efectivamente dispara, como pidió el usuario.
- TIC usa líderes auxiliares invisibles/inmortales y respawns de combatientes.
  No revelar auxiliares ni retirar esas protecciones internas. Registrar únicamente
  combatientes reales y preservar la correspondencia con UnitMap/debrief.

### Compatibilidad prevista

TIC conserva movimiento, salvas y su máquina de estados. Realistic CAS aporta
percepción, contactos autorizados y arbitraje de ocultación de combatientes reales.
Con el nuevo plugin apagado, TIC conserva su funcionamiento sin modificaciones de
comportamiento. Probar la matriz TIC off / normal / StormTrooper, cada una con
Realistic CAS on/off. Si un modo no puede coexistir fielmente, advertir y restringir
esa combinación hasta resolverlo, no ofrecer una casilla que se pelea cada tick.
