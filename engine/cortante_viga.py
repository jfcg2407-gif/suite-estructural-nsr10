"""
engine/cortante_viga.py — Cortante de vigas por CAPACIDAD (NSR-10 C.21.5.4, DES).

El cortante de diseño de una viga con disipación especial (DES) NO es el del
análisis, sino el que aparece cuando la viga desarrolla su momento PROBABLE en
ambos extremos:
    Mpr = As · (1.25·fy) · (d − a/2),   a = As·1.25·fy / (0.85·f'c·b),  φ = 1
    Ve  = (Mpr⁻ + Mpr⁺) / ln  +  Vg          (Vg = cortante de gravedad)

En la zona de confinamiento (2h desde la cara), si el cortante sísmico ≥ ½·Ve y
la carga axial es baja, se toma Vc = 0 (C.21.5.4.2). Estribos:
    Vs = Ve/φ − Vc      (φ = 0.75);   Av·fy·d / s = Vs
    s_conf ≤ min(d/4, 6·db_long, 150 mm);  s_resto ≤ d/2;  1er estribo ≤ 50 mm.

Puro. M en kN·m, longitudes en m, f'c/fy en MPa, V en kN.
"""
import math

PHI_V = 0.75
AV_3_MM2 = 2 * 71.0       # estribo Ø3/8" (#3), 2 ramas (cm²·100 → mm²): 2×0.71 cm²


def momento_probable(As_cm2, b_m, d_m, fc, fy, factor_fy=1.25):
    """Momento del acero As con φ=1 y fy amplificado por `factor_fy` (kN·m):
    1.25 → Mpr (DES, C.21.5.4); 1.0 → Mn (DMO, C.21.3.3)."""
    if As_cm2 <= 0:
        return 0.0
    As = As_cm2 * 100.0                       # mm²
    b, d = b_m * 1000.0, d_m * 1000.0         # mm
    fyf = factor_fy * fy                      # MPa
    a = As * fyf / (0.85 * fc * b)            # mm
    return As * fyf * (d - a / 2.0) / 1e6     # N·mm → kN·m


def _redondea(s_mm, lo=50.0):
    return max(lo, math.floor(s_mm / 25.0) * 25.0)   # múltiplo de 25 mm, ≥ lo


def disenar_cortante(As_sup, As_inf, b_m, h_m, L_m, fc=28.0, fy=420.0,
                     Vg_kN=0.0, db_long_mm=15.9, recub=0.05, nivel="DES",
                     Av_mm2=AV_3_MM2, V2max_kN=None):
    """
    Cortante de viga por CAPACIDAD según el nivel de disipación:
      DES (C.21.5.4): Ve con Mpr (1.25·fy); Vc=0 en zona confinada si el sismo
        domina (≥ ½ Ve). SIN alternativa: Ve es siempre el de capacidad.
      DMO (C.21.3.3): Ve = el MENOR entre (a) capacidad con Mn (1.0·fy) y
        (b) el cortante de las combos con el sismo DUPLICADO (2E) — igual que
        ACI 318 pórticos intermedios. La ruta (b) salva las vigas de LUZ CORTA,
        donde (a) explota al dividir por ln (bug real 2026-07-12: 245 vigas
        condenadas por capacidad cuando ETABS, que aplica el mín, las pasa).
        Vc normal (la regla Vc=0 es de DES).
    As_sup / As_inf en la cara del apoyo (cm²); Vg_kN = cortante de gravedad que
    COEXISTE con el sismo = 1.2(D+SDL) + f_live·L (B.2.4: 0.5/1.0L, NO 1.6L — el
    sismo no coexiste con la viva plena; ACI 318-19 18.6.5 / NSR-10 C.21.5.4.1).
    V2max_kN = |V2| máx de las combos de RESISTENCIA (lector momentos_viga); la
    parte sísmica se reconstruye como E ≈ V2max − Vg → (b) = 2·V2max − Vg. Sin
    V2max (None/0) la ruta (b) no aplica (queda solo capacidad, conservador).
    Devuelve M (Mpr o Mn), Ve, Vc, Vs, la `ruta` que gobernó y estribos.
    """
    es_des = str(nivel).upper() == "DES"
    factor_fy = 1.25 if es_des else 1.0
    d_m = max(h_m - recub, 0.1)
    d, b = d_m * 1000.0, b_m * 1000.0          # mm
    ln = max(float(L_m or 4.0), 1.0)

    Mpr_neg = momento_probable(As_sup, b_m, d_m, fc, fy, factor_fy)
    Mpr_pos = momento_probable(As_inf, b_m, d_m, fc, fy, factor_fy)
    V_cap = (Mpr_neg + Mpr_pos) / ln           # cortante sísmico por capacidad (kN)
    Vg_abs = abs(float(Vg_kN or 0.0))
    Ve = V_cap + Vg_abs
    ruta = "capacidad"
    Ve_2E = None
    if not es_des and V2max_kN:
        # (b) C.21.3.3: combos con el sismo al DOBLE. E ≈ V2max − Vg (la parte
        # sísmica de la combo gobernante) → Vg + 2·(V2max − Vg) = 2·V2max − Vg.
        # El max() cubre la combo gobernante SIN sismo (no hay E que duplicar).
        v2 = abs(float(V2max_kN))
        Ve_2E = max(v2, 2.0 * v2 - Vg_abs)
        if Ve_2E < Ve:
            Ve, ruta = Ve_2E, "2E (C.21.3.3b)"

    # Vc = 0 en zona confinada si el sismo domina (≥ ½ Ve) — C.21.5.4.2 (SOLO DES)
    vc_cero = bool(es_des and Ve > 0 and V_cap >= 0.5 * Ve)
    Vc = 0.0 if vc_cero else 0.17 * math.sqrt(fc) * b * d / 1000.0   # kN
    Vs = max(Ve / PHI_V - Vc, 0.0)             # kN

    Vs_N = Vs * 1000.0
    s_req = (Av_mm2 * fy * d / Vs_N) if Vs_N > 0 else d / 2.0        # mm
    s_conf_max = min(d / 4.0, 6.0 * db_long_mm, 150.0)
    s_conf = _redondea(min(s_req, s_conf_max))
    s_resto = _redondea(min(s_req, d / 2.0))

    avisos = []
    # Tope C.11.4.7.9: Vs ≤ 0.66·√f'c·b·d (fc en MPa — 2.2 es el coef. de kg/cm²)
    Vn_max = (Vc + 0.66 * math.sqrt(fc) * b * d / 1000.0)
    if Ve / PHI_V > Vn_max:
        avisos.append("Ve excede la resistencia máxima a cortante — aumentar la sección.")

    return {
        "nivel": "DES" if es_des else "DMO",
        "Mpr_neg": round(Mpr_neg, 1), "Mpr_pos": round(Mpr_pos, 1),
        "V_cap": round(V_cap, 1), "Vg": round(Vg_abs, 1),
        "ruta": ruta, "Ve_2E": round(Ve_2E, 1) if Ve_2E is not None else None,
        "Ve": round(Ve, 1), "Vc": round(Vc, 1), "Vs": round(Vs, 1),
        "vc_cero": vc_cero, "s_conf_m": round(s_conf / 1000.0, 3),
        "s_resto_m": round(s_resto / 1000.0, 3), "zona_conf_m": round(2 * h_m, 2),
        "estribos": (f'Ø3/8" (#3): 1@5, @{s_conf/10:.1f} en 2h={2*h_m*100:.0f} cm, '
                     f'resto @{s_resto/10:.1f} cm'),
        "avisos": avisos,
    }
