# Prueba 35 — noche e IR

Log archivado en `Saved Games/DCS/realistic-cas-test-results/night-35/dcs.log`.
Sesión 2026-09-09 16:45:12–16:45:27: **0 fallos, 0 inconclusos, 11 controles**.

Misma pareja Abrams–Ural, 2.000,18m, LOS verdadera durante el ensayo:

- 50s: visual con iluminación diurna modelada e IR deshabilitado.
- 95s: oculto tras pasar a noche sin IR; contacto anterior caducado.
- 145s: contacto por canal `ir` con capacidad térmica habilitada.
- 190s: oculto tras retirar IR; la caducidad se observa ya a los 160s.
- 235s: contacto `visual` recuperado al volver al día modelado.
- Sin errores de callbacks; visibilidad restaurada al terminar.

DCS permanece a las 23:00. La iluminación y capacidad IR que cambian son entradas
del modelo, no interruptores físicos ni cambios de hora del motor. Valida el
ciclo completo del plugin y su puente DCS, no alcances térmicos reales ni la
detección nocturna nativa del Abrams. La duración real fue 235s desde el inicio
del script, unos 238s de misión (ligeramente más que los 233s anunciados).

Siguiente ensayo: 36, atenuación de nubes modelada con un A-10 con pod volando,
sin radar de tierra; comprobar EO/IR/bloqueo/recuperación con pose y LOS reales.
