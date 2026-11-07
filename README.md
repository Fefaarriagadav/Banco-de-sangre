# Banco de Sangre

Aplicación de escritorio en Python, CustomTkinter y SQLite.

## Inicio

Desde la raíz del proyecto:

```powershell
python -m pip install -r requirements.txt
python main.py
```

También se conserva `python pantalla.py` como metodo para iniciar la app

## Organización

- `pantallas/`: ingreso, menú principal, registro H1 y resultado H2.
- `servicios/`: consultas, validaciones y permisos del resultado H2.
- `datos/`: ubicación de la base e inicialización de las tablas de H1.
- `tests/`: pruebas de H2 con bases temporales.
- `pantalla.py`: punto de entrada.
- `BancoDeSangre.db`: base existente, ubicada en la raíz.

```powershell
python -m unittest discover -s tests -v
```

Las pruebas usan datos ficticios y bases temporales; no modifican la base real.
