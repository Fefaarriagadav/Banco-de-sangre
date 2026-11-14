# Sprint Planning — Sprint 1

**Proyecto:** Sistema de gestión de banco de sangre  
**Estado:** Documentación reconstruida con el relato del equipo y los registros de GitHub; pendiente de validar la cronología y adjuntar evidencias de Axosoft.  
**Reunión inicial:** Martes 03 de noviembre de 2026, presencial, duración de 1 hora.  
**Período informado del sprint:** domingo 1 a jueves 12 de noviembre de 2026. 

## 1. Participantes, roles y colaboración

Los cinco integrantes participaron en la reunión. El profesor no estuvo presente.

| Integrante | Rol informado | Disponibilidad para el sprint |
|---|---|---:|
| Tomás Garrido | Product Owner; desarrollo de H2 y H4; revisión del trabajo | 15 h |
| Josefa Arriagada | Scrum Master; desarrollo de H1 y H3 | 15 h |
| Ricardo Lagos | Desarrollo de H5 | 15 h |
| Matías Palacios | Desarrollo de H6 | 15 h |
| Diego Mellado | Desarrollo de H7 | 15 h |
| **Total** | | **75 h** |

Según el equipo, los cinco propusieron las historias a partir de los requisitos
funcionales previamente definidos y participaron equitativamente en la
planificación. No se dispone de un registro de intervenciones individuales.
La distribución de implementación y revisión se especifica en la sección 3.

No se establecieron días fijos de trabajo por integrante ni se informaron
ausencias o restricciones de disponibilidad durante este período.

## 2. Objetivo, selección y alcance de la entrega

**Objetivo del sprint —redacción basada en el alcance informado—:** Entregar un
prototipo de gestión interna del banco de sangre que permita, según el rol del
usuario, registrar donantes y extracciones, consultar candidatos aptos, actualizar
su habilitación y controlar las unidades mediante vencimientos y alertas de
excedentes con sugerencias de redistribución.

El equipo seleccionó **H1–H7** para concentrar esta primera entrega en donantes,
donaciones, elegibilidad e inventario. La división del producto separa este
flujo de la gestión posterior de pedidos y envíos de hospitales o clínicas.

**Fuera del compromiso del sprint:** La gestión de pedidos y despachos de
hospitales/clínicas corresponde a una etapa posterior. Las sugerencias de H7
son informativas y no ejecutan despachos. La rama antes denominada H8 y ahora
`feature/final` corresponde, según el equipo, a correcciones posteriores y no a
una octava historia comprometida en este sprint.

La consulta de inventario se documenta en relación con H5–H7. No se incorpora
retrospectivamente una historia adicional por la presencia de pantallas de
stock en versiones posteriores del código.

No se informaron condiciones adicionales del profesor o cliente fuera de la
pauta compartida para la entrega.

## 3. Sprint Backlog: estimaciones y responsabilidades

Las estimaciones siguientes fueron informadas por el equipo y coinciden con los
valores actualmente publicados en las historias de GitHub. Reemplazan las
estimaciones preliminares del primer borrador.

| Historia y fuente | Estimación | Responsable principal | Colaborador/revisor informado | Dependencia | Fecha máxima |
|---|---:|---|---|---|---|
| [H1: registrar donantes con ID único](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/1) | 8 h | Josefa Arriagada | Tomás Garrido | Ninguna | 07-11-2026 |
| [H2: registrar elegibilidad médica](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/2) | 4 h | Tomás Garrido | Josefa Arriagada | H1 | 07-11-2026 |
| [H3: buscar donantes habilitados por grupo y Rh](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/3) | 6 h | Josefa Arriagada | Tomás Garrido | H2; integración con H4 | 07-11-2026 |
| [H4: actualizar habilitación](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/4) | 5 h | Tomás Garrido | Josefa Arriagada | H1; H3 para integrar exclusiones | 07-11-2026 |
| [H5: registrar extracciones](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/5) | 10 h | Ricardo Lagos | Tomás Garrido | H2; integración con restricciones de H4 | 12-11-2026 |
| [H6: controlar vencimientos](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/6) | 10 h | Matías Palacios | Tomás Garrido | H5 | 12-11-2026 |
| [H7: consultar excedentes y redistribución](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/7) | 10 h | Diego Mellado | Tomás Garrido | H6 | 12-11-2026 |
| **Total estimado de historias** | **53 h** | | | | |

### Distribución de capacidad

