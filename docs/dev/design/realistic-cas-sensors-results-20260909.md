# Primera prueba del puente sensor — 2026-09-09

Misión 32, completada por el usuario: 2 fallos. Log preservado fuera de Missions,
en `Saved Games/DCS/realistic-cas-test-results/sensors-20260909/dcs.log`.

## Resultados acreditados

- Fallan únicamente los contactos positivos terrestres NEAR_0 (visual T-72B,
  2 km) y NEAR_1 (térmica Abrams, 4 km): nunca se desvelan.
- Primer contacto Hornet registrado en muestreo a 40s, motivo `rbm:RADAR_F18-1`.
  getRadar devuelve true. Esto acredita que el puente habilita su modelo RBM,
  no que se esté leyendo el modo real del radar ni su detección nativa del blanco.
- Primer contacto A-10 a 45s, motivo `eo:POD_A10-1`. No valida el canal IR aislado.
- Primer contacto F-15C a 60s, motivo `visual:VISUAL_F15-1`.
- Todos los contactos caducan tras parar sensores; el propietario restaura visibilidad.
- Sin errores de callbacks ni de backend. 300 barridos, 345 candidatos, 177
  comprobaciones de LOS, 77 observaciones aceptadas, 9522 pasos de búsqueda.

## Diagnóstico y límites

La falta de LOS es la hipótesis principal para los casos terrestres. Antes de que
los aviones puedan adquirir, cada vuelta de seis observadores ejecuta dos pruebas
de LOS sin producir revelados. Al final hay 100 comprobaciones de LOS adicionales
a las 77 observaciones aceptadas, compatibles con 50 revisitas por cada caso
terrestre positivo. Todos los grupos objetivo están registrados, sin errores.

No se registró qué pareja fue rechazada por LOS ni su perfil de terreno; por tanto
no se atribuye definitivamente al relieve sin más instrumentación. Elegir puntos
separados 2/4 km no garantiza una línea despejada a altura de tanque. También hay
que contrastar alturas de los extremos, no asumir que son correctas por el PASS Lua.

Los controles lejanos y de cobertura ciudad se mantuvieron ocultos, pero no prueban
sus filtros específicos si tampoco tenían LOS. Próximo ensayo: solo tierra,
precondiciones de LOS verificadas y registradas por pareja, con motivos de rechazo,
coordenadas/alturas y controles positivos comparables. No quitar el filtro de
relieve ni ampliar alcances para hacer pasar una prueba geométricamente inválida.
