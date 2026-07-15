"""
Motor de cálculo FHE — NSR-10 Capítulo A.4.
"""
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from engine.nsr10_data import FA_AA, FA_TABLE, FV_AV, FV_TABLE


@dataclass
class StoreyInput:
    nombre: str
    altura_acum: float   # altura acumulada desde la base (m)
    peso: float          # Wi (kN)


@dataclass
class FHEResultado:
    # Parámetros de sitio
    Aa: float; Av: float
    Fa: float; Fv: float
    SMS: float; SM1: float
    T0: float; Ts: float; TL: float

    # Coeficiente sísmico
    T: float
    I: float; R: float
    Cs: float; Cs_min: float; Cs_max: float
    Cs_gov: float
    # Coeficiente ELÁSTICO = meseta del espectro = 2.5·Aa·Fa·I (SIN R). Estilo Jorge:
    # el User Coefficient en ETABS usa este valor; la reducción por R va en el
    # factor de las combinaciones (1/R). Así el caso es elástico → derivas directas.
    C_elastico: float

    # Peso y cortante base
    W: float
    V: float

    # Distribución por piso
    pisos: list     # lista de dicts con Fi, Vi_acum, etc.
    k: float


def _interpolar(tabla: dict, ref_vals: list, suelo: str, val: float) -> float:
    """Interpolación lineal en la tabla Fa o Fv."""
    row = tabla[suelo]
    if val <= ref_vals[0]:
        return row[0]
    if val >= ref_vals[-1]:
        return row[-1]
    for i in range(len(ref_vals) - 1):
        if ref_vals[i] <= val <= ref_vals[i + 1]:
            t = (val - ref_vals[i]) / (ref_vals[i + 1] - ref_vals[i])
            return row[i] + t * (row[i + 1] - row[i])
    return row[-1]


def interpolar_detalle(tabla: dict, ref_vals: list, suelo: str, val: float) -> dict:
    """
    Igual que _interpolar pero devuelve el DETALLE del cálculo para mostrarlo:
        {valor, exacto, x0, x1, y0, y1}
    exacto=True si el valor está tabulado directamente (sin interpolación).
    """
    row = tabla[suelo]
    if val <= ref_vals[0]:
        return {"valor": row[0], "exacto": True, "x0": ref_vals[0], "x1": None,
                "y0": row[0], "y1": None}
    if val >= ref_vals[-1]:
        return {"valor": row[-1], "exacto": True, "x0": ref_vals[-1], "x1": None,
                "y0": row[-1], "y1": None}
    for i, rv in enumerate(ref_vals):
        if abs(val - rv) < 1e-9:
            return {"valor": row[i], "exacto": True, "x0": rv, "x1": None,
                    "y0": row[i], "y1": None}
    for i in range(len(ref_vals) - 1):
        if ref_vals[i] < val < ref_vals[i + 1]:
            t = (val - ref_vals[i]) / (ref_vals[i + 1] - ref_vals[i])
            v = row[i] + t * (row[i + 1] - row[i])
            return {"valor": v, "exacto": False,
                    "x0": ref_vals[i], "x1": ref_vals[i + 1],
                    "y0": row[i], "y1": row[i + 1]}
    return {"valor": row[-1], "exacto": True, "x0": ref_vals[-1], "x1": None,
            "y0": row[-1], "y1": None}


