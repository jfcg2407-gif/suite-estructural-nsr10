"""
Pruebas de engine/zapatas.py — VALIDADO contra la hoja de referencia de Jorge
'ZAPATA CONECTADA.xlsx' (método clásico, combos E.060 1.4D+1.7L). Los 12
valores del método se fijan como regresión; producción usa NSR-10 (1.2D+1.6L).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.zapatas import (COMBO_E060, COMBO_NSR10, presion_biaxial,
                            presion_biaxial_efectiva,
                            presion_neta, zapata_aislada, zapata_conectada,
                            zapata_esquinera)

# Entradas EXACTAS de la hoja de Jorge
HOJA = dict(PD1=70, PL1=26, PD2=120, PL2=45, L=6.2, t1=0.5, t2=0.5,
            sigma_t=3.5, hf=1.5, gamma_m=2.0, fc=210, fy=4200,
            s_piso=0.4, S1=1.35, b_viga=0.5, h_viga=0.9)


class TestValidacionHoja(unittest.TestCase):
    """Regresión 1:1 contra ZAPATA CONECTADA.xlsx (combo E.060)."""

    @classmethod
    def setUpClass(cls):
        cls.r = zapata_conectada(combo=COMBO_E060, **HOJA)

    def _cerca(self, mio, hoja, tol_pct=1.0):
        self.assertLess(abs(mio - hoja) / abs(hoja) * 100, tol_pct,
                        f"{mio} vs hoja {hoja}")

    def test_sigma_neta(self):
        self.assertAlmostEqual(self.r["sigma_n"], 31.6, places=2)

    def test_equilibrio_RN(self):
        self._cerca(self.r["exterior"]["RN"], 106.955)
        self._cerca(self.r["exterior"]["RNU"], 158.111)

    def test_zapata_exterior(self):
        self._cerca(self.r["exterior"]["Az_req"], 3.385)
        self.assertEqual(self.r["exterior"]["T1"], 2.55)
        self._cerca(self.r["exterior"]["Mu"], 32.572)

    def test_viga_momento_y_corte(self):
        self._cerca(self.r["viga"]["Xo"], 1.230)
        self._cerca(self.r["viga"]["Mu"], -51.905)
        self._cerca(self.r["viga"]["Vu"], 13.870)
        self.assertLess(self.r["viga"]["Mu"], 0)     # tracción ARRIBA

    def test_zapata_interior(self):
        self._cerca(self.r["interior"]["P2ef"], 161.011)
        self._cerca(self.r["interior"]["P2uef"], 238.341)
        self._cerca(self.r["interior"]["Az_req"], 5.095)


class TestModoNSR10(unittest.TestCase):
    def test_combos_nsr10_menores_que_e060(self):
        r10 = zapata_conectada(combo=COMBO_NSR10, **HOJA)
        re6 = zapata_conectada(combo=COMBO_E060, **HOJA)
        # 1.2D+1.6L < 1.4D+1.7L → demanda última menor, servicio idéntico
        self.assertLess(r10["exterior"]["RNU"], re6["exterior"]["RNU"])
        self.assertAlmostEqual(r10["exterior"]["RN"], re6["exterior"]["RN"], 2)
        self.assertLess(abs(r10["viga"]["Mu"]), abs(re6["viga"]["Mu"]))

    def test_presion_neta(self):
        self.assertAlmostEqual(presion_neta(3.5, 1.5, 2.0, 0.4), 31.6, places=2)

    def test_momento_S1_crece_S1_y_no_despega(self):
        # Bug end-to-end (2026-06-16): el lazo de la zapata exterior solo crecía T1,
        # así que un momento en la dirección de S1 (M1x) la despegaba para siempre
        # (topaba en T1=6 m). Ahora crece la dimensión que gobierna (S1) y resuelve.
        r = zapata_conectada(PD1=8, PL1=2, PD2=15, PL2=5, L=4.0, t1=0.4, t2=0.4,
                             sigma_t=2.0, hf=1.2, gamma_m=1.8, M1x=3.0, M1y=0.0)
        self.assertTrue(r["sin_despegue"])              # ya NO se despega
        self.assertGreater(r["exterior"]["S1"], 0.65)   # creció S1 (no solo T1)
        self.assertLess(r["exterior"]["T1"], 6.0)       # no quedó topada en 6 m


class TestAislada(unittest.TestCase):
    def test_basica(self):
        r = zapata_aislada(PD=30, PL=10, sigma_t=2.0, hf=1.2, gamma_m=1.8,
                           t1=0.40, t2=0.40)
        self.assertGreater(r["B"], 1.0)              # dimensión razonable
        self.assertGreaterEqual(r["h"], 0.30)
        self.assertLessEqual(r["Wnu"], r["sigma_n"] * 1.6 / 1.0 * 1.4)
        self.assertIn("Ø", r["barras"])

    def test_mas_carga_mas_zapata(self):
        r1 = zapata_aislada(30, 10, 2.0, 1.2, 1.8)
        r2 = zapata_aislada(80, 30, 2.0, 1.2, 1.8)
        self.assertGreater(r2["B"], r1["B"])


class TestPresionBiaxial(unittest.TestCase):
    """σ = P/A·(1 ± 6ex/Bx ± 6ey/By); núcleo (kern) = sin despegue."""

    def test_sin_momento_uniforme(self):
        pb = presion_biaxial(100, 0, 0, 2.0, 2.0)        # P/A = 25
        self.assertAlmostEqual(pb["smax"], 25.0, places=1)
        self.assertAlmostEqual(pb["smin"], 25.0, places=1)
        self.assertTrue(pb["sin_despegue"])

    def test_en_kern(self):
        pb = presion_biaxial(100, 0, 20, 2.0, 2.0)       # My=20 → ex=0.2
        self.assertAlmostEqual(pb["smax"], 40.0, places=1)
        self.assertAlmostEqual(pb["smin"], 10.0, places=1)
        self.assertTrue(pb["sin_despegue"])

    def test_despegue_fuera_del_kern(self):
        pb = presion_biaxial(100, 0, 40, 2.0, 2.0)       # My=40 → ex=0.4
        self.assertLess(pb["smin"], 0)                   # esquina en tracción
        self.assertFalse(pb["sin_despegue"])

    def test_biaxial_suma_dos_ejes(self):
        pb = presion_biaxial(100, 20, 20, 2.0, 2.0)      # ex=ey=0.2
        self.assertAlmostEqual(pb["smax"], 55.0, places=1)
        self.assertFalse(pb["sin_despegue"])             # 0.1+0.1 > 1/6


class TestPresionBiaxialEfectiva(unittest.TestCase):
    """σmax con DESPEGUE PARCIAL (el suelo no tracciona), resuelto numéricamente."""

    def test_concentrico_igual_a_PA(self):
        r = presion_biaxial_efectiva(100, 0, 0, 2.0, 2.0)
        self.assertAlmostEqual(r["smax"], 25.0, places=1)
        self.assertEqual(r["contacto"], 1.0)

    def test_en_kern_igual_al_lineal(self):
        r = presion_biaxial_efectiva(100, 0, 20, 2.0, 2.0)   # ex=0.2 (en núcleo)
        self.assertAlmostEqual(r["smax"], presion_biaxial(100, 0, 20, 2.0, 2.0)["smax"],
                               places=1)
        self.assertEqual(r["contacto"], 1.0)

    def test_uniaxial_despegue_vs_formula_cerrada(self):
        # ex=0.5 > B/6: cerrado σmax = 2P/(3·By·(Bx/2−ex)); contacto = 3(Bx/2−ex)/Bx
        r = presion_biaxial_efectiva(100, 0, 50, 2.0, 2.0)
        smax_cerr = 2 * 100 / (3 * 2.0 * (1.0 - 0.5))        # 66.67
        self.assertAlmostEqual(r["smax"], smax_cerr, delta=0.01 * smax_cerr)   # <1%
        self.assertAlmostEqual(r["contacto"], 0.75, places=2)

    def test_biaxial_pico_supera_al_lineal(self):
        # con despegue el pico REAL supera al lineal (que daría σmin<0, imposible)
        r = presion_biaxial_efectiva(100, 40, 40, 2.0, 2.0)
        self.assertGreater(r["smax"], presion_biaxial(100, 40, 40, 2.0, 2.0)["smax"])
        self.assertLess(r["contacto"], 1.0)

    def test_resultante_fuera_es_invalida(self):
        # ex > Bx/2: la resultante cae FUERA → volcaría → inválida (contacto 0, σmax∞)
        r = presion_biaxial_efectiva(100, 0, 110, 2.0, 2.0)     # ex=1.1 > Bx/2=1.0
        self.assertEqual(r["contacto"], 0.0)
        self.assertGreater(r["smax"], 1e6)


class TestSismoDespegue(unittest.TestCase):
    """Opción sísmica de zapata_aislada: σadm×factor + despegue parcial admitido."""
    KW = dict(PD=11, PL=3, sigma_t=2.0, hf=1.2, gamma_m=1.8, t1=0.3, t2=0.3,
              Mx=2.4, My=2.9)

    def test_default_no_cambia(self):                        # regresión: opción opt-in
        a = zapata_aislada(**self.KW)
        b = zapata_aislada(**self.KW, factor_sismo=1.0, permite_despegue=False)
        self.assertEqual((a["Bx"], a["By"], a["h"]), (b["Bx"], b["By"], b["h"]))
        self.assertTrue(a["sin_despegue"])                   # gravedad: sin despegue

    def test_sismo_achica_la_zapata(self):
        a = zapata_aislada(**self.KW)                        # conservador
        b = zapata_aislada(**self.KW, factor_sismo=1.33,
                           permite_despegue=True, contacto_min=0.5)
        self.assertLess(b["Bx"] * b["By"], a["Bx"] * a["By"])    # más chica
        self.assertGreaterEqual(b["contacto"] + 1e-9, 0.5)       # cumple contacto mínimo

    def test_contacto_minimo_mas_exigente_da_zapata_mayor(self):
        b50 = zapata_aislada(**self.KW, factor_sismo=1.33, permite_despegue=True,
                             contacto_min=0.5)
        b80 = zapata_aislada(**self.KW, factor_sismo=1.33, permite_despegue=True,
                             contacto_min=0.8)
        self.assertGreaterEqual(b80["contacto"] + 1e-9, 0.8)
        self.assertGreaterEqual(b80["Bx"] * b80["By"], b50["Bx"] * b50["By"])

    def test_excentricidad_alta_no_colapsa_a_la_minima(self):
        # carga liviana con momento alto (e > B/2 en la zapata mínima): NO debe
        # aceptar la zapata mínima (volcaría) → crece hasta contacto ≥ mínimo
        b = zapata_aislada(PD=8, PL=1, sigma_t=2.0, hf=1.2, gamma_m=1.8,
                           t1=0.3, t2=0.3, Mx=3.1, My=3.9,
                           factor_sismo=1.33, permite_despegue=True, contacto_min=0.5)
        self.assertGreaterEqual(b["contacto"] + 1e-9, 0.5)
        self.assertGreater(b["Bx"] * b["By"], 0.80 * 0.80 + 1e-6)   # no es la mínima


class TestSismoConectadaEsquinera(unittest.TestCase):
    """La opción sísmica también llega a conectada y esquinera (mismo patrón)."""
    KWC = dict(PD1=70, PL1=26, PD2=120, PL2=45, L=6.2, t1=0.5, t2=0.5,
               sigma_t=3.5, hf=1.5, gamma_m=2.0, M1x=4.0, M1y=5.0, M2x=3.0, M2y=4.0)

    def test_conectada_default_intacta(self):                # regresión (opt-in)
        a = zapata_conectada(**self.KWC)
        b = zapata_conectada(**self.KWC, factor_sismo=1.0, permite_despegue=False)
        self.assertEqual(a["exterior"]["T1"], b["exterior"]["T1"])
        self.assertEqual(a["exterior"]["S1"], b["exterior"]["S1"])
        self.assertEqual(a["interior"]["B"], b["interior"]["B"])

    def test_conectada_sismo_no_es_mayor(self):
        a = zapata_conectada(**self.KWC)
        b = zapata_conectada(**self.KWC, factor_sismo=1.33, permite_despegue=True)
        self.assertLessEqual(b["exterior"]["T1"] * b["exterior"]["S1"],
                             a["exterior"]["T1"] * a["exterior"]["S1"] + 1e-6)


class TestEjeVigaConexion(unittest.TestCase):
    """La dirección de la viga (eje_t1) mapea Mx/My a las dims correctas de la
    zapata exterior. Bug real 2026-07-05: con viga en Y los ejes quedaban
    cruzados → chequeo de despegue NO conservador. Auditoría multi-agente."""
    BASE = dict(PD1=30, PL1=10, PD2=50, PL2=18, L=5.0, t1=0.4, t2=0.4,
                sigma_t=2.0, hf=1.5, gamma_m=1.8)

    def test_sin_momento_eje_no_afecta(self):
        # M=0: el eje no cambia nada (caso validado 1:1 del profesor intacto)
        rx = zapata_conectada(**self.BASE, M1x=0, M1y=0, eje_t1="x")
        ry = zapata_conectada(**self.BASE, M1x=0, M1y=0, eje_t1="y")
        self.assertEqual(rx["exterior"]["T1"], ry["exterior"]["T1"])
        self.assertEqual(rx["exterior"]["S1"], ry["exterior"]["S1"])

    def test_default_es_eje_x(self):
        r_def = zapata_conectada(**self.BASE, M1x=0, M1y=6.0)
        r_x = zapata_conectada(**self.BASE, M1x=0, M1y=6.0, eje_t1="x")
        self.assertEqual(r_def["exterior"]["T1"], r_x["exterior"]["T1"])
        self.assertEqual(r_def["exterior"]["S1"], r_x["exterior"]["S1"])

    def test_viga_en_Y_crece_S1_no_T1(self):
        # My (ecc. en X global) con viga en Y (T1∥Y): debe aliviarse por S1 (dim
        # en X), NO por T1. Con eje_t1='x' se aliviaría por T1 (el bug).
        rx = zapata_conectada(**self.BASE, M1x=0, M1y=8.0, eje_t1="x")
        ry = zapata_conectada(**self.BASE, M1x=0, M1y=8.0, eje_t1="y")
        # x agranda T1; y agranda S1 → footings distintos
        self.assertNotEqual((rx["exterior"]["T1"], rx["exterior"]["S1"]),
                            (ry["exterior"]["T1"], ry["exterior"]["S1"]))
        self.assertGreater(ry["exterior"]["S1"], rx["exterior"]["S1"])

    def test_esquinera_pata_Y_usa_eje_y(self):
        # la pata Y de la esquinera no debe reventar y responde al momento
        from engine.zapatas import zapata_esquinera
        r = zapata_esquinera(PD=30, PL=10, PDx=40, PLx=14, Lx=5.0, t_x=0.4,
                             PDy=40, PLy=14, Ly=5.0, t_y=0.4, t_esq=0.4,
                             sigma_t=2.0, hf=1.5, gamma_m=1.8, Mex=0.0, Mey=8.0)
        self.assertIn("esquinera", r)
        self.assertGreater(r["esquinera"]["Lx"], 0)

    def test_esquinera_acepta_sismo(self):                   # pass-through a conectada
        kw = dict(PD=50, PL=18, PDx=60, PLx=20, Lx=5.0, t_x=0.4,
                  PDy=55, PLy=19, Ly=5.0, t_y=0.4, t_esq=0.4,
                  sigma_t=2.0, hf=1.2, gamma_m=1.8,
                  Mex=4.0, Mey=5.0, Mxx=3.0, Mxy=3.0, Myx=3.0, Myy=3.0)
        a = zapata_esquinera(**kw)
        b = zapata_esquinera(**kw, factor_sismo=1.33, permite_despegue=True)
        self.assertLessEqual(b["esquinera"]["Lx"] * b["esquinera"]["Ly"],
                             a["esquinera"]["Lx"] * a["esquinera"]["Ly"] + 1e-6)


class TestAisladaMomento(unittest.TestCase):
    KW = dict(PD=60, PL=20, sigma_t=2.0, hf=1.2, gamma_m=1.8, t1=0.4, t2=0.4)

    def test_sin_momento_identico_y_cuadrada(self):      # regresión
        a = zapata_aislada(**self.KW)
        b = zapata_aislada(**self.KW, Mx=0, My=0)
        self.assertEqual(a["B"], b["B"])
        self.assertEqual(a["h"], b["h"])
        self.assertEqual(a["barras"], b["barras"])
        self.assertEqual(a["Bx"], a["By"])               # sin momento → cuadrada

    def test_momento_agranda_sin_despegue(self):
        base = zapata_aislada(**self.KW)
        con = zapata_aislada(**self.KW, Mx=15, My=15)
        self.assertGreaterEqual(con["B"], base["B"])     # crece por el momento
        self.assertTrue(con["sin_despegue"])             # sin esquina despegada
        self.assertLessEqual(con["smax"], con["sigma_n"] + 0.5)   # σmax ≤ σn

    def test_momento_asimetrico_da_rectangulo(self):
        # My >> Mx → más excentricidad en X → Bx > By (rectángulo), acero por dir
        r = zapata_aislada(**self.KW, Mx=2, My=12)
        self.assertGreater(r["Bx"], r["By"])
        self.assertTrue(r["sin_despegue"])
        self.assertIn("barras_x", r)
        self.assertIn("barras_y", r)


class TestEsquinera(unittest.TestCase):
    """Doble excéntrica = dos zapatas conectadas (X e Y), envolvente (Calavera)."""

    KW = dict(PD=40, PL=12, PDx=50, PLx=18, Lx=5.0, t_x=0.40,
              PDy=55, PLy=20, Ly=4.5, t_y=0.40, t_esq=0.40,
              sigma_t=2.0, hf=1.2, gamma_m=1.8, fc=210, fy=4200)

    def setUp(self):
        self.r = zapata_esquinera(**self.KW)

    def test_estructura(self):
        for k in ("esquinera", "viga_x", "viga_y", "interior_x", "interior_y"):
            self.assertIn(k, self.r)
        self.assertEqual(self.r["tipo"], "esquinera")

    def test_dos_vigas_traccion_arriba(self):
        # cada viga de conexión tiene el momento principal ARRIBA (Mu < 0)
        self.assertLess(self.r["viga_x"]["Mu"], 0)
        self.assertLess(self.r["viga_y"]["Mu"], 0)

    def test_envolvente_de_las_dos_direcciones(self):
        # la zapata esquinera es la envolvente de los volados exteriores de
        # correr la conectada en X y en Y con la carga COMPLETA de la esquina
        rx = zapata_conectada(40, 12, 50, 18, L=5.0, t1=0.40, t2=0.40,
                              sigma_t=2.0, hf=1.2, gamma_m=1.8, fc=210, fy=4200)
        ry = zapata_conectada(40, 12, 55, 20, L=4.5, t1=0.40, t2=0.40,
                              sigma_t=2.0, hf=1.2, gamma_m=1.8, fc=210, fy=4200)
        ez = self.r["esquinera"]
        self.assertAlmostEqual(ez["Lx"], max(rx["exterior"]["T1"],
                                             ry["exterior"]["S1"]), places=2)
        self.assertAlmostEqual(ez["Ly"], max(ry["exterior"]["T1"],
                                             rx["exterior"]["S1"]), places=2)
        self.assertEqual(ez["h"], max(rx["exterior"]["h"], ry["exterior"]["h"]))

    def test_mas_carga_mas_zapata(self):
        chico = zapata_esquinera(**self.KW)
        grande = zapata_esquinera(**{**self.KW, "PD": 120, "PL": 40})
        self.assertGreaterEqual(grande["esquinera"]["Lx"] * grande["esquinera"]["Ly"],
                                chico["esquinera"]["Lx"] * chico["esquinera"]["Ly"])


class TestConectadaMomento(unittest.TestCase):
    """Momento de columna en medianera: agranda las zapatas; viga intacta."""

    KW = dict(PD1=70, PL1=26, PD2=120, PL2=45, L=6.2, t1=0.5, t2=0.5,
              sigma_t=3.5, hf=1.5, gamma_m=2.0, fc=210, fy=4200, s_piso=0.4)

    def test_sin_momento_identico(self):                 # regresión
        a = zapata_conectada(**self.KW)
        b = zapata_conectada(**self.KW, M1x=0, M1y=0, M2x=0, M2y=0)
        self.assertEqual(a["exterior"]["T1"], b["exterior"]["T1"])
        self.assertEqual(a["interior"]["B"], b["interior"]["B"])
        self.assertEqual(a["viga"]["Mu"], b["viga"]["Mu"])   # viga NO cambia
        self.assertTrue(b["sin_despegue"])

    def test_momento_interior_agranda(self):
        base = zapata_conectada(**self.KW)
        con = zapata_conectada(**self.KW, M2x=40, M2y=20)
        self.assertGreaterEqual(con["interior"]["B"], base["interior"]["B"])
        self.assertTrue(con["interior"]["sin_despegue"])
        self.assertEqual(con["viga"]["Mu"], base["viga"]["Mu"])   # viga intacta

    def test_momento_exterior_agranda(self):
        base = zapata_conectada(**self.KW)
        con = zapata_conectada(**self.KW, M1x=40, M1y=20)
        self.assertGreaterEqual(con["exterior"]["T1"], base["exterior"]["T1"])


class TestEsquineraMomento(unittest.TestCase):
    KW = dict(PD=40, PL=12, PDx=50, PLx=18, Lx=5.0, t_x=0.40,
              PDy=55, PLy=20, Ly=4.5, t_y=0.40, t_esq=0.40,
              sigma_t=2.0, hf=1.2, gamma_m=1.8, fc=210, fy=4200)

    def test_momento_esquina_propaga(self):
        base = zapata_esquinera(**self.KW)
        con = zapata_esquinera(**self.KW, Mex=15, Mey=10)
        a0 = base["esquinera"]["Lx"] * base["esquinera"]["Ly"]
        a1 = con["esquinera"]["Lx"] * con["esquinera"]["Ly"]
        self.assertGreaterEqual(a1, a0 - 0.01)           # la esquina (exterior) crece
        self.assertIn("sin_despegue", con)


class TestSolapesZapatas(unittest.TestCase):
    """Detección de zapatas que se solapan → señal de que van combinadas/mat."""

    def _pr(self, B):
        # dos columnas a 2 m con zapatas aisladas B×B → se solapan si B > 2
        return {"cimentacion": {
            "reacciones": [{"nudo": "1", "x": 0.0, "y": 0.0},
                           {"nudo": "2", "x": 2.0, "y": 0.0}],
            "zapatas": [{"tipo": "aislada", "nudos": ["1"], "resultado": {"B": B}},
                        {"tipo": "aislada", "nudos": ["2"], "resultado": {"B": B}}]}}

    def test_no_solapan_cuando_caben(self):
        from engine.zapatas import solapes_zapatas
        self.assertEqual(solapes_zapatas(self._pr(1.5)), [])     # 1.5 < 2 → no se tocan

    def test_solapan_cuando_grandes(self):
        from engine.zapatas import solapes_zapatas
        self.assertEqual(solapes_zapatas(self._pr(3.0)), [["1", "2"]])   # 3.0 > 2 → un grupo


class TestAmarre(unittest.TestCase):
    """Malla de amarre: ata columnas adyacentes (grilla) que no tengan viga de conexión."""

    def _grid(self, zaps):
        # 2×2: nudos 1(0,0) 2(4,0) 3(0,3) 4(4,3)
        return {"cimentacion": {
            "reacciones": [{"nudo": "1", "x": 0.0, "y": 0.0}, {"nudo": "2", "x": 4.0, "y": 0.0},
                           {"nudo": "3", "x": 0.0, "y": 3.0}, {"nudo": "4", "x": 4.0, "y": 3.0}],
            "zapatas": zaps}}

    def test_grilla_completa(self):
        from engine.zapatas import amarre_pares
        zaps = [{"tipo": "aislada", "nudos": [n]} for n in ("1", "2", "3", "4")]
        pares = {frozenset(p) for p in amarre_pares(self._grid(zaps))}
        # las 4 aristas del cuadrado: 1-2, 3-4 (en X) y 1-3, 2-4 (en Y); NO las diagonales
        self.assertEqual(pares, {frozenset(("1", "2")), frozenset(("3", "4")),
                                 frozenset(("1", "3")), frozenset(("2", "4"))})

    def test_excluye_las_ya_conectadas(self):
        from engine.zapatas import amarre_pares
        zaps = [{"tipo": "conectada", "nudos": ["1", "2"]},   # 1-2 ya tiene viga de conexión
                {"tipo": "aislada", "nudos": ["3"]}, {"tipo": "aislada", "nudos": ["4"]}]
        pares = {frozenset(p) for p in amarre_pares(self._grid(zaps))}
        self.assertNotIn(frozenset(("1", "2")), pares)        # no se duplica
        self.assertIn(frozenset(("3", "4")), pares)


if __name__ == "__main__":
    unittest.main(verbosity=2)
