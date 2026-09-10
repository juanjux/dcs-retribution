# Prueba 36 — atenuación de nubes

Log archivado: `Saved Games/DCS/realistic-cas-test-results/clouds-36/dcs.log`.
Sesión 2026-09-09 17:26:30–17:26:46: **0 fallos, 0 inconclusos, 13 controles**.

Un A-10 con pod y un camión. Pose, vuelo y LOS del motor; transmisión de la capa
1500–3500m MSL controlada por el ensayo, sin cambiar la meteorología nativa.

| Fase | Canal/resultado | Muestras de contacto | Ventanas geométricas |
| --- | --- | ---: | ---: |
| Transparente | EO | 18 | 12 |
| Visual bloqueada, IR 0,85 | IR | 17 | 12 |
| Visual e IR bloqueados | Contacto caducado y oculto | 0 esperado | 12 |
| Recuperación transparente | EO | 16 | 12 |

Las muestras de contacto pueden superar las ventanas conservadoras: el contacto
persiste durante su TTL y el filtro independiente del arnés usa más margen que
el detector. No son conteos de objetivos distintos ni de disparos.

Sin errores de callbacks; visibilidad restaurada al terminar a los 490s.
Esto verifica la aplicación de las reglas de atenuación al puente DCS, no la
física nativa de transmisión IR ni la equivalencia entre presets y densidad real.

Siguiente: 37, RBM/GMTI con radar encendido y velocidades reales de DCS,
controles estáticos y restricción por rol CAS/BAI/Armed Recon.