| Integrante | Historias principales | Esfuerzo estimado de esas historias | Capacidad | Diferencia para revisión, coordinación y ajustes |
|---|---|---:|---:|---:|
| Josefa Arriagada | H1 y H3 | 14 h | 15 h | 1 h |
| Tomás Garrido | H2 y H4 | 9 h | 15 h | 6 h |
| Ricardo Lagos | H5 | 10 h | 15 h | 5 h |
| Matías Palacios | H6 | 10 h | 15 h | 5 h |
| Diego Mellado | H7 | 10 h | 15 h | 5 h |
| **Total** | | **53 h** | **75 h** | **22 h** |

La diferencia de 22 horas es un cálculo de capacidad agregada, **no una reserva
formal que el equipo haya declarado ni un registro de horas reales**. Las
revisiones cruzadas y las funciones de PO/SM no tienen estimación separada.
La carga de Josefa deja solo 1 hora de diferencia; Tomás concentra cinco
revisiones cruzadas además de H2 y H4. Estos puntos deben considerarse al evaluar
la distribución y no permiten afirmar por sí solos que hubo sobrecarga efectiva.

## 4. Plan operativo y secuencia de integración

El equipo informó que trabajó **por etapas, sin desarrollo en paralelo**, para
reducir conflictos en el código. No se informaron fechas de inicio y término
por tarea, por lo que no se reconstruye un calendario diario ficticio.

| Etapa | Trabajo y relaciones entre historias | Criterio para avanzar | Fecha máxima informada |
|---|---|---|---|
| Primera entrega interna | H1 habilita H2 y H4; H2 habilita la búsqueda de H3. La exclusión de restricciones de H4 se integra con H3. | Registrar un donante, consultar/modificar su elegibilidad y demostrar búsquedas que respeten la habilitación; presentar el trabajo al PO. | 07-11-2026 |
| Segunda entrega interna | H5 registra las unidades; H6 utiliza esas unidades para vencimientos; H7 utiliza el inventario resultante para excedentes. | Demostrar extracción, control de vencimiento y sugerencias informativas de redistribución; presentar el trabajo al PO. | 12-11-2026 |

La tabla expresa las dependencias y los dos hitos declarados. Los criterios para
avanzar sintetizan los criterios de las historias; no prueban su ejecución.
Las 53 horas de esfuerzo no equivalen a 53 horas corridas de calendario ni
garantizan el cumplimiento del plazo, especialmente bajo una estrategia secuencial.

## 5. Tareas implementables y verificaciones

Las tareas y asignaciones se extrajeron de GitHub. Cada fila incluye una
verificación derivada de sus criterios de aceptación o Definition of Done.
**Se trata del diseño de verificación, no de resultados ejecutados en esta
revisión.** El anexo conserva las descripciones completas publicadas.

### H1 — Josefa Arriagada; revisión de Tomás Garrido

| Tarea y fuente | Estimación | Verificación explícita |
|---|---:|---|
| [H1-T1: campos y validaciones](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/8) | 1 h | Revisar campos obligatorios/opcionales, tipos y reglas con otro integrante; contrastarlos con el formulario y SQLite. |
| [H1-T2: almacenamiento en SQLite](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/11) | 1 h | Registrar datos válidos, reabrir la aplicación y comprobar persistencia; ante error, verificar ausencia de registro parcial. |
| [H1-T3: identificadores únicos](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/14) | 1 h | Crear varios donantes, comprobar IDs distintos y recuperar cada registro mediante su ID. |
| [H1-T4: interfaz de registro](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/15) | 2 h | Registrar desde la interfaz y comprobar campos, confirmación, ID y mensajes comprensibles. |
| [H1-T5: validaciones y errores](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/16) | 1 h | Probar campos vacíos y formatos inválidos: deben impedir el guardado; corregirlos debe permitir continuar. |
| [H1-T6: autorización por rol](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/17) | 1 h | Comprobar registro autorizado y rechazo de otro rol sin cambios en la base, también al guardar. |
| [H1-T7: aceptación y documentación](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/18) | 1 h | Ejecutar los casos de H1 y guardar resultados, evidencia y revisión de otro integrante. |

Orden registrado: campos → almacenamiento → ID → interfaz → validaciones y
autorización → aceptación. Total de tareas: 8 h.

### H2 — Tomás Garrido; revisión de Josefa Arriagada

| Tarea y fuente | Estimación | Verificación explícita |
|---|---|---|
| [H2.1: registrar y consultar elegibilidad](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/9) | 2h | Guardar y consultar resultado para un donante existente; rechazar donante/valor inválido; comprobar que no se almacenan respuestas clínicas. |
| [H2.2: restringir modificaciones](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/10) | 2h | Comparar actualización autorizada con rechazo por falta de permiso, preservando el valor anterior e informando el motivo. |

