# Anexo: historias y tareas de GitHub — Sprint 1

Consulta realizada el 13-11-2026. Este anexo reproduce el estado disponible al consultar; no demuestra por sí solo qué contenido estaba acordado en la reunión del 03-11-2026. Las casillas de GitHub expresan el registro del equipo y no sustituyen resultados de pruebas ni aprobación independiente.

## #1 — [H1] Registrar donantes con un identificador único

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/1) · Estado al consultar: closed · Asignación: Fefaarriagadav

## Historia de usuario

Como entrevistador, quiero registrar los datos de un donante y obtener un identificador único, para identificarlo en las operaciones del banco reduciendo la exposición innecesaria de sus datos personales.

## Datos del backlog original

- **ID:** H1
- **Valor:** Alto
- **Riesgo:** Bajo
- **Estimación original:** 8 horas
- **Depende de:** Ninguna. Reemplazar por enlaces reales al crear los issues.
- **Planificación:** Seleccionada en el sprint 1.
- **Trazabilidad:** RF-07 y RF-08.

## Criterios de aceptación propuestos

- [x] Dado que estoy autorizado y completo los datos obligatorios válidos de un nuevo donante, cuando confirmo el registro, entonces se guarda un único registro y se muestra su identificador.

- [x] Dado que falta un campo obligatorio o un dato no cumple las validaciones acordadas, cuando intento guardar, entonces se identifica el campo a corregir y no se crea un registro incompleto.

- [x] Dado que existen donantes registrados, cuando se asigna un identificador a uno nuevo, entonces no coincide con ningún identificador ya asignado.

- [x] Dado un usuario sin permiso de registro, cuando intenta crear un donante, entonces la operación se rechaza y no se guardan cambios.

## Definition of Ready

- [x] Rol, acción y beneficio revisados.
- [x] INVEST revisado con el equipo, incluidas independencia, dependencias y tamaño para un sprint.
- [x] Criterios de aceptación acordados y verificables.
- [x] Dudas y reglas de negocio resueltas con el Product Owner.
- [x] Estimación acordada por el equipo de desarrollo.

---

## #2 — [H2] Registrar el resultado final de elegibilidad médica

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/2) · Estado al consultar: closed · Asignación: garridotomas

## Historia de usuario

Como entrevistador, quiero registrar únicamente el resultado final de la evaluación médica de un donante como Apto o No apto, para validar su elegibilidad sin almacenar sus respuestas clínicas confidenciales.

## Datos del backlog original

- **ID:** H2
- **Valor:** Alto
- **Riesgo:** Medio
- **Estimación original:** 4 horas.
- **Depende de:** H1. Reemplazar por enlaces reales al crear los issues.
- **Planificación:** Seleccionada en el sprint 1.
- **Trazabilidad:** RF-02 y RF-08

## Criterios de aceptación propuestos

- [x] Dado un donante registrado y una evaluación realizada, cuando guardo Apto o No apto, entonces el resultado queda asociado al donante seleccionado y puede consultarse.

- [x] Dado que no seleccioné un resultado válido o el donante no existe, cuando intento guardar la evaluación, entonces se explica el error y no se registra el resultado.

- [x] Dado el registro de una evaluación, cuando consulto sus datos almacenados, entonces contiene el resultado final y no las respuestas del cuestionario clínico.

- [x] Dado un usuario sin permiso para evaluar, cuando intenta modificar el resultado, entonces la operación se rechaza y se conserva el resultado previo.

## Pendientes de refinamiento con el Product Owner

Acordar vigencia de la evaluación, responsables autorizados y relación del resultado con los estados de H4. Resolver el alcance de RF-08. La evaluación médica ocurre fuera de esta historia.

## Definition of Ready

- [x] Rol, acción y beneficio revisados.
- [x] INVEST revisado con el equipo, incluidas independencia, dependencias y tamaño para un sprint.
- [x] Criterios de aceptación acordados y verificables.
- [x] Dudas y reglas de negocio resueltas con el Product Owner.
- [x] Estimación acordada por el equipo de desarrollo.

---

## #3 — [H3] Buscar donantes habilitados por grupo sanguíneo y factor Rh

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/3) · Estado al consultar: closed · Asignación: Fefaarriagadav

## Historia de usuario

Como entrevistador/enfermero, quiero buscar donantes habilitados filtrando por grupo sanguíneo y factor Rh, para identificar personas que pueden ser convocadas sin incluir donantes con restricciones vigentes.

## Datos del backlog original

- **ID:** H3
- **Valor:** Medio
- **Riesgo:** Bajo
- **Estimación original:** 6 horas.
- **Depende de:** H2.
- **Planificación:** Seleccionada en el sprint 1.
- **Trazabilidad:** RF-01.

## Criterios de aceptación propuestos

- [x] Dado que existen donantes aptos y habilitados de distintos grupos y Rh, cuando selecciono un grupo y factor válidos y busco, entonces se muestran solo los que coinciden con ambos filtros y cumplen la regla de elegibilidad acordada.

- [x] Dado un filtro con un valor no permitido, cuando intento buscar, entonces se señala el filtro inválido y no se ejecuta una búsqueda con ese valor.

