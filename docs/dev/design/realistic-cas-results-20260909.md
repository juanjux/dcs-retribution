# Realistic CAS — resultados in-engine, 2026-09-09

Fuente: observaciones del usuario y trazas reales RCAS_TEST de las 14 misiones.
Copia preservada en `C:/Users/juanj/Saved Games/DCS/Missions/realistic_cas_diagnostico/results-20260909/dcs.log`.
No se han modificado las misiones ya ejecutadas ni implementado el plugin.

## Conclusiones utilizables

- Control CAS positivo: X_29T de CAS-2 a 219,5 s y CAS-1 a 234,8 s.
- AttackUnit y EngageUnit dirigieron los cuatro X_29T de cada ensayo exclusivamente
  a TARGET-1, incluyendo ambos miembros del vuelo. Buena evidencia para selección
  unitaria; no demuestra todavía revocación de blancos previamente adquiridos.
- En 06 el grupo oculto no fue detectado antes de desvelar a 241 s. El observador
  adquirió sus carros a 271/311 s. El control visible los adquirió a 61/81 s.
  Esto respalda ocultación de grupo, no resuelve control individual.
- Un tirador oculto puede disparar: 08 contiene 17 SHOT de M256_120_HE, seis de
  SA9M33 y seis de M185_155. M113 y Shilka dispararon sin SHOT de sus ráfagas.
  SHOOTING_START sí está presente: 56 ráfagas M113 y 23 Shilka. Las 169 del Abrams
  en todo el registro incluyen tiempo posterior al resumen final (118 hasta FIN).
  La regla de revelado requiere SHOT + SHOOTING_START, con deduplicación/renovación
  controlada. No probar TIC por extrapolación: aquí TIC no estaba cargado.
- MQ-9 vulnerable: en dos ejecuciones de 12, Osa sin detección en todas las muestras
  anteriores a quitar invisibilidad; primer contacto a 221 s, misil a 250,7/250,8 s,
  impacto alrededor de 259,5 s y pérdida del dron a 278,9/280,1 s. No hay evidencia
  de tracking previo en las muestras, aunque el movimiento visual del radar pudo
  parecerlo. No demuestra el protocolo completo de radio FAC.

## CAS: limitaciones de los ensayos temporales

La ventana inicial oculta de 180 s acaba ANTES del primer ataque del control
(219,5 s). Por tanto, ausencia de tiro en esa ventana no prueba que SetInvisible
bloquee AttackGroup, AttackUnit, EngageUnit ni knowTarget.

| Ensayo | Lanzamientos X_29T registrados (s) | Blanco |
| --- | --- | --- |
| 00 CAS visible | 219,5 / 234,8 | 1 / 6 |
| 01 CAS oculto | 699,5 / 713,8 / 817,8 / 823,2 | 2 / 1 / 4 / 3 |
| 02 AttackGroup | 231,0 / 297,4 / 340,9 | 6 / 5 / 3 |
| 03 AttackUnit | 231,6 / 231,8 / 301,2 / 332,3 | siempre 1 |
| 04 EngageUnit | 227,5 / 232,2 / 311,0 / 352,0 | siempre 1 |
| 05 knowTarget + CAS | 706,0 / 706,1 | 5 / 4 |

Todos esos tiros se producen en fases visibles. En 03/04 ya habían gastado los cuatro
misiles antes de reocultar a 361 s: no sirven para verificar revocación de misiles
posteriores. El “siguen atacando” observado no debe confundirse con disparos a blancos
ocultos. En 01/05 el retraso es parecido y compatible con una ventana de búsqueda/
maniobra perdida, pero no identifica por sí solo el mecanismo causal.

Próximo diseño: control y variante idénticos; ocultación que dure al menos una
ventana completa de ataque válida; caducidad disparada por primera adquisición o
primer lanzamiento, con munición suficiente restante. No mezclar revelar, reemitir
tarea y caducar a tiempo fijo y luego atribuir todo a una sola causa.

## 06 y 07 necesitan rediseño, no interpretación optimista

06: cero gasto de munición en TODOS los Abrams observadores, incluido el control.
La calle GROUP_HIDE_UNIT1_SHOW tiene LOS=false. UNIT1_HIDE no adquiere ninguno ni
tras las órdenes finales de mostrar. No hay control positivo final en esas calles,
así que no permite concluir si SetInvisible por unidad oculta a sus compañeros.
Revisar ROE: el generador usa el literal 0 para apertura terrestre, pese a empezar
en HOLD; usar y registrar AI.Option.Ground.val.ROE.OPEN_FIRE, no trasladar el enum
aire-aire ni asumir que ausencia de excepción implica que se obedeció.

