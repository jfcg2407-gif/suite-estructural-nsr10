"""
Pruebas del cortante de vigas por capacidad (engine/cortante_viga.py):
momento probable (1.25·fy), Ve, Vc=0 si domina el sismo, separación de estribos.

Ejecutar:  python -m unittest discover -s tests
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import cortante_viga as CV


class TestMomentoProbable(unittest.TestCase):
    def test_mpr_30x50(self):
        # As=10 cm², 0.30x0.50 (d=0.45), fc28 fy420 → Mpr ≈ 216.9 kN·m
        self.assertAlmostEqual(CV.momento_probable(10.0, 0.30, 0.45, 28, 420),
                               216.9, delta=2.0)

    def test_mpr_cero(self):
        self.assertEqual(CV.momento_probable(0.0, 0.30, 0.45, 28, 420), 0.0)

    def test_mpr_crece_con_As(self):
        self.assertGreater(CV.momento_probable(12, 0.3, 0.45, 28, 420),
                           CV.momento_probable(6, 0.3, 0.45, 28, 420))


class TestCortante(unittest.TestCase):
    def test_estructura_y_estribos(self):
        r = CV.disenar_cortante(10.0, 6.0, 0.30, 0.50, 6.0, fc=28, fy=420, Vg_kN=40)
        for k in ("Mpr_neg", "Mpr_pos", "Ve", "Vc", "Vs", "s_conf_m", "s_resto_m",
                  "estribos", "zona_conf_m"):
            self.assertIn(k, r)
        self.assertGreater(r["Ve"], r["V_cap"])           # Ve = capacidad + gravedad
        self.assertIn('Ø3/8"', r["estribos"])

    def test_vc_cero_si_domina_sismo(self):
        # con Vg pequeño, el cortante por capacidad domina → Vc=0 (C.21.5.4.2)
        r = CV.disenar_cortante(10.0, 6.0, 0.30, 0.50, 5.0, fc=28, fy=420, Vg_kN=5)
        self.assertTrue(r["vc_cero"])
        self.assertEqual(r["Vc"], 0.0)

    def test_confinamiento_respeta_limites(self):
        r = CV.disenar_cortante(10.0, 6.0, 0.30, 0.50, 6.0, fc=28, fy=420,
                                Vg_kN=40, db_long_mm=15.9)
        d = 0.45
        # zona confinada s ≤ min(d/4, 6db, 150mm)
        self.assertLessEqual(r["s_conf_m"] - 1e-9, min(d / 4, 6 * 0.0159, 0.150))
        self.assertGreaterEqual(r["s_conf_m"], 0.05)       # ≥ 5 cm
        self.assertLessEqual(r["s_resto_m"] - 1e-9, d / 2)


class TestTopeVnMax(unittest.TestCase):
    """C.11.4.7.9: Vs ≤ 0.66·√f'c·b·d (MPa). El coef. viejo 2.2 (kg/cm²)
    inflaba el tope ×3.3 y el aviso de sección insuficiente nunca salía."""

    def test_avisa_cuando_excede_tope(self):
        # 0.25x0.40 (d=0.35), fc=21, As=20 cm² c/cara, luz corta 2 m:
        # Ve/φ ≈ 339 kN > 0.66·√21·b·d ≈ 265 kN → DEBE avisar
        r = CV.disenar_cortante(20.0, 20.0, 0.25, 0.40, 2.0, fc=21, fy=420,
                                Vg_kN=10)
        self.assertTrue(any("máxima" in a for a in r["avisos"]),
                        f"debió avisar sección insuficiente: {r['avisos']}")

    def test_no_avisa_caso_normal(self):
        r = CV.disenar_cortante(10.0, 6.0, 0.30, 0.50, 6.0, fc=28, fy=420,
                                Vg_kN=40)
        self.assertEqual(r["avisos"], [])


class TestNivelDMO(unittest.TestCase):
    """DMO (C.21.3.3): cortante por capacidad con Mn (1.0·fy), sin la regla Vc=0."""

    def test_mn_menor_que_mpr(self):
        mpr = CV.momento_probable(10.0, 0.30, 0.45, 28, 420)                  # 1.25fy
        mn = CV.momento_probable(10.0, 0.30, 0.45, 28, 420, factor_fy=1.0)    # 1.0fy
        self.assertLess(mn, mpr)

    def test_dmo_menor_cortante_y_sin_vc_cero(self):
        des = CV.disenar_cortante(10.0, 6.0, 0.30, 0.50, 5.0, fc=28, fy=420,
                                  Vg_kN=5, nivel="DES")
        dmo = CV.disenar_cortante(10.0, 6.0, 0.30, 0.50, 5.0, fc=28, fy=420,
                                  Vg_kN=5, nivel="DMO")
        self.assertLess(dmo["Ve"], des["Ve"])       # Mn < Mpr → menos cortante
        self.assertFalse(dmo["vc_cero"])            # Vc=0 es regla de DES
        self.assertGreater(dmo["Vc"], 0)
        self.assertEqual(dmo["nivel"], "DMO")


class TestRuta2E(unittest.TestCase):
    """DMO C.21.3.3: Ve = MENOR entre (a) capacidad con Mn y (b) combos con el
    sismo DUPLICADO (2·V2max − Vg). La (b) salva las vigas de LUZ CORTA, donde
    (a) explota al dividir por ln (bug real 2026-07-12: 245 vigas condenadas
    por capacidad cuando ETABS, que aplica el mín, las pasaba)."""

    def test_luz_corta_dmo_gobierna_2E(self):
        # viga corta (ln→1 m) con As alto: capacidad ≈ (Mn+Mn)/1 = enorme;
        # V2max real de combos = 60 kN, Vg = 20 → (b) = 2·60−20 = 100 kN
        r = CV.disenar_cortante(15.0, 15.0, 0.30, 0.50, 0.95, fc=21, fy=420,
                                Vg_kN=20, nivel="DMO", V2max_kN=60.0)
        self.assertEqual(r["Ve"], 100.0)
        self.assertIn("2E", r["ruta"])
        self.assertEqual(r["Ve_2E"], 100.0)
        self.assertEqual(r["avisos"], [])           # ya no excede el tope

    def test_luz_normal_gobierna_capacidad(self):
        # viga larga: capacidad (Mn/ln) es menor que 2E → gobierna (a)
        r = CV.disenar_cortante(10.0, 6.0, 0.30, 0.50, 6.0, fc=28, fy=420,
                                Vg_kN=40, nivel="DMO", V2max_kN=200.0)
        self.assertEqual(r["ruta"], "capacidad")
        self.assertEqual(r["Ve"], round(r["V_cap"] + 40.0, 1))

    def test_des_ignora_v2max(self):
        # DES (C.21.5.4) NO tiene la alternativa 2E: capacidad siempre
        des = CV.disenar_cortante(15.0, 15.0, 0.30, 0.50, 0.95, fc=21, fy=420,
                                  Vg_kN=20, nivel="DES", V2max_kN=60.0)
        self.assertEqual(des["ruta"], "capacidad")
        self.assertIsNone(des["Ve_2E"])
        self.assertGreater(des["Ve"], 100.0)

    def test_sin_v2max_queda_capacidad(self):
        # sin dato de combos la (b) no aplica (conservador, legacy)
        r = CV.disenar_cortante(15.0, 15.0, 0.30, 0.50, 0.95, fc=21, fy=420,
                                Vg_kN=20, nivel="DMO")
        self.assertEqual(r["ruta"], "capacidad")
        self.assertTrue(any("máxima" in a for a in r["avisos"]))

    def test_combo_sin_sismo_no_se_duplica(self):
        # V2max ≤ Vg (gobierna gravedad): (b) = max(V2, 2V2−Vg) = V2max
        r = CV.disenar_cortante(15.0, 15.0, 0.30, 0.50, 0.95, fc=21, fy=420,
                                Vg_kN=80, nivel="DMO", V2max_kN=80.0)
        self.assertEqual(r["Ve_2E"], 80.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