- [x] Dado un donante No apto, sin evaluación apta vigente o con inhabilitación vigente, cuando busco su grupo y Rh, entonces no aparece como candidato a convocatoria, conforme a la regla propuesta que debe aprobar el PO.

- [x] Dado que no hay coincidencias, cuando realizo la búsqueda, entonces se informa que no se encontraron donantes sin mostrar personas de otros grupos.

## Pendientes de refinamiento con el Product Owner

Aprobar la regla que combina evaluación e inhabilitaciones y la vigencia de ambas. Revisar vínculos con H4 y H13. Esta historia identifica candidatos; no envía convocatorias.

## Definition of Ready

- [x] Rol, acción y beneficio revisados.
- [x] INVEST revisado con el equipo, incluidas independencia, dependencias y tamaño para un sprint.
- [x] Criterios de aceptación acordados y verificables.
- [x] Dudas y reglas de negocio resueltas con el Product Owner.
- [x] Estimación acordada por el equipo de desarrollo.

---

## #4 — [H4] Actualizar el estado de habilitación de un donante

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/4) · Estado al consultar: closed · Asignación: garridotomas

## Historia de usuario

Como entrevistador autorizado, quiero actualizar la habilitación de un donante e indicar el período de restricción cuando corresponda, para mantener las listas de convocatoria libres de personas con restricciones vigentes.

## Datos del backlog original

- **ID:** H4
- **Valor:** Alto
- **Riesgo:** Bajo
- **Estimación original:** 5 horas. 
- **Depende de:** H1. 
- **Planificación:** Seleccionada en el sprint 1.
- **Trazabilidad:** RF-02.

## Criterios de aceptación propuestos

- [x] Dado un donante registrado y un entrevistador autorizado, cuando confirmo Habilitado, Inhabilitado temporal o Inhabilitado permanente con los datos requeridos, entonces se guarda y se muestra el nuevo estado.

- [x] Dado que selecciono Inhabilitado temporal y falta el período requerido o su fecha final precede a la inicial, cuando intento guardar, entonces se explica el error y se conserva el estado anterior.

- [x] Dado un donante con restricción vigente, cuando se consulta la lista de candidatos, entonces no figura como habilitado para convocatoria.

- [x] Dado un usuario sin autorización, cuando intenta cambiar la habilitación, entonces se rechaza el cambio y se mantiene el estado previo.

## Pendientes de refinamiento con el Product Owner

El original también menciona al personal del banco; RF-02 asigna esta acción al entrevistador. Acordar permisos, fechas exigidas, transición al finalizar una restricción y si se requiere historial de cambios. 

## Definition of Ready

- [x] Rol, acción y beneficio revisados.
- [x] INVEST revisado con el equipo, incluidas independencia, dependencias y tamaño para un sprint.
- [x] Criterios de aceptación acordados y verificables.
- [x] Dudas y reglas de negocio resueltas con el Product Owner.
- [x] Estimación acordada por el equipo de desarrollo.

---

## #5 — [H5] Registrar una bolsa de extracción asociada a un donante apto

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/5) · Estado al consultar: closed · Asignación: Oliverlulz

## Historia de usuario

Como enfermera, quiero registrar una bolsa de extracción asociada a un donante previamente validado como apto, para incorporar la unidad a la trazabilidad interna del banco de sangre.

## Datos del backlog original

- **ID:** H5
- **Valor:** Alto
- **Riesgo:** Medio
- **Estimación original:** 10h
- **Depende de:** H2. 
- **Planificación:** Seleccionada en el sprint 1.
- **Trazabilidad:** RF sin definir por ahora.

## Criterios de aceptación propuestos

- [ ] Dado un donante registrado que cumple la elegibilidad acordada y una bolsa con datos válidos, cuando confirmo la extracción, entonces se registra una unidad identificable vinculada a ese donante y se muestra la confirmación.

- [ ] Dado que falta un dato obligatorio de la bolsa o el donante indicado no existe, cuando intento registrar la extracción, entonces se informa el error y no se crea la unidad.

- [ ] Dado un donante sin resultado Apto vigente o con restricción vigente, cuando intento registrar una extracción, entonces se impide el registro según la regla propuesta pendiente de aprobación.

- [ ] Dado que ya existe una bolsa con el identificador ingresado, cuando intento registrarla nuevamente, entonces se informa el duplicado y no se crea una segunda unidad.

## Pendientes de refinamiento con el Product Owner

Definir campos de la unidad, identificador, estados y validaciones. Aprobar si la habilitación de H4 también condiciona la extracción. Registrar una bolsa no implica que esté liberada para uso clínico ni disponible en stock.

## Definition of Ready

- [ ] Rol, acción y beneficio revisados.
- [ ] INVEST revisado con el equipo, incluidas independencia, dependencias y tamaño para un sprint.
- [ ] Criterios de aceptación acordados y verificables.
- [ ] Dudas y reglas de negocio resueltas con el Product Owner.
- [ ] Estimación acordada por el equipo de desarrollo.

---

## #6 — [H6] Controlar vencimientos y recibir alertas de caducidad próxima

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/6) · Estado al consultar: closed · Asignación: Matiasss-s

