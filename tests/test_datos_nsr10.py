"""
Pruebas de INTEGRIDAD de los datos NSR-10 (engine/nsr10_data.py).

Blindan las tablas oficiales contra ediciones erróneas — el bug de "18/22
ciudades mal" (Aa/Av equivocados, sub-dimensionamiento sísmico) ya ocurrió dos
veces. Estas pruebas fijan valores oficiales conocidos y validan rangos,
consistencia de claves y la coherencia entre el nombre de cada sistema (R₀=X) y
su valor.

Ejecutar:  python -m unittest discover -s tests
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import nsr10_data as D

# Conjunto válido de Aa/Av en NSR-10 (múltiplos de 0.05, Tabla A.2.3-2)
_VALIDOS = {round(0.05 * k, 2) for k in range(1, 11)}   # 0.05 … 0.50

# Valores OFICIALES (Tabla A.2.3-2) de capitales clave — regresión dura.
# Incluye los que ya estuvieron MAL alguna vez (Ibagué, Cúcuta).
_OFICIALES = {
    "Ibagué (Tolima)": (0.20, 0.20),
    "Cúcuta (N. Santander)": (0.35, 0.30),
    "Bogotá D.C.": (0.15, 0.20),
    "Medellín (Antioquia)": (0.15, 0.20),
    "Cali (Valle)": (0.25, 0.25),
    "Barranquilla (Atlántico)": (0.10, 0.10),
    "Quibdó (Chocó)": (0.35, 0.35),
}
_OTRA = "Otra (ingresar manual)"


class TestGrupoUso(unittest.TestCase):
    """Tabla A.2.5-1 y clasificación A.2.5.1 — auditoría 2026-07-11: los ejemplos
    estaban ROTADOS un grupo (hospitales en III, bomberos en IV) y el I de
    Grupo III decía 1.3. Oficial: I = 1.00 / 1.10 / 1.25 / 1.50; hospitales =
    Grupo IV (indispensables); bomberos/policía/colegios = Grupo III."""

    def test_coeficientes_oficiales(self):
        self.assertEqual(sorted(D.GRUPO_USO.values()), [1.00, 1.10, 1.25, 1.50])

    def test_i_por_grupo(self):
        por_grupo = {}
        for etiqueta, i_val in D.GRUPO_USO.items():
            m = re.match(r"Grupo (I{1,3}V?|IV)\b", etiqueta)
            self.assertIsNotNone(m, f"etiqueta sin grupo romano: {etiqueta}")
            por_grupo[m.group(1)] = i_val
        self.assertEqual(por_grupo,
                         {"I": 1.00, "II": 1.10, "III": 1.25, "IV": 1.50})

    def test_ejemplos_en_el_grupo_correcto(self):
        etiquetas = {re.match(r"Grupo (\w+)", k).group(1): k.lower()
                     for k in D.GRUPO_USO}
        self.assertIn("hospital", etiquetas["IV"])      # A.2.5.1.1 indispensables
        self.assertNotIn("hospital", etiquetas["III"])  # el bug: estaban acá
        self.assertIn("bomberos", etiquetas["III"])     # A.2.5.1.2 atención comunidad
        self.assertNotIn("bomberos", etiquetas["IV"])
        self.assertIn("colegios", etiquetas["III"])     # A.2.5.1.2 (d)


class TestCiudades(unittest.TestCase):
    def test_otra_presente_y_vacia(self):
        self.assertIn(_OTRA, D.CIUDADES)
        self.assertEqual(D.CIUDADES[_OTRA], (None, None))

    def test_32_capitales_mas_otra(self):
        reales = [k for k in D.CIUDADES if k != _OTRA]
        self.assertEqual(len(reales), 32)

    def test_aa_av_en_conjunto_valido(self):
        for ciudad, (aa, av) in D.CIUDADES.items():
            if ciudad == _OTRA:
                continue
            self.assertIn(round(aa, 2), _VALIDOS, f"Aa inválido en {ciudad}: {aa}")
            self.assertIn(round(av, 2), _VALIDOS, f"Av inválido en {ciudad}: {av}")

    def test_valores_oficiales_fijos(self):
        for ciudad, esperado in _OFICIALES.items():
            self.assertIn(ciudad, D.CIUDADES)
            self.assertEqual(D.CIUDADES[ciudad], esperado,
                             f"{ciudad}: A.2.3-2 oficial {esperado}")


class TestAeAd(unittest.TestCase):
    def test_mismas_claves_que_ciudades(self):
        self.assertEqual(set(D.AE_AD), set(D.CIUDADES))

    def test_otra_vacia(self):
        self.assertEqual(D.AE_AD[_OTRA], (None, None))

    def test_rangos_ae_ad(self):
        for ciudad, (ae, ad) in D.AE_AD.items():
            if ciudad == _OTRA:
                continue
            self.assertTrue(0.0 < ae <= 0.30, f"Ae fuera de rango en {ciudad}: {ae}")
            self.assertTrue(0.0 < ad <= 0.20, f"Ad fuera de rango en {ciudad}: {ad}")


class TestSistemas(unittest.TestCase):
    def test_otro_manual_none(self):
        otros = [k for k in D.SISTEMAS if D.SISTEMAS[k] is None]
        self.assertTrue(otros, "Debe existir una opción 'Otro' con R₀ manual (None)")

    def test_R0_del_nombre_coincide_con_valor(self):
        # El número embebido en 'R₀=X' DEBE ser igual al valor del diccionario.
        for nombre, r in D.SISTEMAS.items():
            m = re.search(r"R₀\s*=\s*([\d.]+)", nombre)
            if m:
                self.assertAlmostEqual(
                    float(m.group(1)), r, places=3,
                    msg=f"'{nombre}' dice R₀={m.group(1)} pero el valor es {r}")

    def test_R0_en_rango(self):
        for nombre, r in D.SISTEMAS.items():
            if r is None:
                continue
            self.assertTrue(1.0 <= r <= 8.0, f"R₀ fuera de rango en {nombre}: {r}")


class TestTablasFaFv(unittest.TestCase):
    SUELOS = {"A", "B", "C", "D", "E"}

    def test_claves_suelo(self):
        self.assertEqual(set(D.FA_TABLE), self.SUELOS)
        self.assertEqual(set(D.FV_TABLE), self.SUELOS)

    def test_referencias_anclas_oficiales(self):
        # Anclas OFICIALES de las Tablas A.2.4-3/4 (columnas <=0.1, 0.2, 0.3,
        # 0.4, >=0.5). Antes habia una grilla 0.05-0.40 con filas C/E CORRIDAS
        # (espectro -17%: inseguro) — corregido 2026-07-05.
        self.assertEqual(D.FA_AA, [0.10, 0.20, 0.30, 0.40, 0.50])
        self.assertEqual(D.FV_AV, [0.10, 0.20, 0.30, 0.40, 0.50])

    def test_longitud_filas(self):
        for s, row in {**D.FA_TABLE, **D.FV_TABLE}.items():
            self.assertEqual(len(row), 5, f"Fila {s} debe tener 5 valores")

    def test_valores_oficiales_de_la_norma(self):
        # Valores 1:1 de las Tablas A.2.4-3 (Fa) y A.2.4-4 (Fv)
        self.assertEqual(D.FA_TABLE["C"], [1.2, 1.2, 1.1, 1.0, 1.0])
        self.assertEqual(D.FA_TABLE["D"], [1.6, 1.4, 1.2, 1.1, 1.0])
        self.assertEqual(D.FA_TABLE["E"], [2.5, 1.7, 1.2, 0.9, 0.9])
        self.assertEqual(D.FV_TABLE["C"], [1.7, 1.6, 1.5, 1.4, 1.3])
        self.assertEqual(D.FV_TABLE["D"], [2.4, 2.0, 1.8, 1.6, 1.5])
        self.assertEqual(D.FV_TABLE["E"], [3.5, 3.2, 2.8, 2.4, 2.4])

    def test_roca_y_referencia(self):
        # Suelo A (roca dura) de-amplifica (0.8); suelo B es referencia (1.0)
        self.assertTrue(all(v == 0.8 for v in D.FA_TABLE["A"]))
        self.assertTrue(all(v == 1.0 for v in D.FA_TABLE["B"]))
        self.assertTrue(all(v == 0.8 for v in D.FV_TABLE["A"]))
        self.assertTrue(all(v == 1.0 for v in D.FV_TABLE["B"]))

    def test_amplificacion_no_creciente(self):
        # La amplificación NO crece al aumentar Aa/Av (a mayor sismo, menos Fa/Fv)
        for tabla in (D.FA_TABLE, D.FV_TABLE):
            for s, row in tabla.items():
                for i in range(len(row) - 1):
                    self.assertGreaterEqual(
                        row[i] + 1e-9, row[i + 1],
                        f"Suelo {s}: Fa/Fv debe ser no creciente ({row})")

    def test_rangos_fa_fv(self):
        for s, row in D.FA_TABLE.items():
            for v in row:
                self.assertTrue(0.8 <= v <= 2.5, f"Fa fuera de rango suelo {s}: {v}")
        for s, row in D.FV_TABLE.items():
            for v in row:
                self.assertTrue(0.8 <= v <= 3.5, f"Fv fuera de rango suelo {s}: {v}")


class TestZonaDisipacion(unittest.TestCase):
    def test_fronteras_zona(self):
        self.assertEqual(D.zona_amenaza(0.05, 0.05), "baja")
        self.assertEqual(D.zona_amenaza(0.10, 0.10), "baja")       # frontera
        self.assertEqual(D.zona_amenaza(0.10, 0.15), "intermedia")  # el MAYOR manda
        self.assertEqual(D.zona_amenaza(0.20, 0.20), "intermedia")  # frontera
        self.assertEqual(D.zona_amenaza(0.25, 0.25), "alta")
        self.assertEqual(D.zona_amenaza(0.35, 0.30), "alta")

    def test_dmo_en_alta_viola(self):
        v = D.validar_disipacion("Pórtico de concreto — DMO (R₀=5)", 0.25, 0.25)
        self.assertFalse(v["valida"])
        self.assertIn("VIOLA", v["mensaje"])

    def test_des_en_intermedia_valido_con_aviso(self):
        v = D.validar_disipacion("Pórtico de concreto — DES (R₀=7)", 0.20, 0.20)
        self.assertTrue(v["valida"])
        self.assertEqual(v["disipacion"], "DES")     # regresión: el regex DEBE
        self.assertIn("OBLIGA", v["mensaje"])        # leer DES del nombre real

    def test_minimo_justo(self):
        v = D.validar_disipacion("Pórtico de concreto — DMO (R₀=5)", 0.20, 0.20)
        self.assertTrue(v["valida"])

    def test_sistema_sin_etiqueta(self):
        v = D.validar_disipacion("Mampostería confinada (R₀=2)", 0.20, 0.20)
        self.assertIsNone(v["valida"])               # verificar manualmente

    def test_nivel_y_es_des(self):
        self.assertEqual(D.nivel_disipacion("Pórtico de concreto — DES (R₀=7)"), "DES")
        self.assertEqual(D.nivel_disipacion("Pórtico de concreto — DMO (R₀=5)"), "DMO")
        self.assertIsNone(D.nivel_disipacion("Mampostería confinada (R₀=2)"))
        # es_des: solo DES (los chequeos C.21.6/C.21.7 SOLO aplican ahí)
        self.assertTrue(D.es_des({"sismo": {"sistema": "Pórtico de concreto — DES (R₀=7)", "R": 7}}))
        self.assertFalse(D.es_des({"sismo": {"sistema": "Pórtico de concreto — DMO (R₀=5)", "R": 5}}))
        self.assertFalse(D.es_des({"sismo": {"R": 5}}))      # 'Otro' R bajo → no DES
        self.assertTrue(D.es_des({"sismo": {"R": 7}}))       # 'Otro' R alto → DES

    def test_sin_caracteres_de_control_en_fuente(self):
        # Regresión: un \\x08 (backspace) invisible en el regex lo rompía en
        # silencio (parecía correcto al leerlo). Ningún control char en el módulo.
        src = (Path(__file__).resolve().parent.parent /
               "engine" / "nsr10_data.py").read_text(encoding="utf-8")
        malos = [c for c in src if ord(c) < 32 and c not in "\n\r\t"]
        self.assertEqual(malos, [])


class TestCoherenciaFHE(unittest.TestCase):
    def test_interpolacion_exacta_en_tabulados(self):
        # En un Aa tabulado, _interpolar devuelve el valor de la tabla sin error.
        from engine.fhe import _interpolar
        for suelo in ("C", "D", "E"):
            self.assertAlmostEqual(
                _interpolar(D.FA_TABLE, D.FA_AA, suelo, 0.20),
                D.FA_TABLE[suelo][1], places=6)   # 0.20 es el índice 1 (anclas)


if __name__ == "__main__":
    unittest.main(verbosity=2)
