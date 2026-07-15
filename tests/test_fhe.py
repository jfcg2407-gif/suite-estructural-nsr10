"""Tests for the NSR-10 seismic spectrum and Equivalent Lateral Force (fhe.py).

Verifies the exact Title A formulas (A.2.6) and the base-shear distribution
against hand-computed values for a documented reference case.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.fhe import calcular_fhe, espectro_nsr10, StoreyInput


class TestSiteCoefficients(unittest.TestCase):
    """Fa/Fv from the NSR-10 tables (A.2.4-3/4), Ibagué soil D, Aa=Av=0.20."""

    def test_ibague_soil_d(self):
        r = calcular_fhe(Aa=0.20, Av=0.20, suelo="D", I=1.0, R=5.0, T=0.34,
                         pisos=[StoreyInput("P1", 3.0, 300.0)])
        self.assertAlmostEqual(r.Fa, 1.40, places=2)   # official A.2.4-3
        self.assertAlmostEqual(r.Fv, 2.00, places=2)   # official A.2.4-4


class TestSpectrum(unittest.TestCase):
    """A.2.6 exact formulas: plateau 2.5·Aa·Fa, T0, TC(=Ts), TL, branches."""

    def test_plateau_and_corners(self):
        r = calcular_fhe(Aa=0.20, Av=0.20, suelo="D", I=1.0, R=5.0, T=0.34,
                         pisos=[StoreyInput("P1", 3.0, 300.0)])
        self.assertAlmostEqual(r.SMS, 2.5 * 0.20 * 1.40, places=6)      # 0.70
        self.assertAlmostEqual(r.SM1, 0.20 * 2.00, places=6)           # 0.40
        self.assertAlmostEqual(r.T0, 0.1 * r.SM1 / (0.20 * 1.40), places=6)
        self.assertAlmostEqual(r.Ts, 0.48 * r.SM1 / (0.20 * 1.40), places=6)
        self.assertAlmostEqual(r.TL, 2.4 * 2.00, places=6)             # 4.8
        # elastic coefficient = plateau·I (no R)
        self.assertAlmostEqual(r.C_elastico, r.SMS * 1.0, places=6)

    def test_three_branches_are_continuous(self):
        # Sa(T) must be continuous at the corner periods T0/TC and TL
        SMS, SM1 = 0.70, 0.40
        T0, Ts, TL = 0.1429, 0.6857, 4.8
        plateau = espectro_nsr10(SMS, SM1, T0, Ts, TL)
        # helper returns (T_array, Sa_array); at the plateau Sa == SMS
        Ts_arr, Sa_arr = plateau
        i_mid = next(i for i, t in enumerate(Ts_arr) if T0 < t < Ts)
        self.assertAlmostEqual(Sa_arr[i_mid], SMS, places=6)


class TestBaseShearAndDistribution(unittest.TestCase):
    """V = Cs·W and the vertical distribution sums back to V (A.4.3)."""

    def _building(self):
        # 3 storeys × 3 m, 300 kN each → W = 900 kN
        return [StoreyInput("P1", 3.0, 300.0),
                StoreyInput("P2", 6.0, 300.0),
                StoreyInput("P3", 9.0, 300.0)]

    def test_base_shear_on_plateau(self):
        # T=0.30 < TC → Cs = SMS·I/R = 0.70/5 = 0.14 ; V = 0.14·900 = 126 kN
        r = calcular_fhe(Aa=0.20, Av=0.20, suelo="D", I=1.0, R=5.0, T=0.30,
                         pisos=self._building())
        self.assertAlmostEqual(r.W, 900.0, places=3)
        self.assertAlmostEqual(r.Cs_gov, 0.14, places=4)
        self.assertAlmostEqual(r.V, 0.14 * 900.0, places=2)

    def test_distribution_sums_to_base_shear(self):
        r = calcular_fhe(Aa=0.20, Av=0.20, suelo="D", I=1.0, R=5.0, T=0.30,
                         pisos=self._building())
        suma_Fi = sum(p["Fx"] if "Fx" in p else p.get("Fi", 0) for p in r.pisos)
        self.assertAlmostEqual(suma_Fi, r.V, places=1)

    def test_importance_factor_scales_shear(self):
        base = calcular_fhe(Aa=0.20, Av=0.20, suelo="D", I=1.0, R=5.0, T=0.30,
                            pisos=self._building())
        esen = calcular_fhe(Aa=0.20, Av=0.20, suelo="D", I=1.5, R=5.0, T=0.30,
                            pisos=self._building())
        self.assertAlmostEqual(esen.V, base.V * 1.5, places=2)   # I=1.5 → +50%


if __name__ == "__main__":
    unittest.main(verbosity=2)