## Historia de usuario

Como personal de casa donante, quiero registrar el vencimiento de las unidades y consultar su caducidad actualizada y las alertas anticipadas, para identificar las unidades que requieren atención antes de perderse por vencimiento.

## Datos del backlog original

- **ID:** H6
- **Valor:** Alto
- **Riesgo:** Alto
- **Estimación original:** 10h
- **Depende de:** H5. 
- **Planificación:** Seleccionada en el sprint 1.
- **Trazabilidad:** RF-03 y RF-04.

## Criterios de aceptación propuestos

- [x] Dado una unidad registrada y una fecha de vencimiento válida, cuando guardo el vencimiento, entonces queda asociado a esa unidad y puede consultarse.

- [x] Dado un vencimiento ausente o con formato inválido, cuando intento guardarlo, entonces se informa el problema y no se sustituye un valor válido por el dato inválido.

- [x] Dado una unidad no vencida que entra en la ventana de alerta acordada, cuando transcurre el intervalo máximo de actualización acordado, entonces el personal recibe o puede ver la alerta por el canal definido, identificando la unidad y su vencimiento.

- [x] Dado una unidad que alcanza el límite de vencimiento acordado, cuando se ejecuta la actualización automática dentro del intervalo definido, entonces queda identificada como vencida sin intervención manual y deja de contarse como disponible según la definición de stock acordada.

- [x] Dado una unidad fuera de la ventana de alerta, cuando se actualiza la caducidad, entonces no se muestra como próxima a vencer.

## Pendientes de refinamiento con el Product Owner

Acordar anticipación de alerta, frecuencia máxima de actualización, fecha/hora de corte, zona horaria y canal de aviso. Esos parámetros deben tener valores concretos antes del sprint. Revisar división vertical si no cabe en un sprint.

## Definition of Ready

- [x] Rol, acción y beneficio revisados.
- [x] INVEST revisado con el equipo, incluidas independencia, dependencias y tamaño para un sprint.
- [x] Criterios de aceptación acordados y verificables.
- [x] Dudas y reglas de negocio resueltas con el Product Owner.
- [x] Estimación acordada por el equipo de desarrollo.

---

## #7 — [H7] Consultar alertas de sobreabastecimiento y sugerencias de redistribución

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/7) · Estado al consultar: closed · Asignación: Molonmlgg

## Historia de usuario

Como personal de casa donante, quiero visualizar alertas de exceso de stock y sugerencias de redistribución, para identificar excedentes que pueden derivarse antes de generar mermas.

## Datos del backlog original

- **ID:** H7
- **Valor:** Bajo
- **Riesgo:** Medio
- **Estimación original:** 10h
- **Depende de:** H6. 
- **Planificación:** Seleccionada en el sprint 1.
- **Trazabilidad:** RF-06.

## Criterios de aceptación propuestos

- [ ] Dado un umbral de abastecimiento definido y un stock que lo supera, cuando consulto las alertas, entonces se identifica el grupo y Rh afectado, el stock y el excedente respecto del umbral.

- [ ] Dado un excedente y destinos que cumplen las reglas de redistribución acordadas, cuando consulto el detalle, entonces se presentan las sugerencias que cumplen esas reglas sin ejecutar despachos.

- [ ] Dado datos de stock o umbrales inválidos, cuando se evalúa el abastecimiento, entonces se informa que no puede determinarse el excedente y no se presenta una sugerencia como válida.

- [ ] Dado un stock igual o inferior al umbral, cuando se actualizan las alertas, entonces no aparece una alerta vigente de sobreabastecimiento para ese grupo y Rh.

- [ ] Dado un excedente sin destinos válidos conocidos, cuando consulto la alerta, entonces se muestra el excedente y se informa que no hay una sugerencia de destino disponible.

## Pendientes de refinamiento con el Product Owner

Definir umbrales por grupo/Rh, unidades que cuentan como stock, centros candidatos y reglas de sugerencia. La alerta y la sugerencia no autorizan un traslado automático.

## Definition of Ready

- [ ] Rol, acción y beneficio revisados.
- [ ] INVEST revisado con el equipo, incluidas independencia, dependencias y tamaño para un sprint.
- [ ] Criterios de aceptación acordados y verificables.
- [ ] Dudas y reglas de negocio resueltas con el Product Owner.
- [ ] Estimación acordada por el equipo de desarrollo.

---

## #8 — [H1-T1] Definir los campos y validaciones del registro de donantes.

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/8) · Estado al consultar: closed · Asignación: Fefaarriagadav

**Descripción**
Identificar y documentar los campos necesarios para registrar un nuevo donante en el sistema Banco de Sangre. 
Definir cuáles son obligatorios, sus tipos de datos y las validaciones correspondientes, considerando la estructura de la tabla Donantes y los requisitos acordados con el equipo.

**Acceptance Criteria**
- Se identifican todos los campos necesarios para registrar un donante.
- Se especifican los campos obligatorios y opcionales.
- Se definen los tipos de datos y las validaciones de cada campo.
- Se documentan las reglas que impiden registros incompletos o inválidos.
- Se revisan y acuerdan las reglas con el equipo.

