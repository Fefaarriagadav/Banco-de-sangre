# Banco de Sangre

Aplicación de escritorio desarrollada en **Python, CustomTkinter y SQLite** para gestionar donantes, registrar resultados de elegibilidad médica y buscar donantes aptos para convocatorias de donación de sangre.

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

Si el proyecto incluye `main.py` como punto de entrada, también puede iniciarse mediante:

```powershell
python main.py
```

En macOS, puede ser necesario utilizar `python3` en lugar de `python`.

## Organización del proyecto

- `pantallas/`: interfaz de inicio de sesión, menú principal, registro de donantes (HU01), resultado médico (HU02) y búsqueda de donantes (HU03).
- `servicios/`: consultas, validaciones, permisos, elegibilidad y envío de correos electrónicos.
- `datos/`: configuración de la ruta de la base de datos e inicialización de tablas.
- `tests/`: pruebas automatizadas con bases temporales.
- `pantalla.py`: punto de entrada principal de la aplicación.
- `BancoDeSangre.db`: base de datos SQLite ubicada en la raíz.
- `.env`: configuración local de las credenciales para el envío de correos.
- `.gitignore`: archivos y credenciales excluidos del control de versiones.

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

### HU03: Búsqueda de donantes aptos y envío de correos

Permite al entrevistador:

- Filtrar donantes por grupo sanguíneo (A, B, AB u O) y factor Rh (positivo o negativo).
- Consultar donantes registrados como aptos.
- Visualizar una tabla con el ID, grupo sanguíneo y factor Rh.
- Consultar el total de donantes aptos encontrados.
- Limpiar los filtros y actualizar los resultados.
- Visualizar mensajes de validación que desaparecen automáticamente después de cinco segundos.
- Confirmar el envío de invitaciones por correo electrónico.
- Enviar mensajes individuales utilizando Gmail mediante `smtplib`.
- Visualizar la cantidad de correos aceptados para envío y los fallidos.

Las direcciones de correo se obtienen de la base de datos, pero no se muestran en la tabla de resultados.

La aplicación vuelve a consultar la elegibilidad antes de preparar el envío para reducir el riesgo de contactar a donantes cuyo estado haya cambiado.

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

### 3. Funcionamiento del envío

El flujo de HU03 es el siguiente:

1. El entrevistador selecciona el grupo sanguíneo y factor Rh.
2. Presiona el botón **Buscar**.
3. El sistema consulta SQLite y muestra los donantes aptos.
4. El entrevistador presiona **Enviar correo**.
5. El sistema vuelve a comprobar la elegibilidad registrada y solicita confirmación.
6. Al confirmar, se utiliza `servicios/enviar_correos.py` para enviar las invitaciones.
7. Se presenta el número de correos aceptados y fallidos.

Los envíos se realizan individualmente, evitando compartir las direcciones de correo entre destinatarios.

## Seguridad y consideraciones

- Las credenciales del correo se almacenan localmente en `.env`.
- No deben incluirse contraseñas ni información confidencial en el repositorio.
- Los correos electrónicos de los donantes permanecen ocultos en la tabla de HU03.
- El sistema requiere confirmación antes de iniciar el envío.
- Las invitaciones reales solo deben enviarse a donantes que hayan autorizado recibir comunicaciones.
- Antes de utilizar el envío con donantes reales, se deben completar las validaciones de consentimiento, vigencia de elegibilidad, prevención de duplicados y registro de envíos.
- El envío mediante SMTP todavía requiere mejoras de rendimiento para convocatorias masivas.

## Pruebas

Para ejecutar las pruebas automatizadas existentes:

```powershell
python -m unittest discover -s tests -v
```

Las pruebas están diseñadas para utilizar datos ficticios y bases temporales, sin modificar la base real.

El envío de correos debe probarse inicialmente con direcciones controladas por el equipo.

## Dependencias

Las dependencias externas del proyecto se encuentran en `requirements.txt`:

- `customtkinter`: interfaz gráfica.
- `python-dotenv`: lectura de variables de entorno.

Otras bibliotecas utilizadas, como `sqlite3`, `smtplib`, `email`, `os` y `pathlib`, forman parte de la biblioteca estándar de Python.

## H6-T1: Registro y actualización de vencimientos
### Funcionamiento
Cada registro de `DONACIONES` representa una unidad del modelo actual.

Al registrar una donación:
- La fecha de extracción se obtiene según la zona horaria `America/Santiago`.
- El vencimiento se calcula automáticamente desde la extracción.
- Se guarda la fecha de vencimiento y el estado `Disponible`.
- La confirmación del registro muestra el vencimiento calculado. (Aun hay que ver cuantos días le ponemos, ahora tiene 20 pero podrían ser hasta 35)
La vida útil se configura mediante `VIDA_UTIL_DIAS`, en
`servicios/vencimientos.py`. Su valor inicial es **20 días**, conservando
la regla previa del proyecto. Como dije arriba se debe hablar en conjunto que valor le damos.

La unidad permanece vigente durante toda su fecha de vencimiento.
A las 00:00 del día siguiente corresponde marcarla como `Vencida`.

### Validaciones y estados
El servicio permite guardar vencimientos con formato `DD-MM-AAAA`
y los almacena como `AAAA-MM-DD`.

Rechaza fechas ausentes, inexistentes o anteriores a la extracción,
sin sustituir un valor válido por un dato inválido.

Los registros con fechas ausentes o inconsistentes quedan como
`Pendiente de revisión` al ejecutar la actualización.

Las unidades usadas, descartadas o vencidas no se reactivan automáticamente.
Tampoco se permite extender la vigencia de una unidad que ya caducó.

### Actualización automática

La aplicación actualiza los vencimientos al iniciar y comprueba cada minuto
si cambió el día para ejecutar nuevamente el proceso.

También puede ejecutarse sin interfaz desde la raíz del proyecto:

```powershell
python -m servicios.vencimientos
```

En Windows se incluye el archivo:

```text
scripts/actualizar_vencimientos.bat
```

El archivo `.bat` no registra la tarea automáticamente: cada instalación
debe configurarla y verificar su ejecución.

### Pruebas

Ejecutar las pruebas de vencimientos:

```powershell
python -m unittest discover -s tests -p "test_vencimientos.py" -v
```

Ejecutar toda la suite:

```powershell
python -m unittest discover -s tests -v
```

Las pruebas de H6 utilizan bases temporales y cubren persistencia,
validaciones, cambios de mes y año, corte horario chileno,
migración y actualización automática.