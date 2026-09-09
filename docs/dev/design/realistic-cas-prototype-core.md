# Realistic CAS — primer núcleo (2026-09-09)

## Alcance implementado

Biblioteca Lua 5.1 en `resources/plugins/realisticcas`, sin registrar todavía como
plugin seleccionable ni modificar misiones de campaña. Sigue la decisión del
usuario: descubrir un miembro desvela su grupo completo; F10 queda fuera.

- Contactos simétricos para azul/rojo; neutros excluidos.
- Revelado al disparar mediante SHOT y SHOOTING_START; observaciones explícitas.
- TTL por defecto 600 segundos, renovable; copia de última posición observada.
- Una entrada por grupo en una cola de expiración indexada, trabajo limitado por
  tick y sin generar un temporizador por disparo. El atraso de ocultación física
  bajo carga se distingue de la expiración lógica y requiere medición en campaña.
- Registro exclusivamente por lista autorizada, con declaración explícita de que
  la invisibilidad original era falsa. No interfiere automáticamente con TIC.
- Restauración al apagar, reintentos de expiración, errores y cambios registrados.
- Protección frente a carga duplicada, nacimientos tardíos y sustitución de nombre
  por otro ID. El cierre parcialmente fallido no vuelve a registrar lo restaurado.

## Verificación y siguiente prueba

`tools/realistic_cas_tests/test_contact_core.py`: pruebas Lua 5.1 con dobles,
incluyendo 12.000 operaciones aleatorias contra un modelo de referencia, 10.000
renovaciones de un contacto, errores de backend, temporizador y cierre.
El guion de la misión también se ejecuta con y sin eventos simulados; la ausencia
de disparos debe producir fallo de cobertura, nunca un resultado positivo vacío.

`build_core_smoke.py` genera una sola misión, `31_Realistic_CAS_core.miz`, con los
fuentes reales incrustados, ambos bandos, vehículos distinguibles e inmortales,
Game Master y sin slots pilotables. Duración 480 segundos. Solo necesita `dcs.log`.
Se comprueban sintaxis Lua 5.1 y recarga pydcs; ejecución en DCS completada por el usuario.
El resultado interno PASS no sustituye el contraste de detección nativa del log.

### Resultado in-engine, 2026-09-09

Log archivado en `Missions/realistic_cas_core_01/results-20260909/dcs.log`,
relativo a Saved Games/DCS. Una ejecución completa: `failures=0`, 45 eventos de
fuego rojos y 55 azules. No son 100 proyectiles: 26 eventos SHOT de cañón de tanque
y 74 SHOOTING_START de ráfagas. Cero errores del backend. Estado final: 3 revelados,
101 renovaciones, 3 expiraciones y ninguna entrada pendiente.

Contraste nativo (tiempos relativos al arranque del ensayo, muestreo cada 5s):

- Inicialmente ninguno detecta al contrario.
- BLUE se revela a 30s; RED lo detecta en la muestra de 35s.
- RED dispara a 45,184s y queda expuesto por el evento real; BLUE lo detecta a 50s.
- Último evento rojo a 179,024s; expiración física a 240s y detección perdida
  por BLUE a 245s. El desfase de 0,976s respecto a la expiración lógica es
  compatible con el intervalo de servicio de 1s.
- Último evento azul a 209,973s; expiración a 270s y detección perdida por RED a 275s.
- Observación manual de RED a 300s, detectado por BLUE a 310s; renovación a 330s
  mantiene la exposición más allá de 360s. Expira a 390s; BLUE deja de detectarlo
  en la muestra de 395s.
- Apagado a 430s: ambos vuelven a detectar al contrario a 435s. La restauración
  no solo fue aceptada por setCommand, también se refleja en detección nativa.

Conclusión: núcleo validado para este escenario terrestre, incluyendo eventos
reales y visibilidad efectiva. No valida todavía sensores propios, combate CAS,
grandes cantidades de grupos ni rendimiento general bajo aceleración.

## Pendiente, deliberadamente

Actualización posterior: detección visual/EO/IR/radar/terrestre, entorno aproximado,
perfiles, índice espacial y puente DCS implementados como prototipo separado.
Ver `resources/plugins/realisticcas/README.md`. El conjunto pasa 31 pruebas Lua 5.1,
incluido el guion de la nueva misión con dobles y una búsqueda densa de 5.000 blancos
que comprueba límites de trabajo. No equivale a un benchmark de FPS en DCS.
Misión `32_Realistic_CAS_sensors.miz` preparada en `Missions/realistic_cas_sensors_01`:
380s, solo log, de día. Noche/nubes/GMTI tienen pruebas de modelo pero aún no de motor.

Continúan pendientes: validación del puente sensor en DCS; generación de lista y propiedad de
visibilidad; ciclo de vida completo y clones TIC; integración JTAC/MOOSE/Skynet;
coordinación de tareas y GUI/opciones; pruebas de rendimiento de campaña. Las
observaciones manuales de la misión de prueba no son un modelo de sensores.