**Definition of Done**
- Documento de campos y validaciones completado.
- Reglas revisadas por otro integrante del equipo.
- Requisitos consistentes con los criterios de aceptación de HU01.
- Documentación incorporada al repositorio.

**Tiempo estimado**
1 Hora.

**Dependencias**
Ninguna

---

## #9 — [H2.1] Registrar y consultar el resultado final de elegibilidad

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/9) · Estado al consultar: closed · Asignación: garridotomas

**Historia padre:** [H2](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/2)

**Resultado:** El entrevistador autorizado registra `Apto` o `No apto` para un donante de H1 y puede consultar el resultado.

## Alcance

- Capturar solo el resultado final, sin respuestas del cuestionario clínico.
- Asociarlo al identificador correcto del donante.
- Validar que el donante exista y que el valor esté permitido.

## Criterios de aceptación

- [x] Dado un donante existente y un valor válido, cuando el entrevistador guarda el resultado, entonces queda asociado a ese donante y puede consultarse.
- [x] Dado un donante inexistente o un valor inválido, cuando se intenta guardar, entonces se informa el error y no se crea el resultado.
- [x] Dado un resultado registrado, cuando se consultan los datos guardados por esta función, entonces no incluyen respuestas clínicas.


---

## #10 — [H2.2] Restringir la modificación del resultado de elegibilidad

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/10) · Estado al consultar: closed · Asignación: garridotomas

**Historia padre:** [H2](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/2)

**Resultado:** Solo los roles autorizados pueden cambiar el resultado de elegibilidad.

## Alcance

- Verificar el permiso al guardar o cambiar el resultado.
- Conservar el valor anterior cuando se rechaza una operación.
- Informar al usuario el resultado de la operación.

## Criterios de aceptación

- [x] Dado un entrevistador autorizado, cuando actualiza un resultado válido, entonces se guarda el nuevo valor.
- [x] Dado un usuario sin permiso, cuando intenta cambiar el resultado, entonces se rechaza el cambio y se conserva el valor anterior.
- [x] Dado un cambio rechazado, cuando termina la operación, entonces se informa el motivo al usuario.


---

## #11 — [H1-T2] Implementar el almacenamiento de donantes en SQLite

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/11) · Estado al consultar: closed · Asignación: Fefaarriagadav

**Descripción**
Implementar la funcionalidad que permite guardar los datos de un nuevo donante en la tabla de Donantes de BancoDeSangre.db
La operación debe almacenar los datos proporcionados y evitar la creación de registros incompletos cuando ocurra un error.

**Acceptance Criteria**
- Se establece correctamente la conexión con BancoDeSangre.db.
- Se implementa la inserción de registros en la tabla "Donantes".
- Los datos se almacenan en sus columnas correspondientes
- Los registros se conversan después de cerrar la aplicación.
- Si ocurre un error durante la inserción, no queda un registro parcial.

**Definition of done**
- Función de inserción implementada.
- Inserción de prueba ejecutada correctamente.
- Persistencia de los registros verificada en SQLite.
- Manejo de errores implementados.
- Código revisado e integrado al proyecto.

**Tiempo estimado**
1 hora.

**Dependencias**
H1-T1: Definir los campos y validaciones del registro.

---

## #12 — [H4.1] Cambiar la habilitación y validar restricciones temporales

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/12) · Estado al consultar: closed · Asignación: garridotomas

**Historia padre:** [H4](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/4)

**Resultado:** El entrevistador autorizado cambia el estado de un donante entre `Habilitado`, `Inhabilitado temporal` e `Inhabilitado permanente`.

## Alcance

- Registrar y consultar el estado actual de un donante de H1.
- Pedir y validar el período de una inhabilitación temporal.
- Rechazar datos inválidos y cambios de usuarios sin permiso.

## Criterios de aceptación

- [x] Dado un entrevistador autorizado y datos válidos, cuando cambia el estado, entonces queda guardado y visible para el donante correcto.
- [x] Dada una restricción temporal sin período válido, cuando se intenta guardar, entonces se informa el error y se conserva el estado anterior.
- [x] Dado un usuario sin permiso, cuando intenta cambiar el estado, entonces se rechaza la operación y se conserva el estado anterior.


---

## #13 — [H4.2] Excluir de las convocatorias a donantes con restricción vigente

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/13) · Estado al consultar: closed · Asignación: garridotomas

**Historia padre:** [H4](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/4)

**Resultado:** La búsqueda de candidatos de H3 respeta el estado de habilitación actualizado en H4.

## Alcance

- Excluir donantes con inhabilitación temporal vigente o permanente.
- Reflejar los cambios de estado en la siguiente búsqueda.
- Combinar la habilitación con el resultado de H2 según la regla aprobada.

## Criterios de aceptación

- [x] Dado un donante con restricción vigente, cuando se buscan candidatos de su grupo y Rh, entonces no aparece.
- [x] Dado un cambio a inhabilitado, cuando se hace una nueva búsqueda, entonces el donante deja de aparecer.
- [x] Dado un cambio a habilitado, cuando se hace una nueva búsqueda, entonces se respetan las demás condiciones de elegibilidad acordadas.