Estimación de la historia: 4 h. H2 requiere H1; las verificaciones de permisos se
integran con el registro y consulta.

### H3 — Josefa Arriagada; revisión de Tomás Garrido

| Tarea y fuente | Estimación | Verificación explícita |
|---|---:|---|
| [H3-T1: búsqueda por grupo/Rh](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/20) | 1 h | Probar grupos A/B/AB/O y Rh +/−; comprobar coincidencia simultánea y rechazo de filtros inválidos. |
| [H3-T2: validar elegibilidad](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/21) | 1 h | Comprobar inclusión de habilitados y exclusión de restricciones temporales/permanentes, incluida selección para comunicaciones. |
| [H3-T3: interfaz y resultados](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/22) | 1 h | Verificar resultados, ausencia de coincidencias, errores de filtros y navegación. |
| [H3-T4: selección y correos](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/23) | 2 h | Con destinatarios de prueba autorizados, comprobar selección, confirmación previa, mensajes de éxito/error y ausencia de envío automático por stock. |
| [H3-T5: pruebas y documentación](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/24) | 1 h | Documentar casos de búsqueda, exclusión y envío, sus resultados y los errores detectados. |

Secuencia funcional: consulta → elegibilidad → interfaz → selección/envío →
verificación. Total: 6 h. Los correos aparecen en las subtareas y en el PR de
H3; la descripción de la historia padre todavía dice que no incluye convocatorias.
Debe explicarse esa evolución como ajuste de alcance y no ocultarse la diferencia.

### H4 — Tomás Garrido; revisión de Josefa Arriagada

| Tarea y fuente | Estimación | Verificación explícita |
|---|---|---|
| [H4.1: cambiar habilitación y validar períodos](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/12) | 3h | Guardar estados válidos, rechazar períodos ausentes/invertidos y usuarios sin permiso, manteniendo el valor previo ante error. |
| [H4.2: excluir restricciones en convocatorias](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/13) | 2h | Inhabilitar y repetir la búsqueda: debe desaparecer; rehabilitar y comprobar que reaparece si cumple las demás reglas. |

Estimación de la historia: 5 h. H4.1 requiere un donante de H1; H4.2 requiere
la búsqueda de H3 y la actualización de estado de H4.1.

### H5 — Ricardo Lagos; revisión de Tomás Garrido

| Tarea y fuente | Estimación | Verificación explícita |
|---|---:|---|
| [H5-T1: validar información de la donación](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/28) | 2 h | Revisar datos obligatorios y asociación al donante; probar datos incompletos y donante no válido sin crear unidad. |
| [H5-T2: ID de donación y relación con donante](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/29) | 3 h | Registrar varias unidades, comprobar unicidad y recuperar la donación con su donante correcto. |
| [H5-T3: interfaz de registro](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/30) | 3 h | Probar acceso del rol Enfermero, registro válido, confirmación con ID y mensajes ante rechazo. |
| [H5-T4: interfaz de banco de donaciones](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/31) | 2 h | Consultar lista y detalle; comprobar identificación de unidades no aptas y su motivo. |

Secuencia: validaciones → identidad/asociación → formulario → consulta. Total:
10 h. La cuarta tarea exige integración con los estados de H6 para mostrar
correctamente las unidades vencidas; esa comprobación debe completarse tras H6.

### H6 — Matías Palacios; revisión de Tomás Garrido

| Tarea y fuente | Estimación | Verificación explícita |
|---|---:|---|
| [H6-T1: vencimiento, validaciones y actualización automática](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/26) | 5,5 h | Guardar vencimiento válido; rechazar formatos inválidos sin sustituir valores válidos; simular el límite temporal y comprobar exclusión del stock. |
| [H6-T2: alertas anticipadas y visualización](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/27) | 4,5 h | Probar unidades dentro y fuera de la ventana de alerta y comprobar identificación y vencimiento en la visualización. |

H6 requiere unidades de H5. La actualización de vencimiento y su consulta
alimentan las alertas. Total de tareas: 10 h.

### H7 — Diego Mellado; revisión de Tomás Garrido

| Tarea y fuente | Estimación | Verificación explícita |
|---|---:|---|
| [H7-T1: umbrales y alertas de excedente](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/37) | 5 h | Probar stock superior, igual e inferior al umbral y datos inválidos; verificar excedente y ausencia de alertas improcedentes. |
| [H7-T2: sugerencias de redistribución](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/38) | 5 h | Probar excedente con destinos válidos y sin ellos; comprobar sugerencias informativas sin ejecución de despacho. |

