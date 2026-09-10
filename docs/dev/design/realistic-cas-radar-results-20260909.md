# Prueba 37 — RBM/GMTI y roles

Log archivado: `Saved Games/DCS/realistic-cas-test-results/radar-37/dcs.log`.
Sesión 2026-09-09 17:51:34–17:51:56: **0 fallos, 0 inconclusos, 36 controles**.

- CAS: el camión lejano móvil produce contactos `gmti` (10 muestras); el cercano
  estático, `rbm` (10). El lejano estático permanece oculto.
- STRIKE en los metadatos: todos ocultos, con contactos anteriores caducados.
- CAS sin capacidad GMTI: lejano móvil oculto, cercano estático detectado por RBM.
- BAI y Armed Recon: recuperan GMTI para móvil lejano y RBM para estático cercano.
- Siete oportunidades geométricas conservadoras para cada positivo de radar
  informado. Velocidades/pose/LOS y encendido de radar proceden de DCS.
- Sin errores de callbacks; visibilidad restaurada al terminar a los 610s.

Los roles y la capacidad GMTI que cambian son metadatos del plugin, no la tarea
nativa o el modo real del radar. Se prueba el uso del booleano de encendido y la
velocidad nativa, no una API de barrido/modo GMTI inexistente en este puente.

Con esto se cierra la matriz aislada de sensores 32–37. Continúa la integración
de campaña, no otra repetición de estos controles. Se añadió el colector de
registro de misión con pruebas pydcs reales de nombres, coaliciones, roles,
cargas por aparato, propiedad de visibilidad y serialización Lua tipada. Aún no
se habilita el plugin en campañas ni se considera validada su coexistencia con
TIC/JTAC/MOOSE o su rendimiento en una campaña completa.