**Depende de:** H3 para la integración con la búsqueda.

---

## #14 — [H1-T3] Implementar la generación de identificadores únicos (ID) para donantes.

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/14) · Estado al consultar: closed · Asignación: Fefaarriagadav

**Descripción**
Implementar la asignación automática de un identificador único (ID) para cada donante nuevo, utilizando una clave primaria en la tabla "Donantes".
El identificador permitirá reconocer al donante en las operaciones del Banco de Sangre sin mostrar innecesariamente sus datos personales.

**Acceptance Criteria**
- Cada nuevo donante recibe automáticamente un identificador.
- Dos donantes diferentes no pueden compartir el mismo identificador.
- El identificador queda almacenado en la base de datos.
- El sistema permite recuperar un donante mediante su identificador.
- El identificador generado se devuelve para mostrarlo después del registro.

**Definition of Done**
- Generación de identificadores implementada.
- Restricción de unicidad verificada en SQLite.
- Pruebas con múltiples donantes completadas.
- Recuperación mediante identificador comprobada.
- Código revisado e integrado al proyecto.

**Tiempo estimado**
1 hora.

**Dependencias**
H1-T2: Implementar el almacenamiento de donantes en SQLite

---

## #15 — [H1-T4] Construir la interfaz de registro de donantes.

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/15) · Estado al consultar: closed · Asignación: Fefaarriagadav

**Descripción**
Diseñar e implementar la pantalla de registro de donantes.
El formulario debe permitir al entrevistador ingresar los datos definidos para un nuevo donante, confirmar el registro y visualizar el identificador asignado cuando la operación se complete correctamente.

**Acceptance Criteria**
- La pantalla muestra los campos definidos para registrar donantes.
- Los campos están correctamente identificados mediante etiquetas.
- Existe un botón para confirmar el registro.
- El formulario permite ingresar los datos requeridos.
- Cuando el registro es exitoso, se muestra el identificador único generado.
- La interfaz muestra mensajes comprensibles al usuario.

**Definition of Done**
- Interfaz implementada.
- Formulario conectado con la funcionalidad de registro.
- Componentes visibles y correctamente organizados.
- Registro exitoso demostrado desde la interfaz.
- Código revisado e integrado al proyecto.

**Tiempo estimado**
2 horas.

**Dependencias**
H1-T1: Definir los campos y validaciones.
H1-T2: Implementar el almacenamiento.
H1-T3: Generar identificadores únicos.

---

## #16 — [H1-T5] Implementar validaciones y mensajes de error en el registro de donantes.

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/16) · Estado al consultar: closed · Asignación: Fefaarriagadav

**Descripción**
Implementar la validación de los datos ingresados en el formulario antes de guardar un donante.
El sistema debe identificar los campos obligatorios vacíos y los datos que no cumplan las reglas acordadas, mostrando mensaje que permitan corregirlos.

**Acceptance Criteria**
- El sistema detecta cuando falta un campo obligatorio.
- Se verifican los formatos y restricciones definidos para cada campo.
- Se muestra un mensaje que identifica el campo que debe corregirse.
- Los datos inválidos no se almacenan en la base de datos.
- El entrevistador puede corregir los datos y volver a intentar el registro.
- Un formulario válido permite continuar con el registro.

**Definition of Done**
- Validaciones implementadas.
- Mensajes de error integrados en la interfaz.
- Pruebas con campos vacíos realizadas.
- Pruebas con formatos inválidos realizadas.
- Confirmación de que no se guardan registros inválidos.
- Código revisado e integrado al proyecto.

**Tiempo estimado**
1 hora.

**Dependencias**
H1-T1: Definir los campos y validaciones.
H1-T4: Construir el formulario de registro.



---

## #17 — [H1-T6] Implementar la autorización por rol para registrar donantes.

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/17) · Estado al consultar: closed · Asignación: Fefaarriagadav

**Descripción**
Implementar el control de acceso que permita registrar nuevos donantes únicamente a los empleados autorizados.
El sistema debe consultar el rol del empleado en la tabla "Personal" y comprobar sus permisos antes de realizar el registro.
Para HU01 se considera autorizado al entrevistador, sujeto a las reglas de permisos acordadas con el equipo.

**Acceptance criteria**
- El sistema identifica al empleado que inició sesión.
- Se obtiene su rol desde la tabla "Personal".
- Un entrevistador autorizado puede registrar nuevos donantes.
- Un usuario sin permiso no puede registrar donantes.
- Un intento no autorizado muestra un mensaje de acceso denegado.
- Un intento no autorizado no genera modificaciones en la base de datos.
- La autorización se verifica antes de guardar, no solamente al mostrar el menú.

**Definition of Done**
- Validación del rol implementada.
- Integración con el inicio de sesión completada.
- Prueba con entrevistador autorizado realizada.
- Prueba con empleado sin permiso realizada.
- Ausencia de modificaciones no autorizadas verificada.
- Código revisado e integrado al proyecto.

**Tiempo estimado**
1 hora.

