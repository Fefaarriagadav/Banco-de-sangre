import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

RUTA_BD = Path(
    os.environ.get(
        "BANCO_SANGRE_BD",
        str(RAIZ / "BancoDeSangre.db"),
    )
)