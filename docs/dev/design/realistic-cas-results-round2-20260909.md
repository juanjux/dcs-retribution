# Realistic CAS — segunda tanda in-engine, 2026-09-09

Usuario ejecutó 20–30 con aceleración solicitada 200x, sin anomalías visuales
reportadas. No se ha medido el factor de aceleración real ni se deduce rendimiento
del plugin a partir de este dato.

Fuente preservada: `C:/Users/juanj/Saved Games/DCS/Missions/realistic_cas_tanda2/results-20260909/dcs.log`.
Las once ejecuciones alcanzan su estado final previsto, sin INVALID y sin errores
RCAS_TEST. El fichero incluye también pruebas de la primera tanda: separar por nombre.
Los eventos siguen registrándose después de FIN aunque se congelen los contadores
del experimento; no confundir total del log con total durante la ventana de medición.

## 1. La granularidad efectiva observada es el grupo

| Prueba | Ventana experimental | Detección / fuego |
| --- | --- | --- |
| 20 control | 32–212 s; abre fuego a 62 s | Ambos visibles; cañón contra tanque y ametralladora/HE contra camión |
| 21 SetInvisible al controlador del tanque | 30–210 s; abre fuego a 60 s | AMBOS dejan de detectarse; ningún disparo/ráfaga en la ventana |
| 22 SetInvisible al grupo | 32–212 s; abre fuego a 62 s | AMBOS dejan de detectarse; ningún disparo/ráfaga en la ventana |

En 21/22 los dos sujetos habían sido adquiridos antes del cambio, conservan LOS,
y ambos reaparecen y reciben fuego después de restaurar. Son controles positivos
iniciales y finales, a diferencia de la primera tanda.

21: las 36 muestras de la ventana dan ALL=false para cada sujeto. 22: una muestra
en el límite inicial conserva detección, las 35 siguientes no. No exigir sincronía
inmediata exacta de detección con la llamada del script.

Consecuencia: en esta composición de grupo terrestre, usar Unit:getController()
NO consigue aislar al tanque de su compañero. No concluir que todas las categorías
de DCS tengan exactamente el mismo comportamiento, pero tampoco diseñar la V1
prometiendo revelado por vehículo con este backend.

Decisión de producto pendiente: aceptar exposición del grupo lógico cuando se
desvele alguno de sus integrantes, o desarrollar otra solución. Dividir grupos
no es una transformación inocua para baterías SAM, convoyes, órdenes y debrief.
Mantener un estado interno por unidad no evita que DCS exponga a sus compañeros.

## 2. La ocultación no ofrece memoria nativa utilizable en esta prueba

23 y 24: adquisición estable confirmada a 14 s; cambio a 29 s; orden de movimiento
a 39 s; destino lateral alcanzado, desplazamiento final 248 m; LOS se conserva.
Restauración a 209 s, final a 289 s.

- Control: continúa detectado/visible durante el movimiento.
- Oculto: ALL=false, visible/lastTime/lastPos/lastVel=nil durante la ventana.
- Al mostrar, recupera contacto (falso aún en muestra a 217 s, verdadero a 252 s).
- Mientras hay contacto visible, lastPos/lastTime pueden ser nil: no son la posición
  actual, que debe leerse del objeto solo cuando la observación esté autorizada.

No hay posición falsa/antigua que el script pueda imponer a la IA con lo ensayado.
Usar la aproximación temporal prevista y conservar snapshots propios para lógica
de búsqueda/debug. No actualizar snapshots internos con la posición secreta actual
de un blanco perdido. F10 queda fuera de alcance.

## 3. Ocultación bloquea ataques incluso después de adquirir/asignar por ID

| Prueba | Resultado de misiles Kh-29T |
| --- | --- |
| 25 CAS control | 220,2 / 231,6 / 332,2 / 333,4 s: cuatro lanzamientos |
| 26 CAS revocada | Primer tiro 196,6; oculta a 197 con tres restantes; cero nuevos hasta restaurar a 437 |
| 27 CAS siempre oculta | Cero lanzamientos durante 720 s; cuatro misiles restantes |
| 28 AttackUnit control | 46,2 y 50,7 s: uno de cada avión, ambos a BLANCOS-1 |
| 29 AttackUnit revocada | Primer tiro 46,2; oculta a 47 con tres restantes; no hay segundo misil durante ocultación |
| 30 AttackUnit siempre oculta | Cero lanzamientos durante 720 s; cuatro misiles restantes |

Un ID asignado no ha sorteado SetInvisible en esta versión/escenario. En 29 incluso
se inhibe el lanzamiento del punta que sí ocurrió a 50,7 s en el control idéntico.
No se cancelaron tareas ni se destruyeron armas desde el script.

Los impactos del primer misil pueden ocurrir tras ocultar. No constituyen tiros
nuevos y no se deben impedir artificialmente en el plugin.

## 4. Desvelar no garantiza un ataque inmediato ni reactivación de una tarea terminada

26 restaura a 437 s, termina el resumen a 617 s sin tiros nuevos, pero el log de
eventos registra nuevos Kh-29T a **618,0 y 620,5 s**, y ráfaga a 646,7 s. CAS sí
reanuda sin reemitir tarea, después de unos 181–184 s. Leer solo el resumen final
habría producido la conclusión errónea de que no reanuda.

29 no registra nuevos misiles después de restaurar a 287 s en el tiempo observado.
Esto no demuestra que AttackUnit nunca pueda reanudar: el propio control tampoco
agota su munición (solo un misil por avión). Puede ser necesario reconstruir una
tarea concreta si se descartó/finalizó, pero no sustituirla repetidamente sin
comprobar su ciclo de vida. Esa integración queda pendiente del prototipo.

## 5. Siguiente decisión / implementación propuesta (no ejecutada)

1. Acordar el compromiso de granularidad por grupo, explícitamente.
2. Con ese acuerdo, núcleo de contactos/TTL propios y SetInvisible por grupo.
   Los sensores propios gobiernan descubrimiento: no esperar que la IA nativa
   descubra por sí sola un objeto que el script le ha ocultado.
3. Revelado por SHOT/SHOOTING_START y perfiles geométricos de observación.
4. Gestionar reanudación de CAS y tareas directas en un prototipo pequeño, sin
   confundir tiempos de maniobra con falta de conocimiento ni reemitir cada tick.
5. Validación posterior específica de tareas reales del generador, SAM, TIC y
   debrief; estas once pruebas no acreditan aún esa compatibilidad.

No se ha modificado código de campaña ni generado otra tanda como parte del análisis.