**Dependencias**
H1-T2: Implementar almacenamiento de donantes.
Funcionalidad de inicio de sesión y consulta de roles disponible.

---

## #18 — [H1-T7] Ejecutar pruebas de aceptación y documentar el registro de donantes.

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/18) · Estado al consultar: closed · Asignación: Fefaarriagadav

**Descripción**
Realizar pruebas funcionales de la historia HU01 para comprobar que el registro de donantes cumple todos los criterios de aceptación.
Documentar los resultados y preparar evidencias que permitan demostrar la funcionalidad durante la revisión del sprint.

**Acceptance Criteria**
- Se registra correctamente un donante con datos válidos.
- Se comprueba que el registro genera un identificador único.
- Se verifica que un campo obligatorio vacío impide el registro.
- Se verifica que un dato inválido impide el registro.
- Se comprueba que distintos donantes reciben identificadores diferentes.
- Se verifica que un usuario sin autorización no puede registrar donantes.
- Los resultados de las pruebas quedan documentados.

**Definition of Done**
- Todos los criterios de aceptación de HU01 comprobados.
- Pruebas funcionales ejecutadas exitosamente.
- Errores detectados corregidos o documentados.
- Código integrado y revisado por otro integrante.
- Documentación y evidencias actualizadas.
- Historia lista para ser demostrada en la Sprint Review.

**Tiempo estimado**
1 hora.

**Dependencias**
H1-T2: Almacenamiento en SQLite.
H1-T3: Generación de identificadores únicos.
H1-T4: Interfaz de registro.
H1-T5: Validaciones.
H1-T6: Autorización por rol.

---

## #20 — [H3-T1] Implementar búsqueda de donantes por grupo sanguíneo y factor Rh.

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/20) · Estado al consultar: closed · Asignación: Fefaarriagadav

**Descripción**
Implementar una consulta a la base de datos que permita buscar donantes utilizando filtros simultáneos de grupo sanguíneo y factor Rh.

**Acceptance Criteria**
- Se permite filtrar por grupos sanguíneos A, B, AB y O.
- Se permite filtrar por factor Rh positivo (+) y negativo (-).
- Los resultados coinciden con ambos filtros.
- Los filtros inválidos son rechazados antes de ejecutar la consulta.

**Definition of Done**
- Consulta implementada y funcional.
- Validación de filtros completada.
- Código comentado y revisado.

**Tiempo estimado**
1 hora.

---

## #21 — [H3-T2] Validar elegibilidad de los donantes.

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/21) · Estado al consultar: closed · Asignación: Fefaarriagadav

**Descripción**
Implementar la lógica necesaria para excluir de la búsqueda a donantes que no estén habilitados, considerando su elegibilidad y las restricciones vigentes según las reglas aprobadas por el Product Owner.

**Acceptance Criteria**
- Se incluyen únicamente donantes habilitados.
- Se excluyen donantes no aptos temporal o permanentemente.
- Se consideran las restricciones y evaluaciones vigentes según las reglas acordadas.
- Los donantes no habilitados no pueden seleccionarse para el envío de correos.

**Definition of Done**
- Lógica de elegibilidad implementada.
- Validaciones probadas con datos ficticios.
- Regla de habilitación confirmada con el Product Owner.
- Código documentado.

**Tiempo estimado**
1 hora

---

## #22 — [H3-T3] Crear interfaz de búsqueda y visualización de resultados.

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/22) · Estado al consultar: closed · Asignación: Fefaarriagadav

**Descripción**
Desarrollar una pantalla en CustomTkinter donde el entrevistador pueda seleccionar grupo sanguíneo y factor Rh, ejecutar la búsqueda y visualizar los donantes habilitados encontrados.

**Acceptance Criteria**
- La interfaz permite seleccionar grupo sanguíneo y factor Rh.
- Existe un botón para ejecutar la búsqueda.
- Se muestran solamente los donantes que cumplen los filtros y la regla de habilitación.
- Si no existen coincidencias, se muestra un mensaje informativo.
- Los filtros incompletos o inválidos generan mensajes de error en pantalla.

**Definition of Done**
- Interfaz gráfica implementada.
- Búsqueda integrada con la base de datos.
- Resultados mostrados correctamente.
- Navegación integrada al menú principal.
- Interfaz revisada en distintos tamaños de pantalla.

**Tiempo estimado**
1 hora.



---

## #23 — [H3-T4] Implementar selección de donantes y envío de correos.

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/23) · Estado al consultar: closed · Asignación: Fefaarriagadav

**Descripción**
Implementar una funcionalidad que permita al entrevistador seleccionar donantes habilitados desde los resultados de búsqueda y enviarles un correo electrónico de convocatoria, sin depender de alertas automáticas de stock.

**Acceptance Criteria**
- El entrevistador puede seleccionar uno o varios donantes habilitados.
- Se permite redactar o visualizar el mensaje antes de enviarlo.
- El envío requiere confirmación del entrevistador.
- Solo se envían correos a donantes que hayan autorizado recibir comunicaciones.
- Se muestra un mensaje de éxito o error después del intento de envío.
- No se envían correos automáticamente por cambios en el stock.

