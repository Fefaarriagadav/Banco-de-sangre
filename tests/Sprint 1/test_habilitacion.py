import os, shutil, sqlite3, sys, tempfile, unittest
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datos.basededatos import inicializar_base
from servicios import elegibilidad as e

F = lambda d: d.strftime("%d-%m-%Y")
HOY = date.today()


class PruebasH4(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(__file__)))
        self.bd = os.path.join(self.dir, "t.db")
        inicializar_base(self.bd)
        c = sqlite3.connect(self.bd)
        c.execute("INSERT INTO PERSONAL (ID_EMPLEADO, RUT, NOMBRE, ROL) VALUES (1,'1-9','Ana','Entrevistador')")
        c.execute("INSERT INTO PERSONAL (ID_EMPLEADO, RUT, NOMBRE, ROL) VALUES (2,'2-7','Luis','Enfermero')")
        for i in (10, 11):
            c.execute("""INSERT INTO DONANTES (ID,NOMBRE,APELLIDO,EDAD,SEXO,GRUPO_SANGUINEO,FACTOR_RH,PESO,EMAIL,ELEGIBLE,FECHA_DE_NACIMIENTO)
                         VALUES (?,?,?,30,'Masculino','A','+',70,?,'Donante apto','1996-01-01')""", (i, "N", "A", f"d{i}@x.cl"))
        c.commit(); c.close()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def estado(self, i=10):
        c = sqlite3.connect(self.bd)
        r = c.execute("SELECT ELEGIBLE, INHABILITACION_INICIO, INHABILITACION_FIN FROM DONANTES WHERE ID=?", (i,)).fetchone()
        c.close(); return r

    def guardar(self, res, ini=None, fin=None, emp=1, i=10):
        return e.guardar_resultado(i, res, emp, inicio=ini, fin=fin, ruta=self.bd)

    # H4.1 criterio 1
    def test_cambio_valido_queda_guardado_y_visible(self):
        self.guardar(e.TEMPORAL, F(HOY), F(HOY + timedelta(days=30)))
        self.assertEqual(self.estado(), (e.TEMPORAL, HOY.isoformat(), (HOY + timedelta(days=30)).isoformat()))
        d = e.consultar_donante(10, self.bd)
        self.assertIn("del", e.describir_estado(d["RESULTADO"], d["INICIO"], d["FIN"]))

    def test_permanente_y_habilitado_no_dejan_periodo(self):
        self.guardar(e.TEMPORAL, F(HOY), F(HOY + timedelta(days=5)))
        self.guardar(e.PERMANENTE)
        self.assertEqual(self.estado(), (e.PERMANENTE, None, None))
        self.guardar(e.TEMPORAL, F(HOY), F(HOY + timedelta(days=5)))
        self.guardar(e.APTO)
        self.assertEqual(self.estado(), (e.APTO, None, None))

    # H4.1 criterio 2 (período faltante / inválido conserva el estado)
    def test_periodo_invalido_conserva_estado(self):
        casos = [(None, None), (F(HOY), ""), ("", F(HOY)), ("31-02-2026", F(HOY)),
                 (F(HOY), F(HOY - timedelta(days=1))),          # fin < inicio
                 (F(HOY + timedelta(days=2)), F(HOY + timedelta(days=9))),  # inicio futuro
                 (F(HOY - timedelta(days=9)), F(HOY - timedelta(days=2))),  # fin pasado
                 ("abc", "def")]
        for ini, fin in casos:
            with self.assertRaises(ValueError, msg=(ini, fin)):
                self.guardar(e.TEMPORAL, ini, fin)
            self.assertEqual(self.estado(), (e.APTO, None, None))
        with e.conectar(self.bd) as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM HISTORIAL_HABILITACION").fetchone()[0], 0)

    def test_inicio_igual_a_fin_es_valido(self):
        self.guardar(e.TEMPORAL, F(HOY), F(HOY))
        self.assertEqual(self.estado()[0], e.TEMPORAL)

    # H4.1 criterio 3 / H4 criterio 4 (sin permiso)
    def test_sin_permiso_se_rechaza(self):
        with self.assertRaises(PermissionError):
            self.guardar(e.PERMANENTE, emp=2)
        with self.assertRaises(PermissionError):
            self.guardar(e.PERMANENTE, emp=999)
        self.assertEqual(self.estado(), (e.APTO, None, None))

    # H4.2 criterios
    def test_candidatos_excluyen_restriccion_vigente_y_reflejan_cambios(self):
        ids = lambda: sorted(r[0] for r in e.buscar_candidatos("A", "+", self.bd))
        self.assertEqual(ids(), [10, 11])
        self.guardar(e.TEMPORAL, F(HOY), F(HOY + timedelta(days=10)))
        self.assertEqual(ids(), [11])                       # temporal vigente
        self.guardar(e.PERMANENTE)
        self.assertEqual(ids(), [11])                       # permanente
        self.guardar(e.APTO)
        self.assertEqual(ids(), [10, 11])                   # vuelve a aparecer
        self.assertIsNotNone(e.candidato_vigente(10, "A", "+", self.bd))
        self.guardar(e.PERMANENTE)
        self.assertIsNone(e.candidato_vigente(10, "A", "+", self.bd))

    def test_restriccion_vencida_vuelve_a_aparecer(self):
        self.guardar(e.TEMPORAL, F(HOY), F(HOY + timedelta(days=10)))
        manana = HOY + timedelta(days=11)
        ids = [r[0] for r in e.buscar_candidatos("A", "+", self.bd, hoy=manana)]
        self.assertIn(10, ids)
        # el último día de la restricción todavía NO puede ser convocado
        ultimo = HOY + timedelta(days=10)
        self.assertNotIn(10, [r[0] for r in e.buscar_candidatos("A", "+", self.bd, hoy=ultimo)])

    def test_temporal_antiguo_sin_fechas_sigue_excluido(self):
        c = sqlite3.connect(self.bd)
        c.execute("UPDATE DONANTES SET ELEGIBLE='Donante NO apto temporalmente' WHERE ID=10"); c.commit(); c.close()
        self.assertNotIn(10, [r[0] for r in e.buscar_candidatos("A", "+", self.bd)])

    def test_historial(self):
        self.guardar(e.TEMPORAL, F(HOY), F(HOY + timedelta(days=3)))
        self.guardar(e.APTO)
        with e.conectar(self.bd) as c:
            filas = [tuple(fila) for fila in c.execute("SELECT ESTADO_ANTERIOR, ESTADO_NUEVO, EMPLEADO_ID FROM HISTORIAL_HABILITACION ORDER BY ID").fetchall()]
        self.assertEqual(filas, [(e.APTO, e.TEMPORAL, 1), (e.TEMPORAL, e.APTO, 1)])

    def test_migracion_sobre_base_real_no_pierde_datos(self):
        real = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "BancoDeSangre.db")
        copia = os.path.join(self.dir, "real.db"); shutil.copy(real, copia)
        def n():
            with e.conectar(copia) as c:
                return c.execute("SELECT COUNT(*) FROM DONANTES").fetchone()[0]
        antes = n(); inicializar_base(copia); inicializar_base(copia)  # idempotente
        self.assertEqual(antes, n())
        with e.conectar(copia) as c:
            cols = [r[1] for r in c.execute("PRAGMA table_info(DONANTES)")]
        self.assertIn("INHABILITACION_FIN", cols)


if __name__ == "__main__":
    unittest.main(verbosity=2)