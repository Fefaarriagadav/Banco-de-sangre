# Banco de Sangre

Aplicación de escritorio desarrollada en **Python, CustomTkinter y SQLite** para gestionar donantes, registrar resultados de elegibilidad médica, buscar donantes aptos para convocatorias de donación de sangre y controlar el stock y los vencimientos de las unidades donadas.

## Tabla de contenidos

1. [Requisitos](#requisitos)
2. [Instalación e inicio](#instalación-e-inicio)
3. [Organización del proyecto](#organización-del-proyecto)
4. [Funcionalidades](#funcionalidades)
   - [HU01: Registro de donantes](#hu01-registro-de-donantes)
   - [HU02: Registro del resultado médico](#hu02-registro-del-resultado-médico)
   - [HU03: Búsqueda de donantes aptos y envío de correos](#hu03-búsqueda-de-donantes-aptos-y-envío-de-correos)
   - [H4: Habilitación temporal de donantes](#h4-habilitación-temporal-de-donantes)
   - [H5: Registro de donaciones](#h5-registro-de-donaciones)
   - [H6: Vencimientos, alertas y stock](#h6-vencimientos-alertas-y-stock)
   - [Alertas de sobreabastecimiento y redistribución](#alertas-de-sobreabastecimiento-y-redistribución)
5. [Configuración del correo electrónico](#configuración-del-correo-electrónico)
6. [Integración con H7](#integración-con-h7)
7. [Seguridad y consideraciones](#seguridad-y-consideraciones)
8. [Pruebas](#pruebas)
9. [Dependencias](#dependencias)
10. [Decisiones pendientes](#decisiones-pendientes)

## Requisitos

- Python 3.10 o superior.
- Las dependencias indicadas en `requirements.txt`.
- Una base de datos SQLite ubicada en la raíz del proyecto.
- Para utilizar el envío de correos, una cuenta Gmail configurada con verificación en dos pasos y contraseña de aplicación.

## Instalación e inicio

Desde la raíz del proyecto:

```powershell
python -m pip install -r requirements.txt
python pantalla.py
```

En macOS puede ser necesario utilizar `python3` en lugar de `python`.

> **Antes de actualizar una instalación existente:** respaldar `BancoDeSangre.db`. La inicialización agrega los elementos de H6 a la base existente sin borrar las donaciones, pero un respaldo previo evita sorpresas.

## Organización del proyecto

| Ruta | Descripción |
|------|-------------|
| `pantalla.py` | Punto de entrada principal de la aplicación. |
| `pantallas/` | Interfaz: inicio de sesión, menú principal, registro de donantes (HU01), resultado médico (HU02), búsqueda de donantes (HU03) y vistas de alertas y stock (H6). |
| `servicios/` | Consultas, validaciones, permisos, elegibilidad (`elegibilidad.py`), donaciones (`donaciones.py`), vencimientos (`vencimientos.py`), alertas de stock (`alertas_stock.py`) y envío de correos (`enviar_correos.py`). |
| `datos/` | Configuración de la ruta de la base de datos e inicialización de tablas. |
| `scripts/` | Utilidades de ejecución manual, como `actualizar_vencimientos.bat` (Windows). |
| `tests/` | Pruebas automatizadas con bases temporales. |
| `BancoDeSangre.db` | Base de datos SQLite ubicada en la raíz. |
| `.env` | Configuración local de las credenciales para el envío de correos. |
| `.gitignore` | Archivos y credenciales excluidos del control de versiones. |

## Funcionalidades

### HU01: Registro de donantes

Permite registrar donantes mediante un formulario en CustomTkinter, validando sus datos y almacenándolos en SQLite con un identificador único.

### HU02: Registro del resultado médico

Permite al entrevistador buscar un donante mediante su identificador y registrar su elegibilidad.

Los estados disponibles son:

- Donante apto.
- Donante NO apto temporalmente.
- Donante NO apto PERMANENTEMENTE.

La elegibilidad se actualiza directamente en la columna `ELEGIBLE` de la tabla `DONANTES`.

**Regla automática por peso:** si el peso del donante es **inferior a 50 kg**, el sistema lo califica automáticamente como *Donante NO apto temporalmente*, sin depender de la selección manual del entrevistador. [COMPLETAR: indicar en qué archivo se aplica la regla y si el valor de 50 kg es una constante configurable].

### HU03: Búsqueda de donantes aptos y envío de correos

Permite al entrevistador:

- Filtrar donantes por grupo sanguíneo (A, B, AB u O) y factor Rh (positivo o negativo).
- Consultar donantes registrados como aptos (se excluyen los que tienen una inhabilitación vigente, ver H4).
- Visualizar una tabla con el ID, grupo sanguíneo y factor Rh.
- Consultar el total de donantes aptos encontrados.
- Limpiar los filtros y actualizar los resultados.
- Visualizar mensajes de validación que desaparecen automáticamente después de cinco segundos.
- Confirmar el envío de invitaciones por correo electrónico.
- Enviar mensajes individuales utilizando Gmail mediante `smtplib`.
- Visualizar la cantidad de correos aceptados para envío y los fallidos.

Las direcciones de correo se obtienen de la base de datos, pero no se muestran en la tabla de resultados.

La aplicación vuelve a consultar la elegibilidad antes de preparar el envío para reducir el riesgo de contactar a donantes cuyo estado haya cambiado.

**Flujo de uso:**

1. El entrevistador selecciona el grupo sanguíneo y factor Rh.
2. Presiona **Buscar**.
3. El sistema consulta SQLite y muestra los donantes aptos.
4. El entrevistador presiona **Enviar correo**.
5. El sistema vuelve a comprobar la elegibilidad registrada y solicita confirmación.
6. Al confirmar, `servicios/enviar_correos.py` envía las invitaciones.
7. Se presenta el número de correos aceptados y fallidos.

Los envíos se realizan individualmente, evitando compartir las direcciones de correo entre destinatarios.

### H4: Habilitación temporal de donantes

Extiende el resultado médico de HU02. Solo el rol **Entrevistador** puede cambiar el estado de un donante; cualquier otro rol o empleado inexistente es rechazado con error de permisos y el estado no cambia.

- **NO apto temporalmente** exige un período con fecha de inicio y fecha de fin (`DD-MM-AAAA`). Se rechaza si falta alguna, si la fecha no existe (por ejemplo, 31-02), si el fin es anterior al inicio, si el inicio es futuro o si el fin ya pasó. Inicio y fin iguales son válidos. Ante cualquier rechazo se conserva el estado anterior y no se escribe historial.
- **Apto** y **NO apto PERMANENTEMENTE** no dejan período guardado.
- El período se guarda en `INHABILITACION_INICIO` e `INHABILITACION_FIN` de `DONANTES`.
- Cada cambio exitoso queda en la tabla `HISTORIAL_HABILITACION` (estado anterior, estado nuevo, fechas y empleado).
- La búsqueda de candidatos de HU03 excluye a los donantes con restricción vigente, incluido el último día del período. Cuando el período termina, el donante vuelve a aparecer. Los registros antiguos marcados como temporales y sin fechas siguen excluidos.
- La actualización de la base (`inicializar_base`) agrega las columnas e historial sin perder datos y puede ejecutarse varias veces sin efectos adicionales.

### H5: Registro de donaciones

Permite al **Enfermero** registrar la extracción de una unidad de sangre. Solo ese rol puede hacerlo: Entrevistador, empleados inexistentes o sin identificar son rechazados. Cada registro de `DONACIONES` representa una unidad del modelo actual y la cantidad se guarda en centímetros cúbicos (cc).

**Datos que se guardan:** identificador autoincremental, donante, cantidad, grupo sanguíneo y Rh (tomados del donante), fecha de extracción, fecha de vencimiento (ver H6), estado `Disponible` y ubicación.

**Validaciones:**

- El donante debe existir (ID entero positivo) y estar en estado *Donante apto*. Un donante NO apto, temporal o permanente, no puede donar.
- **Cantidad máxima por extracción: 450 cc.** Se acepta cualquier valor mayor que 0 hasta 450 (incluidos decimales como 0,1). Se rechazan vacío, texto, 0, negativos, valores superiores a 450 y valores no finitos.
- Si algo falla, no se escribe nada: la donación, el cambio de elegibilidad y el historial se guardan juntos o no se guarda ninguno.

**Ubicación de la donación:** cada unidad se asigna a un refrigerador según su grupo sanguíneo, sin importar el Rh, y se guarda en la columna `UBICACION`.

| Grupo sanguíneo | Ubicación |
|-----------------|-----------|
| O | Refrigerador 1 |
| A | Refrigerador 2 |
| B y AB | Refrigerador 3 |

La búsqueda de sangre por grupo y Rh (`buscar_sangre`) devuelve, para cada unidad, su ID, cantidad, grupo, Rh y ubicación.

**Inhabilitación automática tras la extracción:** al registrar una donación el donante pasa a *NO apto temporalmente* durante un período de espera que depende de su sexo:

| Sexo | Espera | Ejemplo (extracción el 13-11-2026) |
|------|--------|------------------------------------|
| Masculino | 3 meses | Inhabilitado hasta el 12-02-2027; habilitado desde el 13-02-2027 |
| Femenino | 4 meses | Inhabilitada hasta el 12-03-2027; habilitada desde el 13-03-2027 |

- La inhabilitación comienza el día de la extracción y termina el día anterior a la fecha de habilitación.
- Si el mes de destino tiene menos días, la fecha se ajusta al fin de mes (extracción masculina el 30-11-2026: habilitación el 28-02-2027).
- Un sexo no reconocido produce un error y no se registra la donación.
- También se actualiza `FECHA_ULTIMA_DONACION` y se agrega un registro a `HISTORIAL_HABILITACION`.
- Como el donante queda no apto, un segundo registro mientras dure la espera es rechazado.

### H6: Vencimientos, alertas y stock

Cada registro de `DONACIONES` representa una unidad del modelo actual.

#### H6-T1: Registro y actualización de vencimientos

**Al registrar una donación:**

- La fecha de extracción se obtiene según la zona horaria `America/Santiago`.
- El vencimiento se calcula automáticamente desde la extracción.
- Se guarda la fecha de vencimiento y el estado `Disponible`.
- La confirmación del registro muestra el vencimiento calculado.

La vida útil se configura mediante `VIDA_UTIL_DIAS` en `servicios/vencimientos.py`. Su valor inicial es **20 días**, conservando la regla previa del proyecto. Este valor es provisional (ver [Decisiones pendientes](#decisiones-pendientes)).

La unidad permanece vigente durante toda su fecha de vencimiento. A las 00:00 del día siguiente corresponde marcarla como `Vencida`.

**Validaciones y estados:**

- El servicio permite guardar vencimientos con formato `DD-MM-AAAA` y los almacena como `AAAA-MM-DD`.
- Rechaza fechas ausentes, inexistentes o anteriores a la extracción, sin sustituir un valor válido por un dato inválido.
- Los registros con fechas ausentes o inconsistentes quedan como `Pendiente de revisión` al ejecutar la actualización.
- Las unidades usadas, descartadas o vencidas no se reactivan automáticamente.
- Tampoco se permite extender la vigencia de una unidad que ya caducó.

**Actualización automática:**

Los vencimientos se actualizan:

- Al iniciar la aplicación.
- Al detectar un cambio de día mientras está abierta (se comprueba cada minuto).
- Antes de consultar el resumen o el detalle de stock.

No se ejecutan procesos con la aplicación cerrada. Al volver a abrirla se actualizan los vencimientos pendientes.

También puede ejecutarse sin interfaz desde la raíz del proyecto:

```powershell
python -m servicios.vencimientos
```

En Windows se incluye `scripts/actualizar_vencimientos.bat`. Este archivo **no** registra la tarea automáticamente ni instala una tarea programada: cada instalación debe configurarla y verificar su ejecución.

#### H6-T2: Alertas y stock en la ventana principal

**Panel "Próximos a expirar"** (lateral derecho de la ventana principal):

- Lista desplazable de unidades disponibles próximas a vencer.
- Identificador de unidad, grupo sanguíneo, factor Rh y vencimiento.
- Indicaciones "Vence hoy", "Vence mañana" o "En N días".
- Fecha y hora de la última actualización.
- Botón para actualizar manualmente.
- Orden por vencimiento: primero las unidades que requieren atención más pronto.

**Sección "Stocks"** (accesible desde el menú lateral):

- Totales disponibles para los ocho grupos sanguíneos y factores Rh.
- Cantidad de unidades y litros por grupo/Rh.
- Próximo vencimiento de cada grupo/Rh.
- Detalle de unidades con fechas de extracción y vencimiento.
- Tablas con desplazamiento y actualización manual y automática.

Las vistas de H6 se refrescan al mostrarse y al cambiar el minuto, además de permitir actualización manual.

**Reglas de disponibilidad y alertas:**

- El registro de H5 y la columna `CANTIDAD` utilizan centímetros cúbicos (cc). El resumen y la vista Stocks convierten esas cantidades a litros solo al mostrarlas (450 cc = 0,45 litros). Los datos almacenados no se modifican.
- La ventana de alerta inicial es de **7 días**, configurable mediante `DIAS_ALERTA` en `servicios/vencimientos.py`. Incluye hoy y el séptimo día.
- El stock disponible **excluye**:
  - Unidades vencidas, usadas, descartadas o reservadas.
  - Registros con fechas ausentes, inválidas o inconsistentes.
  - Extracciones futuras.
  - Cantidades ausentes, no positivas o no finitas.
- H6 conserva los datos originales inconsistentes para su revisión; los registros revisables se identifican como `Pendiente de revisión`.
- La fecha de vencimiento permanece vigente durante todo ese día; la unidad pasa a `Vencida` a partir del día siguiente, según la zona horaria `America/Santiago`.

### Alertas de sobreabastecimiento y redistribución

Detecta grupos sanguíneos con exceso de stock y sugiere hospitales a los que redistribuir unidades (`servicios/alertas_stock.py` y `pantallas/alertas_redistribucion.py`).

- Cada combinación grupo/Rh tiene un **umbral máximo** en la tabla `UMBRALES`.
- Se genera una alerta cuando las unidades `Disponible` superan el umbral (igual al umbral no alerta). La alerta indica stock, umbral y excedente.
- Un umbral en 0 alerta desde la primera unidad. Los grupos sin umbral y los umbrales negativos o vacíos se omiten.
- Solo se cuentan unidades en estado `Disponible`.
- El botón **Ver Destinos** muestra los hospitales de la tabla `HOSPITALES` que requieren ese grupo y Rh (con cantidad requerida mayor que 0). La consulta no modifica el inventario.
- **Actualizar Alertas** vuelve a consultar. Sin alertas, la pantalla indica "Niveles normales".

## Configuración del correo electrónico

La aplicación utiliza Gmail mediante el servidor SMTP y la biblioteca `smtplib`, incluida en Python.

### 1. Preparar la cuenta Gmail

Es necesario disponer de una cuenta Gmail con:

- Verificación en dos pasos activada.
- Una contraseña de aplicación generada para el sistema, cuando esta opción esté disponible.

### 2. Crear el archivo `.env`

En la raíz del proyecto, crear un archivo llamado `.env` con la siguiente estructura:

```dotenv
CORREO_REMITENTE=ejemplo@gmail.com
CONTRASENA_APP=contraseña_de_aplicacion
```

Reemplazar los valores de ejemplo por las credenciales correspondientes.

**Importante:** el archivo `.env` no debe subirse a GitHub. Debe estar incluido en `.gitignore`.

## Integración con H7

H7 debe obtener el stock vigente mediante el servicio de H6:

```python
from servicios.vencimientos import consultar_stock_detallado

datos = consultar_stock_detallado()

for total in datos["totales"]:
    grupo = total["grupo"]
    rh = total["rh"]
    unidades = total["unidades"]
    litros = total["litros"]
    proximo_vencimiento = total["proximo_vencimiento"]
```

## Seguridad y consideraciones

- Las credenciales del correo se almacenan localmente en `.env`.
- No deben incluirse contraseñas ni información confidencial en el repositorio.
- Los correos electrónicos de los donantes permanecen ocultos en la tabla de HU03.
- El sistema requiere confirmación antes de iniciar el envío.
- Las invitaciones reales solo deben enviarse a donantes que hayan autorizado recibir comunicaciones.
- Antes de utilizar el envío con donantes reales, se deben completar las validaciones de consentimiento, vigencia de elegibilidad, prevención de duplicados y registro de envíos.
- El envío mediante SMTP todavía requiere mejoras de rendimiento para convocatorias masivas.

## Pruebas

Ejecutar toda la suite:

```powershell
python -m unittest discover -s tests -v
```

Ejecutar solo las pruebas de vencimientos (H6):

```powershell
python -m unittest discover -s tests -p "test_vencimientos.py" -v
```

Las pruebas utilizan datos ficticios y bases temporales, sin modificar la base real. Las de H6 cubren persistencia, validaciones, cambios de mes y año, corte horario chileno, migración y actualización automática.

Archivos de prueba incluidos en `tests/`:

| Archivo | Qué verifica |
|---------|--------------|
| `test_registro_donantes.py` | Registro de donantes (HU01): persistencia, ID automático, y rechazo de nombre/apellido vacíos, fechas inválidas, peso no numérico o no positivo, email inválido, listas sin seleccionar, y rol no autorizado. |
| `test_elegibilidad.py` | Búsqueda de donantes, registro y actualización de resultados (HU02), permisos e historial. |
| `test_habilitacion.py` | H4: períodos de inhabilitación, rechazos que conservan el estado, candidatos vigentes, vencimiento de la restricción, historial y migración sobre una copia de `BancoDeSangre.db`. |
| `test_pedir_donaciones.py` | HU03: filtros, búsqueda, revalidación, confirmación y envío de correos (SMTP simulado, sin envíos reales). |
| `test_registro_donaciones.py` | H5: registro de donaciones, límite de 450 cc, ubicación por grupo, inhabilitación por sexo, fechas de fin de mes, permisos y reversión ante errores. |
| `test_vencimientos.py` | H6-T1: persistencia, validaciones, cambios de mes y año, corte horario chileno, migración y actualización automática. |
| `test_stock_vencimientos.py` | H6-T2: pantallas de Stocks y panel "Próximos a expirar", actualización y temporizadores. |
| `test_integracion_h5_h6.py` | Flujo completo H5 + H6: del formulario de donación al stock, vencimiento y estado `Vencida`. |
| `test_alertas_redistribucion.py` | Alertas de sobreabastecimiento, sugerencias de redistribución y su pantalla. |

Para ejecutar solo uno de estos archivos:

```powershell
python -m unittest discover -s tests -p "test_registro_donaciones.py" -v
```

La prueba de migración de `test_habilitacion.py` trabaja sobre una **copia** de `BancoDeSangre.db`, por lo que ese archivo debe existir en la raíz del proyecto.

El envío de correos debe probarse inicialmente con direcciones controladas por el equipo.

## Dependencias

Las dependencias externas del proyecto se encuentran en `requirements.txt`:

- `customtkinter>=5.2,<6`: interfaz gráfica.
- `python-dotenv>=1.0,<2`: lectura de variables de entorno.
- `tzdata>=2025.2`: disponibilidad de la zona horaria `America/Santiago` en Windows.

Otras bibliotecas utilizadas, como `sqlite3`, `smtplib`, `email`, `os` y `pathlib`, forman parte de la biblioteca estándar de Python.

## Decisiones pendientes

- **Vida útil de las unidades (`VIDA_UTIL_DIAS`):** actualmente es de 20 días, regla provisional heredada del proyecto. Podría ser de hasta 35 días; el equipo debe acordar y validar el valor definitivo.
- **Reglas de donación:** confirmar con el equipo (y con la normativa aplicable) la espera por sexo (3 meses hombres, 4 meses mujeres), la cantidad máxima de 450 cc y el umbral de peso de 50 kg.