def calcular_fhe(
    Aa: float,
    Av: float,
    suelo: str,           # "A"-"E"
    I: float,
    R: float,
    T: float,             # período fundamental (s)
    pisos: list,          # lista de StoreyInput
    TL: Optional[float] = None,   # si None → 2.4·Fv (NSR-10 A.2.6.1.2)
    Fa_manual: Optional[float] = None,
    Fv_manual: Optional[float] = None,
) -> FHEResultado:

    # ── Coeficientes de sitio ─────────────────────────────────────────────────
    if suelo == "F":
        raise ValueError("Suelo tipo F requiere evaluación específica (NSR-10 A.2.4).")

    Fa = Fa_manual if Fa_manual else _interpolar(FA_TABLE, FA_AA, suelo, Aa)
    Fv = Fv_manual if Fv_manual else _interpolar(FV_TABLE, FV_AV, suelo, Av)

    # ── Espectro NSR-10 A.2.6 (fórmulas EXACTAS del Título A) ────────────────
    #   Meseta:      Sa = 2.5·Aa·Fa·I              (T0 ≤ T ≤ TC)
    #   Descendente: Sa = 1.2·Av·Fv·I / T          (TC < T ≤ TL)
    #   Largo:       Sa = 1.2·Av·Fv·TL·I / T²      (T > TL)
    #   T0 = 0.1·Av·Fv/(Aa·Fa) · TC = 0.48·Av·Fv/(Aa·Fa) · TL = 2.4·Fv
    SMS  = 2.5 * Aa * Fa           # meseta (sin I)
    SM1  = Av * Fv
    T0   = 0.1 * SM1 / (Aa * Fa)
    Ts   = 0.48 * SM1 / (Aa * Fa)  # TC de la norma (nombre Ts por compat.)
    if TL is None:
        TL = 2.4 * Fv              # A.2.6.1.2

    # ── Coeficiente sísmico Cs = Sa·I/R (A.4.2.2 con A.2.6) ─────────────────
    if T <= Ts:
        Cs = SMS * I / R
    elif T <= TL:
        Cs = 1.2 * SM1 * I / (R * T)
    else:
        Cs = 1.2 * SM1 * TL * I / (R * T**2)

    # NSR-10 no define un Cs mínimo tipo ASCE (0.044·SMS); el espectro A.2.6
    # gobierna directamente. Se mantiene el campo en 0 por compatibilidad.
    Cs_min = 0.0
    Cs_max = SMS * I / R           # tope físico (meseta reducida)
    Cs_gov = min(Cs, Cs_max)

    # Coeficiente elástico = meseta del espectro = 2.5·Aa·Fa·I (sin R).
    C_elastico = SMS * I

    # ── Peso sísmico total ────────────────────────────────────────────────────
    W = sum(p.peso for p in pisos)
    V = Cs_gov * W

    # ── Exponente k (NSR-10 A.4.3.2) ─────────────────────────────────────────
    if T <= 0.5:
        k = 1.0
    elif T >= 2.5:
        k = 2.0
    else:
        k = 1.0 + (T - 0.5) / 2.0   # interpolación lineal

    # ── Distribución de fuerzas por piso (NSR-10 A.4.3.2) ────────────────────
    denominador = sum(p.peso * (p.altura_acum ** k) for p in pisos)

    resultados_pisos = []
    V_acum = 0.0
    for p in reversed(pisos):   # Story3 → Story1
        wh_k = p.peso * (p.altura_acum ** k)
        Fx   = V * wh_k / denominador
        V_acum += Fx
        resultados_pisos.append({
            "piso":       p.nombre,
            "h_acum":     p.altura_acum,
            "Wi":         p.peso,
            "Wi_hi_k":    wh_k,
            "Fx":         Fx,
            "Vi":         V_acum,
        })
    resultados_pisos.reverse()   # orden Story1 → Story3

    return FHEResultado(
        Aa=Aa, Av=Av, Fa=Fa, Fv=Fv,
        SMS=SMS, SM1=SM1, T0=T0, Ts=Ts, TL=TL,
        T=T, I=I, R=R,
        Cs=Cs, Cs_min=Cs_min, Cs_max=Cs_max, Cs_gov=Cs_gov,
        C_elastico=C_elastico,
        W=W, V=V,
        pisos=resultados_pisos,
        k=k,
    )


def espectro_nsr10(SMS: float, SM1: float, T0: float, Ts: float,
                   TL: Optional[float] = None, n_pts: int = 300):
    """Devuelve (T[], Sa[]) del espectro de diseño NSR-10 A.2.6 (exacto).
    Si TL es None, se calcula como 2.4·Fv = 2.4·SM1/Av (A.2.6.1.2).
    """
    if TL is None:
        # Si no se proporciona, calcular TL de forma coherente
        # Nota: sin Av, usamos un valor conservador = 2.4 s
        TL = 2.4
    T_arr = np.linspace(0.0, max(min(4.0, TL * 1.2), Ts * 2.5), n_pts)
    Sa    = np.zeros(n_pts)
    for i, t in enumerate(T_arr):
        if t < T0:
            Sa[i] = SMS * (0.4 + 0.6 * t / T0)   # rampa inicial
        elif t <= Ts:
            Sa[i] = SMS                           # meseta 2.5·Aa·Fa
        elif t <= TL:
            Sa[i] = 1.2 * SM1 / t                 # 1.2·Av·Fv/T
        else:
            Sa[i] = 1.2 * SM1 * TL / t**2         # 1.2·Av·Fv·TL/T²
    return T_arr, Sa


def periodo_aproximado(sistema: str, hn: float) -> float:
    """Período aproximado NSR-10 A.4.2.1: Ta = Ct * hn^x"""
    from engine.nsr10_data import COEF_PERIODO
    for key, (Ct, x) in COEF_PERIODO.items():
        if key.lower() in sistema.lower():
            return Ct * (hn ** x)
    return 0.047 * (hn ** 0.9)   # default: concreto
