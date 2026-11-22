from calendar import monthrange

import customtkinter as ctk

from servicios.vencimientos import fecha_actual


MESES = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)

BORDE = ("#DDE5EF", "#354255")
TINTA = ("#193653", "#F1F5F9")
TEXTO_SECUNDARIO = ("#53677E", "#B4C2D3")
CAMPO = ("#EDF3F9", "#2D3C50")
BOTON_CAMPO = ("#DCE8F4", "#3B506A")
ESTILO_SELECTOR = {
    "fg_color": CAMPO, "button_color": BOTON_CAMPO, "button_hover_color": BORDE,
    "text_color": TINTA, "font": ("Arial", 13), "height": 34, "corner_radius": 8,
}


class SelectorProgramacion(ctk.CTkFrame):
    def __init__(self, padre, *, etiqueta_fecha, anio_editable=False):
        super().__init__(padre, fg_color="transparent")
        self.columnconfigure((0, 1), weight=1)
        for columna, texto in enumerate((etiqueta_fecha, "Hora de Santiago")):
            ctk.CTkLabel(self, text=texto, font=("Arial", 14, "bold"), text_color=TINTA).grid(
                row=0, column=columna, sticky="w",
            )

        hoy = fecha_actual()
        fecha = ctk.CTkFrame(self, fg_color="transparent")
        fecha.grid(row=1, column=0, sticky="w", pady=(3, 0), padx=(0, 16))
        self.dia = self._selector(fecha, 0, "Día", ["01"], f"{hoy.day:02}", 68)
        self.mes = self._selector(fecha, 1, "Mes", list(MESES), MESES[hoy.month - 1], 130)
        anios = [str(anio) for anio in range(hoy.year, min(hoy.year + 5, 10000))]
        self.anio = self._selector(
            fecha, 2, "Año", anios, str(hoy.year), 90, tipo=ctk.CTkComboBox,
            state="normal" if anio_editable else "readonly", border_color=BORDE, border_width=1,
        )
        self.mes.configure(command=self._actualizar_dias)
        self.anio.configure(command=self._actualizar_dias)
        if anio_editable:
            self.anio.bind("<FocusOut>", self._actualizar_dias)
        self._actualizar_dias()

        horario = ctk.CTkFrame(self, fg_color="transparent")
        horario.grid(row=1, column=1, sticky="w", pady=(3, 0))
        self.hora = self._selector(horario, 0, "Hora", [f"{hora:02}" for hora in range(24)], "—", 76)
        self.minuto = self._selector(horario, 1, "Minuto", [f"{minuto:02}" for minuto in range(60)], "00", 76)

    @staticmethod
    def _selector(padre, columna, nombre, valores, inicial, ancho, *, tipo=ctk.CTkOptionMenu, **opciones):
        ctk.CTkLabel(padre, text=nombre, font=("Arial", 12, "bold"), text_color=TEXTO_SECUNDARIO).grid(
            row=0, column=columna, sticky="w",
        )
        control = tipo(padre, values=valores, width=ancho, **ESTILO_SELECTOR, **opciones)
        control.set(inicial)
        control.grid(row=1, column=columna, sticky="w", padx=(0, 8), pady=(3, 0))
        return control

    def _actualizar_dias(self, _=None):
        try:
            ultimo_dia = monthrange(int(self.anio.get()), MESES.index(self.mes.get()) + 1)[1]
        except ValueError:
            return
        dias = [f"{dia:02}" for dia in range(1, ultimo_dia + 1)]
        self.dia.configure(values=dias)
        if self.dia.get() not in dias:
            self.dia.set("—")

    def obtener(self):
        if self.dia.get() == "—":
            raise ValueError("Selecciona un día válido para el mes elegido.")
        if self.hora.get() == "—":
            raise ValueError("Selecciona la hora del traslado.")
        fecha = f"{self.dia.get()}-{MESES.index(self.mes.get()) + 1:02}-{self.anio.get().strip()}"
        horario = f"{self.hora.get()}:{self.minuto.get()}"
        return fecha, horario

    def limpiar_horario(self):
        self.hora.set("—")
        self.minuto.set("00")