07: ninguna muestra de adquisición, ni antes ni después de ocultar. El camión se
desplazó 2.519 m; al alejarse perdió también LOS geométrica. No hay memoria previa
que medir. El círculo en la posición inicial procede de markToAll del propio test,
no de memoria espontánea de DCS. lastPos estaba solo en el log y fue nil.

Próximos ensayos: calles sobre geometría con control positivo, orientación explícita,
blancos visualmente diferenciables y mismas composiciones entre control/variante;
contador legible por blanco. No empezar ocultación/movimiento hasta adquirir, o
terminar como INVALID tras un timeout. Mostrar última posición y desplazamiento
en pantalla, no pedir al usuario que observe un valor que solo está en dcs.log.

## Sensores: el log distingue cosas que la pantalla resumida no mostraba

Distancias siguientes: metros oblicuos al primer contacto muestreado, no máximos
calibrados. Frecuencia de muestra 10 s, geometría variable, detección no equivale
necesariamente a identificación ni a visibilidad actual.

| Caso | Evidencia real de los filtros de detección |
| --- | --- |
| Día | Hornet con pod y A-10 por OPTIC a 14,5–14,7 km; Hornet sin pod por RADAR al estático a 8,7 km; MQ-9 por OPTIC/RADAR desde primeras muestras |
| Nubes | MQ-9 por RADAR a 15,1/15,8 km; Hornets por RADAR, móviles a 13,2 km y estáticos a 8,7 km; Kiowa bajo capa por OPTIC a 12,9 km; A-10 sin detección |
| Noche | A-10/Hornet con pod por OPTIC desde ~14,5 km; Hornet sin pod por RADAR; Kiowa estático por OPTIC a 9,4 km; MQ-9 primero RADAR, después también OPTIC |

No hay detección F-15C en estas trayectorias: NO se concluye que carezca de detección
visual de vehículos a baja altura/corta distancia. El modelo tendrá visual común,
y radar de superficie solo para quien tenga esa capacidad.

Kiowa: getSensors declara TVS y TIS, con opticType 0 y 2, y detecta por OPTIC, no
VISUAL en este test. No es evidencia de visión nocturna a ojo desnudo a nueve km.
MQ-9: declara cámara, FLIR y SAR. Su detección detrás de nubes no acredita FLIR
atravesándolas: en ese ensayo el canal positivo fue RADAR.

Hallazgo para exportación: getSensors del Hornet CON pod enumera APG-73/RWR, pero
NO el ATFLIR; el A-10 CON pod solo enumera RWR, pese a que ambos detectan por OPTIC.
Es imprescindible combinar descriptores con payload/equipo integrado. Los valores
RBM/HRM publicados tampoco equivalen directamente a los alcances observados aquí.

AGL: las condiciones iniciales/ruta usan RADIO; Orbit utiliza altitud BARO de
referencia+200 m. Los nombres de perfiles no garantizan AGL constante. Utilizar las
alturas reales registradas. En siguientes ensayos explicitar MSL/AGL en pantalla.

## Instrumentación

Cero errores Lua registrados. Eso NO acredita corrección semántica de sus etiquetas.
Se encontró un error de orden de retornos en samplePair y en el doble de prueba:
el orden usado por el wrapper MOOSE y compatible con las trazas reales es
detected, visible, knowType, knowDistance, lastTime, lastPos, lastVel.
El arnés etiquetó posiciones 3/4/5 como lastTime/type/distance. Por eso aparecía
last=true y dist=una hora de simulación. Posiciones 1, 2, 6 y 7 no están desplazadas.
Corregir antes de nueva tanda y conservar retornos crudos con sus tipos para no
volver a hacer que un mock confirme la misma suposición equivocada del logger.

## Alcance actualizado

Por decisión explícita del usuario, ocultación F10 fuera de alcance. No más matriz
de roles/mapa ni sustitución de iconos. Conservar mapa y settings normales. Las siete
capturas son evidencia histórica, no un requisito que bloquee implementación.

No está autorizado por estos resultados un salto a implementar toda la feature.
Siguiente trabajo propuesto: corregir arnés y preparar solo pruebas reducidas de
granularidad, memoria tras adquisición y caducidad con munición restante.