**Definition of Done**
- Selección de donantes implementada.
- Servicio de envío de correos integrado.
- Confirmación previa al envío implementada.
- Validación de destinatarios autorizados completada.
- Pruebas con correos ficticios realizadas.
- Código documentado.

**Tiempo estimado**
2 horas.




---

## #24 — [H3-T5] Realizar pruebas y documentar la funcionalidad.

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/24) · Estado al consultar: closed · Asignación: Fefaarriagadav

**Descripción**
Verificar mediante pruebas funcionales la búsqueda de donantes, los filtros de elegibilidad, la selección de destinatarios y el envío manual de correos electrónicos.

**Acceptance Criteria**
- Las búsquedas muestran únicamente donantes coincidentes y habilitados.
- Los filtros inválidos se rechazan correctamente.
- Las búsquedas sin coincidencias muestran un mensaje.
- No se seleccionan donantes con restricciones vigentes.
- Los correos se envían únicamente a destinatarios autorizados.
- Los errores de envío se muestran dentro de la interfaz.
- El envío de mensajes funciona independientemente del módulo de stock.

**Definition of Done**
- Pruebas de búsqueda y elegibilidad completadas.
- Pruebas de envío de correos realizadas.
- Errores corregidos.
- Evidencias documentadas.
- Código comentado y revisado.
- Funcionalidad preparada para revisión del Product Owner.

**Tiempo estimado**
1 hora.



---

## #26 — [H6-T1] Implementar registro de fecha de vencimiento, validaciones y actualización automática de estado vencido

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/26) · Estado al consultar: closed · Asignación: Matiasss-s

### Descripción
Desarrollar la lógica backend y validaciones para asociar fechas de vencimiento a las unidades de sangre de la casa donante, asegurando que unidades caducadas pasen a estado no disponible automáticamente.

### Tareas / Alcance
- [x] Implementar la persistencia de la fecha de vencimiento asociada a la unidad registrada.
- [x] Incorporar validaciones para fechas ausentes o con formato inválido, notificando el problema sin sobreescribir datos válidos.
- [x] Implementar el proceso automático (cron/task) que identifique unidades que alcanzaron la fecha/hora límite de caducidad y actualice su estado a "vencida" para sacarlas del stock disponible.

### Criterios de Aceptación Cubiertos
- [x] Registro exitoso de vencimiento asociado a la unidad.
- [x] Manejo de errores y rechazo de formatos de fecha inválidos o ausentes.
- [x] Cambio automático a estado vencido sin intervención manual al alcanzar la fecha límite.

### Horas Estimadas
 -  5.5 horas estimadas.

---

## #27 — [H6-T2] Implementar lógica de alertas anticipadas de caducidad y visualización en el sistema

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/27) · Estado al consultar: closed · Asignación: Matiasss-s

### Descripción
Construir el mecanismo de detección e informe de unidades próximas a caducar dentro del margen o ventana de alerta acordada para evitar la pérdida de stock.

### Tareas 
- [x] Definir e implementar el cálculo de la ventana de alerta (días/horas previas a la caducidad).
- [x] Desarrollar la consulta/servicio para filtrar las unidades no vencidas que entran en la ventana de alerta.
- [x] Exponer la información en la interfaz o canal de avisos definido para que el personal de la casa donante pueda identificar la unidad y su fecha de vencimiento.
- [x] Asegurar que las unidades fuera de la ventana de alerta no se muestren como próximas a vencer.

### Criterios de Aceptación Cubiertos
- [x] Notificación o visualización de unidades en ventana de alerta por el canal definido.
- [x] Exclusión visual de unidades que aún están fuera del rango de alerta.

### Horas Estimadas
- 4.5 horas estimadas.

---

## #28 — [H5-T1] Validar informacion de la donacion

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/28) · Estado al consultar: closed · Asignación: Oliverlulz

Descripción
Identificar y documentar los datos necesarios para registrar una donación.
Definir cuáles datos son obligatorios, sus tipos de datos y las validaciones correspondientes, considerando los requisitos acordados con el equipo.
Incorporar a el donante como información esencial para el registro de donación y aceptarlo solo si es donante valido.

Acceptance Criteria

    Se identifican todos los campos necesarios para registrar una donación.
    Se especifican los campos obligatorios y opcionales.
    Se definen los tipos de datos y las validaciones de cada campo.
    Se documentan las reglas que impiden registros incompletos o inválidos.
    Se revisan y acuerdan las reglas con el equipo.

Definition of Done

    Documento de campos y validaciones completado.
    Reglas revisadas por otro integrante del equipo.
    Requisitos consistentes con los criterios de aceptación de HU01.
    Documentación incorporada al repositorio.
    Avisar si algún requerimiento no es completado.

Tiempo estimado
2 Horas.

Dependencias
Ninguna

---

## #29 — [H5-T2] Crear identificadores únicos por donación y asociado a su respectivo donante

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/29) · Estado al consultar: closed · Asignación: Oliverlulz

Descripción
Crear el mecanismo para guardar la información de cada donación y crear un id único el cual se asocie a su respectivo donante.
El identificador permitirá reconocer a la donación y su donante en las operaciones del Banco de Sangre.

