# Prueba 33 — diagnóstico terrestre (2026-09-09)

Resultado: **0 fallos, 2 inconclusos, 7 controles ejecutados**. Log archivado fuera
de Missions en `Saved Games/DCS/realistic-cas-test-results/ground-los-33/dcs.log`.

## Causa de los fallos de la prueba 32

Confirmada para las geometrías y alturas de sensor del prototipo: falta de LOS por
relieve, no un error de registro ni de eventos del detector.

- Pareja original T-72 → camión a 2 km: `land.isVisible=false`. El perfil muestreado
  tiene despeje mínimo de **−4,29 m** respecto al rayo observador+2m / blanco+1m.
- Pareja original Abrams → camión a 4 km: `land.isVisible=false`, despeje mínimo
  muestreado **−41,13 m**. Elevar ambos extremos 10m sigue sin despejarla.
- Los orígenes de las unidades están aproximadamente a 0m AGL, sin un desfase
  oculto significativo. Las alturas añadidas son las del modelo, no prueba de la
  posición exacta de las ópticas reales de cada vehículo.

Los rayos elevados son diagnósticos, nunca se usan para conceder contactos. El
despeje muestreado no es una medida exhaustiva de cada obstáculo; el veto aplicado
es la consulta de LOS del propio motor.

## Controles concluyentes

- Ambos observadores detectan sus controles cercanos a unos 100m con LOS.
- Abrams detecta un candidato distinto a **4.000,13m** con LOS.
- T-72 no descubre el candidato a **4.000,01m** pese a tener LOS: supera su rango.
- Abrams no descubre el candidato a **6.000,08m** pese a tener LOS: supera su rango.
- Ambas parejas originales bloqueadas permanecen ocultas.
- Caducidad y restauración al detener el plugin correctas. Sin errores de callbacks.

## Inconclusos, no fallos del plugin

- `NEAR_0`: ninguna de las ocho orientaciones a 2 km tenía LOS desde el T-72.
- `CITY_0`: ninguna de las ocho orientaciones a 1,5 km tenía LOS. No se pudo ejecutar
  el diferencial desierto/ciudad manteniendo geometría idéntica.

Pendiente tras la prueba 33: control visual terrestre intermedio (2km) y
diferencial de cobertura (1,5km) desde un emplazamiento distinto, escogido con LOS
comprobada. No aumentar alturas/rangos para forzar un PASS. Este ensayo no valida
alcances reales de los vehículos, solo las reglas aproximadas del plugin.

## Prueba 34 — controles pendientes resueltos

Resultado: **0 fallos, 0 inconclusos**, confirmado por el usuario y por el log
del 2026-09-09, sesión de las 16:03–16:04 UTC. Evidencias archivadas en
`Saved Games/DCS/realistic-cas-test-results/clear-ground-34/`: `dcs.log` y
`visual-confirmation.png`.

El selector encontró el candidato 64 con LOS para ambas distancias; tras crear
las unidades se comprobó de nuevo la LOS con las alturas del detector, sin
elevar sensores ni modificar rangos para conseguir el resultado.

- A los 55s, el T-72 había descubierto ambos camiones: 2km y 1,5km.
- Al cambiar únicamente la cobertura modelada del camión a 1,5km de desierto a
  ciudad, dejó de cumplir el rango de detección y caducó su exposición. Control
  confirmado a los 110s; el camión a 2km seguía detectándose.
- Las trazas distinguen `ENVELOPE_REJECT` para el objetivo con cobertura ciudad
  de `DETECT ... via visual` para el control a 2km. No se movieron las unidades.
- Tras detener los detectores, ambos contactos habían caducado a los 165s.
- Visibilidad restaurada al detener el plugin a los 180s, sin errores de callbacks.

Esto cierra los dos inconclusos de la prueba 33. La cobertura ciudad es un
parámetro del modelo: no valida clasificación automática del terreno ni edificios
reales. Quedan pendientes los controles in-engine específicos de noche/IR,
nubes y GMTI; este resultado no equivale a validar toda la integración de campaña.