Secuencia: inventario actualizado de H6 → evaluación de umbral → destinos y
sugerencias. Total: 10 h.

## 6. Criterios de aceptación y condiciones de término

Los criterios completos están en las siete historias y en sus tareas enlazadas,
reproducidas en [el anexo de trazabilidad](anexo_historias_tareas_sprint_1.md).
Las verificaciones de la sección 5 permiten comprobar sus resultados observables.

Las Definition of Done de las tareas incluyen, según cada caso: funcionalidad
implementada, validaciones, comprobación de persistencia/identidad, pruebas,
documentación y código revisado e integrado. Estas condiciones se consolidan
aquí; no se atribuye al equipo una Definition of Done global formal que no fue
aportada.

Según el equipo, el PO verifica el trabajo y determina su aceptación mediante
la revisión de los PR. Para acreditar el término de cada historia conviene
adjuntar: resultado de sus verificaciones, referencia del PR integrado y
conformidad del PO. Un issue cerrado o una casilla marcada no reemplaza esa evidencia.

## 7. Estrategia de pruebas y evidencia disponible

El equipo indicó que las historias tienen pruebas en Python.

| Cobertura a contrastar con los criterios | Archivo de referencia en la versión posterior |
|---|---|
| H1: registro de donantes | `tests/test_registro_donantes.py` |
| H2: elegibilidad | `tests/test_elegibilidad.py` |
| H3: búsqueda y convocatorias | `tests/test_pedir_donaciones.py` |
| H4: habilitación | `tests/test_habilitacion.py` |
| H5: registro de extracciones | `tests/test_registro_donaciones.py` |
| Integración H5–H6 | `tests/test_integracion_h5_h6.py` |
| H6 e inventario | `tests/test_vencimientos.py`, `tests/test_stock_vencimientos.py` |
| H7: excedentes y redistribución | `tests/test_alertas_redistribucion.py` |