Acceptance Criteria

    Cada nueva donación tiene identificador.
    No hay dos identificadores iguales.
    El identificador representa la donación en la base de datos.
    El sistema permite identificar al donador respectivo a base de su asociacion.

Definition of Done

    Generación de identificadores implementada.
    Restricción de unicidad verificada en SQLite.
    Pruebas con múltiples donantes y donadores.
    Recuperación mediante identificador comprobada.
    Código revisado e integrado al proyecto.

Tiempo estimado
3 horas.

Dependencias
[H5-T1] Definir identificación de la donación

---

## #30 — [H5-T3] Incorporar a la interfaz el sistema de registro de donaciones

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/30) · Estado al consultar: closed · Asignación: Oliverlulz

Descripción
Implementar a la interfaz el registro de donaciones.
Permitir el acceso especializado a l@s Enfrermer@s, el incluir una donación obligatoria mente a un donante.

Acceptance Criteria

    La pantalla incluye una ventana de agregar donación.
    Existe un botón para confirmar el registro.
    Cuando el registro es exitoso, se muestra el identificador único generado.
    La interfaz muestra mensajes comprensibles al usuario.

Definition of Done

    Interfaz visible y intuitiva implementada.
    Validar si todos los datos obligatorios son incluidos.
    Código revisado e integrado al proyecto.

Tiempo estimado
3 horas.

Dependencias
[H5-T2] Crear identificadores únicos por donación y asociado a su respectivo donante

---

## #31 — [H5-T4] Incorporar interfaz de banco de donaciones

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/31) · Estado al consultar: closed · Asignación: Oliverlulz

Descripción
Implementar interfaz para el Banco de donaciones.
Permitir el acceso especializado a las clínicas y l@s Enfermer@s a la disponibilidad de sangre.
Mostrar todas las donaciones, separando entre las aptas, y no aptas (vencidas o usadas). 

Acceptance Criteria

La pantalla incluye una lista de las donaciones.
Existe la posibilidad de ver la información especifica de cada donación.
En un apartado separado se pueden ver las donaciones no aptas y porque.
La interfaz es comprensible a un usuario promedio.

Definition of Done

Interfaz visible y intuitiva implementada.
La interfaz no contiene errores visuales.
Código revisado e integrado al proyecto.

Tiempo estimado
2 horas.

Dependencias
Ninguna, si ya existe una base de datos.

---

## #37 — [H7-T1] Implementar evaluación de umbrales de stock  y alertas de sobreabastecimiento

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/37) · Estado al consultar: closed · Asignación: Molonmlgg

### Descripción
Desarrollar la lógica para evaluar el stock de sangre disponible contra los umbrales definidos, identificando los excedentes por grupo y factor Rh, además de manejar errores por datos inválidos o ausentes.

### Tareas / Alcance
- [x] Implementar la validación entre el stock actual y el umbral de abastecimiento por grupo y Rh.
- [x] Desarrollar el cálculo del excedente respecto del umbral cuando este es superado.
- [x] Incorporar el manejo de errores para informar al usuario cuando los datos de stock o umbrales sean inválidos.
- [x] Asegurar que los niveles de stock iguales o inferiores al umbral no levanten alertas vigentes.

### Criterios de Aceptación Cubiertos
- [x] Dado un umbral de abastecimiento definido y un stock que lo supera, cuando consulto las alertas, entonces se identifica el grupo y Rh afectado, el stock y el excedente respecto del umbral.
- [x] Dado datos de stock o umbrales inválidos, cuando se evalúa el abastecimiento, entonces se informa que no puede determinarse el excedente y no se presenta una sugerencia como válida.
- [x] Dado un stock igual o inferior al umbral, cuando se actualizan las alertas, entonces no aparece una alerta vigente de sobreabastecimiento para ese grupo y Rh.

### Horas Estimadas
- 5.0 horas estimadas.

---

## #38 — [H7-T2] Implementar sugerencias de redistribución

[Fuente en GitHub](https://github.com/Fefaarriagadav/Banco-de-sangre/issues/38) · Estado al consultar: closed · Asignación: Molonmlgg

### Descripción
Construir el mecanismo para cruzar el stock excedente con los destinos válidos para presentar sugerencias de redistribución al personal, asegurando que la acción sea solo informativa y contemple casos sin destinos disponibles.

### Tareas / Alcance
- [x] Implementar la lógica para identificar destinos que cumplen las reglas de redistribución acordadas para el excedente.
- [x] Exponer en la interfaz las sugerencias de redistribución.
- [x] Configurar la visualización para informar adecuadamente al usuario cuando se identifique un excedente pero no existan destinos válidos conocidos.

### Criterios de Aceptación Cubiertos
- [x] Dado un excedente y destinos que cumplen las reglas de redistribución acordadas, cuando consulto el detalle, entonces se presentan las sugerencias que cumplen esas reglas sin ejecutar despachos aún.
- [x] Dado un excedente sin destinos válidos conocidos, cuando consulto la alerta, entonces se muestra el excedente y se informa que no hay una sugerencia de destino disponible.

### Horas Estimadas
- 5.0 horas estimadas.

---