[Directorio de pruebas de la versión consultada](https://github.com/Fefaarriagadav/Banco-de-sangre/tree/60da51e1b3cd44a6336ff006b44b4c25c08bb35b/tests).

- **Comando:** `python -m unittest discover -s tests -v`
![Resultado de las pruebas automatizadas](docs/prueba_test)

## 8. Coordinación, revisión e integración

- **Seguimiento:** El equipo informó que utilizó Axosoft desde el comienzo,
  registrando historias, tareas, responsables, estimaciones y estados. No se
  accedió a Axosoft en esta revisión; quedan pendientes capturas o un reporte.
- **Coordinación:** Se utilizó WhatsApp para informar al PO de la creación de
  PR y recibir indicaciones o aceptación. No se declaró una frecuencia fija
  de reuniones de seguimiento ni se inventan Daily Scrums.
- **Ramas:** Cada integrante trabajaba en la rama de su historia y abría un
  PR para revisión e integración en `main`.
- **Validación:** El PO revisaba el trabajo y solicitaba cambios o lo aceptaba,
  según el relato del equipo; Josefa figura como colaboradora/revisora de H2 y H4.
- **Evidencia conversacional:** El equipo conserva los mensajes. Deben
  seleccionarse extractos relevantes con fecha, evitando exponer conversaciones
  o datos ajenos a la entrega.

## 9. Riesgos, ajustes y diferencias respecto del plan

| Punto | Información disponible | Tratamiento documental |
|---|---|---|
| Conflictos al integrar código | El equipo eligió trabajar por etapas para reducirlos. | Registrar esta medida como decisión informada. |
| Variaciones de esfuerzo | Algunas tareas demoraron más y otras menos, según el equipo. | No calcular desviaciones ni horas reales sin datos por tarea. |
| Diferencia entre estimación y nota del PR de H6 | Las tareas suman 5,5 + 4,5 h; el PR #39 indica «T1: 3 horas; T2: 4.5 horas». | Confirmar si 3 h son tiempo real, estimación revisada u otra referencia antes de usarlo como resultado. |
| H3 incorpora correos en sus tareas | El issue padre dice que no envía convocatorias, mientras las tareas y el PR #32 incluyen envío manual. | Identificar cuándo se acordó la ampliación y actualizar la trazabilidad. |
| Estados de cierre y checklist | H5 y H7 están cerradas, pero sus criterios padre conservan casillas sin marcar en la consulta. | Conciliar el registro con el PO y las evidencias; no marcar cumplimiento automáticamente. |
| Correcciones posteriores | El equipo distingue `feature/final` del compromiso H1–H7. | Identificar los cambios posteriores y no utilizarlos como prueba de que estaban terminados el 12. |
| Inhabilitación automática después de donar | El equipo confirmó que se incorporó durante el sprint, cerca de su término. | Registrar como ajuste realizado durante el sprint; falta vincular el cambio con su evidencia de versión o aceptación. No clasificarlo como corrección posterior. |

Los puntos detectados durante esta revisión son observaciones posteriores,
no riesgos que se atribuyan retrospectivamente a la reunión del día 3.

## 10. Contraste de cronología con GitHub

Las horas siguientes se convirtieron de UTC a **America/Santiago**. La fecha de
integración no demuestra por sí sola la fecha de aceptación ni el momento en
que se implementó todo el alcance.

| Evidencia | Integración registrada en horario de Chile | Relación con el período informado |
|---|---|---|
| [PR #19 — H1](https://github.com/Fefaarriagadav/Banco-de-sangre/pull/19) | 03-11-2026, 17:26 | Integración anterior al inicio declarado; véase aclaración de las fuentes. |
| [PR #25 — H2](https://github.com/Fefaarriagadav/Banco-de-sangre/pull/25) | 07-11-2026, 16:51 | Integración anterior al inicio declarado; véase aclaración de las fuentes. |
| [PR #32 — H3](https://github.com/Fefaarriagadav/Banco-de-sangre/pull/32) | 08-11-2026, 20:31 | Dentro del período informado. |
| [PR #33 — H4](https://github.com/Fefaarriagadav/Banco-de-sangre/pull/33) | 09-11-2026, 21:30 | Dentro del período informado. |
| [PR #36 — actualización de H4 e integración](https://github.com/Fefaarriagadav/Banco-de-sangre/pull/36) | 10-11-2026, 00:15 | Dentro del primer hito informado. |
| [PR #40 — H5](https://github.com/Fefaarriagadav/Banco-de-sangre/pull/40) | 12-11-2026, 22:35 | Dentro del segundo hito informado. |
| [PR #39 — H6](https://github.com/Fefaarriagadav/Banco-de-sangre/pull/39) | 12-11-2026, 22:35 | Dentro del segundo hito informado. |
| [PR #41 — H7](https://github.com/Fefaarriagadav/Banco-de-sangre/pull/41) | 12-11-2026, 22:35 | Dentro del segundo hito informado. |

## 11. Evidencias y pendientes para cerrar el documento

| Pendiente | Evidencia o respuesta necesaria | Estado |
|---|---|---|
| Respaldar colaboración y planificación | Extractos de WhatsApp de selección, estimación, distribución y revisión, con fechas. | No adjuntos |
| Respaldar control de tareas | Capturas/reporte de Axosoft con tareas, responsables, estimaciones, estados y ajustes. | No adjuntos |
| Acreditar pruebas del incremento | Reporte con fecha real, commit, comando, resultados y casos de interfaz. Si se obtiene ahora, identificarlo como verificación posterior. | El equipo no conserva capturas; reporte no adjunto |
| Acreditar aceptación | Conformidad del PO y correspondencia con criterios de H1–H7. | Relato del equipo; faltan evidencias específicas |
| Aclarar ampliaciones y correcciones | La inhabilitación posdonación fue incorporada durante el sprint según el equipo; falta su evidencia y aclarar la evolución de correos en H3. Mantener separadas las correcciones posteriores de `feature/final`. | Inhabilitación aclarada por el equipo; evidencias pendientes |


## 12. Fuentes y relación con la pauta

- Registro del equipo: fechas, participantes, roles, disponibilidad, responsables,
  hitos, coordinación y separación del trabajo posterior.
- [Anexo de historias y tareas](anexo_historias_tareas_sprint_1.md): estado de los
  issues consultados el 13-11-2026, con enlaces a las fuentes originales.
- [Captura estructurada de issues](evidencias/github_issues_sprint1.json) y
  [metadatos de PR](evidencias/github_prs_sprint1.json).
- Pauta de evaluación de la entrega.
| Criterio de la pauta | Secciones que lo respaldan |
|---|---|
| Priorización y planificación del desarrollo | 3 y 4 |
| Visión de la entrega parcial y metas del sprint | 2, 3 y 6 |
| Colaboración y distribución de responsabilidades | 1, 3 y 8 |
| Plan operativo del sprint | 3, 4, 5 y 10 |
| Traducción de requerimientos en tareas implementables | 5 y anexo |
| Diseño de tests o verificaciones | 5, 6 y 7 |
 
Este documento respalda la planificación. El control de tareas en Axosoft, el
informe de resultados de pruebas y la retrospectiva se presentan en sus
apartados correspondientes de la entrega.
