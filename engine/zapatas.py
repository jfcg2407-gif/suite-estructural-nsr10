"""
Cimentaciones — zapata AISLADA y zapata CONECTADA (viga de conexión).

Método de la zapata conectada (columna medianera): la zapata exterior no puede
centrarse bajo la columna (lindero) → se conecta con una viga rígida a la
zapata interior. La viga toma el momento de la excentricidad como palanca
(ΣM en la columna interior) y la zapata exterior queda con presión ~uniforme.

Implementa el flujo de la hoja de referencia de Jorge ("ZAPATA CONECTADA.xlsx",
método clásico tipo E.060/ACI) pero con combos parametrizados:
    COMBO_NSR10 = (1.2, 1.6)   ← producción (B.2.4.2)
    COMBO_E060  = (1.4, 1.7)   ← solo para validar contra la hoja

UNIDADES (las de obra, como la hoja): cargas en Tn, longitudes en m,
σt en kg/cm², f'c y fy en kg/cm². (1 kg/cm² ≈ 10 Tn/m².)
La página convierte las reacciones de ETABS (kN → Tn: /9.80665).

Módulo PURO.
"""
from __future__ import annotations

import math
import re

from engine.despiece import BARRAS, NUM_BARRA, proponer_barras

COMBO_NSR10 = (1.2, 1.6)
COMBO_E060 = (1.4, 1.7)

GAMMA_CONCRETO = 2.4      # Tn/m³
PHI_FLEX = 0.9
PHI_CORTE = 0.75
RHO_TEMP = 0.0018         # retracción/temperatura (C.7.12)


def _ceil5(v: float, minimo: float = 0.0) -> float:
    return round(max(minimo, math.ceil(round(v, 6) / 0.05) * 0.05), 2)


def presion_neta(sigma_t: float, hf: float, gamma_m: float,
                 s_piso: float = 0.4) -> float:
    """σn [Tn/m²] = σt·10 − hf·γm − sobrecarga de piso. Lo que queda del suelo
    para la carga de la columna, descontando el relleno encima de la zapata."""
    return sigma_t * 10.0 - hf * gamma_m - s_piso


def _as_flexion(Mu_Tnm: float, b_cm: float, d_cm: float,
                fc: float, fy: float) -> float:
    """As [cm²] por flexión, iterando el bloque 'a' (4 vueltas, como la hoja).
    As = Mu·10⁵ / (φ·fy·(d−a/2)) · a = As·fy/(0.85·f'c·b)."""
    Mu = abs(Mu_Tnm)
    if Mu <= 0 or d_cm <= 0:
        return 0.0
    a = d_cm / 5
    As = 0.0
    for _ in range(4):
        As = Mu * 1e5 / (PHI_FLEX * fy * (d_cm - a / 2))
        a = As * fy / (0.85 * fc * b_cm)
    return round(As, 2)


def _vc_uni(b_cm: float, d_cm: float, fc: float) -> float:
    """Vc unidireccional [Tn] = 0.53·√f'c·b·d (kg) — C.11 (=0.17√f'c MPa)."""
    return 0.53 * math.sqrt(fc) * b_cm * d_cm / 1000.0


def _d_util(h_m: float, db_cm: float = 1.91) -> float:
    """d [cm] = h − 7.5 cm (recubrimiento a fondo) − db/2 (como la hoja)."""
    return h_m * 100 - 7.5 - db_cm / 2


_DB_CM = {3: 0.95, 4: 1.27, 5: 1.59, 6: 1.91, 7: 2.22, 8: 2.54}   # diámetros de barra (cm)


def _db_min(*textos) -> float:
    """Diámetro [cm] de la barra longitudinal MÁS DELGADA de los textos ('4Ø1/2\" (#4)')."""
    ns = [int(m) for t in textos for m in re.findall(r"#(\d+)", t or "")]
    return min((_DB_CM.get(n, 1.27) for n in ns), default=1.27)


def _estribos_cortante(Vu: float, b_cm: float, d_cm: float, fc: float, fy: float,
                       db_long_cm: float) -> dict:
    """Diseña los estribos por CORTANTE de una viga (NSR-10 C.11 + confinamiento C.21.3.3),
    en unidades de obra (Vu en Tn, fc/fy en kg/cm², dims en cm). Estribo Ø3/8\" (#3) de 2
    ramas. Devuelve {texto, s_conf, s_resto, Vs, Vc, seccion_ok}; el texto trae las DOS
    zonas ('@s_conf en 2h, resto @s_resto') que el plano dibuja."""
    Vc = _vc_uni(b_cm, d_cm, fc)                          # Tn
    phiVc = PHI_CORTE * Vc
    Av = 2 * 0.71                                         # cm² (2 ramas Ø3/8")
    fyt = min(fy, 4200.0)                                 # C.11.5.2: fyt ≤ 420 MPa
    raiz = math.sqrt(fc)
    Vs = max(Vu / PHI_CORTE - Vc, 0.0)                    # Tn que deben tomar los estribos
    s_max = min(d_cm / 2.0, 60.0)                         # C.11.5.5.1
    if Vs > 1.06 * raiz * b_cm * d_cm / 1000.0:           # Vs alto → s_max = d/4 (C.11.5.5.3)
        s_max = min(d_cm / 4.0, 30.0)
    s_avmin = Av * fyt / max(0.2 * raiz * b_cm, 3.5 * b_cm)   # área mínima C.11.4.6.3
    if Vs > 1e-6:                                         # gobierna la resistencia
        s_resto = min(Av * fyt * d_cm / (Vs * 1000.0), s_max, s_avmin)
    elif Vu > 0.5 * phiVc:                                # estribos mínimos
        s_resto = min(s_max, s_avmin)
    else:                                                 # Vu ≤ ½φVc → solo montaje
        s_resto = min(s_max, 30.0)
    s_conf = min(d_cm / 4.0, 6.0 * db_long_cm, 15.0, s_resto)   # confinado en 2h (C.21.3.3)
    _r = lambda s: max(5.0, math.floor(s / 2.5) * 2.5)   # múltiplo práctico de 2.5 cm, mín 5
    s_resto, s_conf = _r(s_resto), _r(s_conf)
    seccion_ok = Vs <= 2.1 * raiz * b_cm * d_cm / 1000.0  # C.11.5.7.9 (si no, agrandar sección)
    return {"texto": f'Ø3/8" (#3): @{s_conf:g} en 2h, resto @{s_resto:g} cm',
            "s_conf": s_conf, "s_resto": s_resto, "Vs": round(Vs, 2),
            "Vc": round(Vc, 2), "seccion_ok": seccion_ok}


def _estribos_desde_viga(v: dict) -> str:
    """Estribos por cortante a partir de un dict de viga YA calculado (Vu, phiVc, b, h,
    barras). Reconstruye √f'c de phiVc (no depende de 'materiales') y asume estribo #3
    fyt=4200. Sirve para que el PLANO muestre el corte real aun en proyectos ya guardados."""
    Vu = abs(float(v.get("Vu", 0) or 0))
    phiVc = float(v.get("phiVc", 0) or 0)
    b_cm = float(v.get("b", 0.30)) * 100
    d_cm = _d_util(float(v.get("h", 0.60)), 2.54)
    if Vu <= 0 or phiVc <= 0 or d_cm <= 0 or b_cm <= 0:
        return 'Ø3/8" (#3) @15 cm'
    raiz = phiVc * 1000.0 / (PHI_CORTE * 0.53 * b_cm * d_cm)   # phiVc = 0.75·0.53·√fc·b·d/1000
    fc = raiz ** 2
    db = _db_min(v.get("barras_sup"), v.get("barras_inf"))
    return _estribos_cortante(Vu, b_cm, d_cm, fc, 4200.0, db)["texto"]


def _barras_texto(As_cm2: float, n_min: int = 2, ancho: float | None = None,
                  s_max: float = 0.45, rec: float = 0.075) -> dict:
    """Propone barras para As. Si se pasa `ancho` (m) es una PARRILLA de zapata: además
    de As, fuerza un mínimo de barras para que la separación NO exceda s_max (NSR-10
    C.7.6.5 / C.10.5.4: s ≤ min(3h, 450 mm)). Sin `ancho` se comporta como antes (vigas)."""
    n = n_min
    nmax = 24
    if ancho:
        n = max(n, math.ceil((ancho - 2 * rec) / s_max) + 1)   # nº mínimo por separación
        nmax = 60                                              # zapatas anchas → permitir más barras
    return proponer_barras(max(As_cm2, 0.0), n_min=n, n_max=nmax)


def presion_biaxial(P: float, Mx: float, My: float, Bx: float, By: float) -> dict:
    """Presión del suelo bajo zapata rectangular Bx×By con axial P (Tn) y
    momentos de servicio Mx, My (Tn·m). Fórmula de flexión biaxial:

        σ = P/A · (1 ± 6·ex/Bx ± 6·ey/By),  ex = |My|/P,  ey = |Mx|/P

    Convención: Mx flexiona en Y (ey), My flexiona en X (ex). σ en Tn/m².
    Devuelve {smax, smin, ex, ey, sin_despegue}. `sin_despegue` = la resultante
    cae en el núcleo central (kern): ex/Bx + ey/By ≤ 1/6 → toda la zapata
    comprime (σmin ≥ 0). Si False, una esquina se despega (hay que agrandar)."""
    A = Bx * By
    if P <= 0 or A <= 0:
        return {"smax": 0.0, "smin": 0.0, "ex": 0.0, "ey": 0.0,
                "sin_despegue": True}
    ex = abs(My) / P
    ey = abs(Mx) / P
    base = P / A
    fx, fy_ = 6.0 * ex / Bx, 6.0 * ey / By
    return {"smax": round(base * (1 + fx + fy_), 3),
            "smin": round(base * (1 - fx - fy_), 3),
            "ex": round(ex, 4), "ey": round(ey, 4),
            "sin_despegue": (ex / Bx + ey / By) <= 1.0 / 6.0 + 1e-9}


def _solve3(M, r):
    """Resuelve un sistema 3×3 M·x = r por Cramer. None si es singular."""
    a, b, c = M[0]; d, e, f = M[1]; g, h, i = M[2]
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if abs(det) < 1e-12:
        return None
    r0, r1, r2 = r
    dx = r0 * (e * i - f * h) - b * (r1 * i - f * r2) + c * (r1 * h - e * r2)
    dy = a * (r1 * i - f * r2) - r0 * (d * i - f * g) + c * (d * r2 - r1 * g)
    dz = a * (e * r2 - r1 * h) - b * (d * r2 - r1 * g) + r0 * (d * h - e * g)
    return dx / det, dy / det, dz / det


def presion_biaxial_efectiva(P: float, Mx: float, My: float,
                             Bx: float, By: float, n: int = 20) -> dict:
    """σmax REAL bajo zapata Bx×By con P, Mx, My (Tn, Tn·m), permitiendo
    DESPEGUE PARCIAL: el suelo NO toma tracción. Si la resultante cae en el
    núcleo (sin despegue) → idéntico a presion_biaxial (contacto total, fórmula
    lineal). Si no, resuelve el plano de presión σ=a+b·x+c·y con la condición
    σ≥0 iterando el área de contacto (método del set activo, no-tracción).

    Devuelve {smax, contacto, ex, ey}. `contacto` = fracción del área en
    compresión (NSR-10 H / práctica: bajo sismo se admite despegue con contacto
    ≥ 50%). PURO."""
    A = Bx * By
    if P <= 0 or A <= 0:
        return {"smax": 0.0, "contacto": 1.0, "ex": 0.0, "ey": 0.0}
    ex, ey = abs(My) / P, abs(Mx) / P
    # camino rápido: resultante en el núcleo → contacto total, idéntico al lineal
    if ex / Bx + ey / By <= 1.0 / 6.0 + 1e-9:
        base = P / A
        return {"smax": round(base * (1 + 6 * ex / Bx + 6 * ey / By), 3),
                "contacto": 1.0, "ex": round(ex, 4), "ey": round(ey, 4)}
    # resultante FUERA de la zapata (e ≥ lado/2) → no hay equilibrio con σ≥0: la
    # zapata volcaría. Inválida → señala contacto 0 / σmax enorme para que el
    # dimensionador la AGRANDE (no la acepte).
    if ex >= Bx / 2 - 1e-9 or ey >= By / 2 - 1e-9:
        return {"smax": 1e9, "contacto": 0.0,
                "ex": round(ex, 4), "ey": round(ey, 4)}
    # malla de celdas (centros) — momentos objetivo respecto a los ejes centroidales
    dx, dy = Bx / n, By / n
    dA = dx * dy
    cells = [(-Bx / 2 + (i + 0.5) * dx, -By / 2 + (j + 0.5) * dy)
             for i in range(n) for j in range(n)]
    Mtx, Mty = P * ex, P * ey            # ex→eje Y (x), ey→eje X (y)
    active = [True] * len(cells)
    abc, contacto = None, 1.0
    for _ in range(60):
        S0 = Sx = Sy = Sxx = Syy = Sxy = 0.0
        for k, (x, y) in enumerate(cells):
            if not active[k]:
                continue
            S0 += dA; Sx += x * dA; Sy += y * dA
            Sxx += x * x * dA; Syy += y * y * dA; Sxy += x * y * dA
        abc = _solve3([[S0, Sx, Sy], [Sx, Sxx, Sxy], [Sy, Sxy, Syy]],
                      [P, Mtx, Mty])
        if abc is None:
            break
        a, b, c = abc
        nuevo, n_act = [], 0
        for (x, y) in cells:
            on = (a + b * x + c * y) > 1e-9
            nuevo.append(on)
            n_act += on
        contacto = n_act / len(cells)
        if nuevo == active:
            break
        active = nuevo
    # σmax en la ESQUINA real de la zapata (el plano σ=a+b·x+c·y es lineal → su
    # máximo sobre el rectángulo está en una esquina, no en el centro de celda)
    if abc is None:                          # contacto colapsó (singular) → inválida
        return {"smax": 1e9, "contacto": 0.0,
                "ex": round(ex, 4), "ey": round(ey, 4)}
    a, b, c = abc
    smax = max(a + b * sx * Bx / 2 + c * sy * By / 2
               for sx in (-1, 1) for sy in (-1, 1))
    return {"smax": round(smax, 3), "contacto": round(contacto, 3),
            "ex": round(ex, 4), "ey": round(ey, 4)}


# ══════════════════════════════════════════════════════════════════════════════
# ZAPATA AISLADA
# ══════════════════════════════════════════════════════════════════════════════

def zapata_aislada(PD: float, PL: float, sigma_t: float, hf: float,
                   gamma_m: float, t1: float = 0.30, t2: float = 0.30,
                   fc: float = 210.0, fy: float = 4200.0,
                   combo: tuple = COMBO_NSR10, s_piso: float = 0.4,
                   Mx: float = 0.0, My: float = 0.0,
                   factor_sismo: float = 1.0, permite_despegue: bool = False,
                   contacto_min: float = 0.5, B_min: float = 0.0) -> dict:
    """Zapata aislada cuadrada. Cargas en Tn, dims en m.

    Mx, My = momentos de servicio en la base de la columna (Tn·m). Si se dan,
    además del axial dimensiona por **presión biaxial**: agranda B hasta que
    σmax ≤ σn y la resultante caiga en el núcleo (sin despegue), y amplifica la
    presión de diseño por el momento. Con Mx=My=0 el resultado es idéntico al
    concéntrico (regresión intacta).

    `B_min` = lado mínimo (m) para FORZAR una zapata más grande que la que pide
    la presión — típico cuando el ASENTAMIENTO gobierna (más área → menos
    presión → menos Se). 0 = automático (sin piso)."""
    mem: list[str] = []
    cd, cl = combo
    sn = presion_neta(sigma_t, hf, gamma_m, s_piso)
    P = PD + PL
    Pu = cd * PD + cl * PL
    mem.append(f"σn = {sigma_t:g}·10 − {hf:g}·{gamma_m:g} − {s_piso:g} = "
               f"{sn:.1f} Tn/m² · P = {P:.1f} Tn · Pu = {cd}·{PD:g}+{cl}·{PL:g}"
               f" = {Pu:.1f} Tn")

    Az = P / sn
    B0 = _ceil5(math.sqrt(Az), 0.80)
    if B_min and B_min > B0:                    # piso pedido (p. ej. por asentamiento)
        B0 = _ceil5(B_min, B_min)
        mem.append(f"Lado mínimo pedido B ≥ {B_min:g} m (asentamiento/criterio) → "
                   f"arranca en {B0:.2f} m")
    Bx = By = B0
    sn_chk = sn * factor_sismo                  # σn admisible (×factor bajo sismo, NSR-10 H)
    pb = presion_biaxial(P, Mx, My, Bx, By)

    def _acepta(bx, by):                         # ¿cumple la zapata bx×by?
        if permite_despegue:                     # sismo: admite despegue parcial (contacto≥mín)
            pe = presion_biaxial_efectiva(P, Mx, My, bx, by)
            return (pe["smax"] <= sn_chk and pe["contacto"] >= contacto_min), pe
        p = presion_biaxial(P, Mx, My, bx, by)   # gravedad: σmax≤σn y SIN despegue (kern)
        return (p["smax"] <= sn_chk and p["sin_despegue"]), p

    if Mx or My:                                # crecer RECTANGULAR por presión biaxial:
        guard = 0                               # alarga la dirección con peor excentricidad
        ok, chk = _acepta(Bx, By)
        while not ok and Bx < 6.0 and By < 6.0 and guard < 220:
            if chk["ex"] / Bx >= chk["ey"] / By:   # más excentricidad relativa en X → alarga X
                Bx = round(Bx + 0.05, 2)
            else:
                By = round(By + 0.05, 2)
            ok, chk = _acepta(Bx, By)
            guard += 1
        pb = presion_biaxial(P, Mx, My, Bx, By)
    Az_prov = Bx * By
    # presión de diseño del cuerpo: si hay despegue, el PICO real (contacto parcial)
    # gobierna el peralte y el acero → queda del lado seguro aunque la zapata sea menor
    pe_fin = (presion_biaxial_efectiva(P, Mx, My, Bx, By)
              if (permite_despegue and (Mx or My)) else None)
    smax_dis = pe_fin["smax"] if pe_fin else pb["smax"]
    contacto = pe_fin["contacto"] if pe_fin else (1.0 if pb["sin_despegue"] else 0.0)
    wnu = Pu / Az_prov                          # Tn/m² (uniforme equivalente)
    k_mom = (smax_dis / (P / Az_prov)) if (Mx or My) and P > 0 else 1.0
    wnu *= k_mom                                # el momento amplifica la presión
    rect = abs(Bx - By) > 0.001
    mem.append(f"Az = P/σn = {Az:.3f} m² → {Bx:.2f}×{By:.2f}"
               f"{' (rectangular)' if rect else ''} (Az = {Az_prov:.2f} m²) · "
               f"Wnu = {wnu:.1f} Tn/m²")
    if (Mx or My) and permite_despegue:
        mem.append(
            f"Sismo (NSR-10 H): σadm×{factor_sismo:g} = {sn_chk:.1f} · σmax = "
            f"{smax_dis:.1f} {'≤' if smax_dis <= sn_chk else '> ⚠'} · contacto "
            f"{contacto*100:.0f}% {'≥' if contacto >= contacto_min else '< ⚠'} "
            f"{contacto_min*100:.0f}% (despegue parcial admitido) · Wnu ×{k_mom:.2f}")
    elif Mx or My:
        mem.append(
            f"Biaxial: ex = {pb['ex']:.3f} / ey = {pb['ey']:.3f} m → σmax = "
            f"{pb['smax']:.1f} {'≤' if pb['smax'] <= sn else '> ⚠'} σn {sn:.1f} · "
            f"σmin = {pb['smin']:.1f} Tn/m² "
            f"({'sin despegue ✓' if pb['sin_despegue'] else '⚠ DESPEGUE: agranda'})"
            f" · Wnu ×{k_mom:.2f} por momento")

    # Peralte: crece hasta pasar punzonamiento y corte unidireccional (ambas dir.)
    lv_x = (Bx - t1) / 2                         # volado en X (franja de ancho By)
    lv_y = (By - t2) / 2                         # volado en Y (franja de ancho Bx)
    h = 0.30
    while h < 1.50:
        d = _d_util(h)
        bo = 2 * ((t1 + d / 100) + (t2 + d / 100)) * 100      # cm
        Vup = Pu - wnu * (t1 + d / 100) * (t2 + d / 100)
        Vcp = 1.06 * math.sqrt(fc) * bo * d / 1000.0
        Vu1x = wnu * By * max(lv_x - d / 100, 0); Vc1x = _vc_uni(By * 100, d, fc)
        Vu1y = wnu * Bx * max(lv_y - d / 100, 0); Vc1y = _vc_uni(Bx * 100, d, fc)
        if (Vup <= PHI_CORTE * Vcp and Vu1x <= PHI_CORTE * Vc1x
                and Vu1y <= PHI_CORTE * Vc1y):
            break
        h = round(h + 0.05, 2)
    d = _d_util(h)
    mem.append(f"h = {h*100:.0f} cm (punz.: Vu {Vup:.1f} ≤ φVc {PHI_CORTE*Vcp:.1f} Tn)")

    # Acero por dirección: la franja en X tiene ancho By (y viceversa).
    Mu_x = wnu * By * lv_x ** 2 / 2
    Mu_y = wnu * Bx * lv_y ** 2 / 2
    As_x = max(_as_flexion(Mu_x, By * 100, d, fc, fy), RHO_TEMP * By * 100 * h * 100)
    As_y = max(_as_flexion(Mu_y, Bx * 100, d, fc, fy), RHO_TEMP * Bx * 100 * h * 100)
    prop_x = _barras_texto(As_x, n_min=4, ancho=By)   # barras en X repartidas a lo largo de By
    prop_y = _barras_texto(As_y, n_min=4, ancho=Bx)   # barras en Y repartidas a lo largo de Bx
    if rect:
        mem.append(f"Acero: dir X (volado {lv_x:.2f} m) {prop_x['texto']} · "
                   f"dir Y (volado {lv_y:.2f} m) {prop_y['texto']}")
    else:
        mem.append(f"Volado lv = {lv_x:.2f} m → As = {As_x:.1f} → "
                   f"{prop_x['texto']} (ambos sentidos)")

    return {"tipo": "aislada", "B": Bx, "Bx": Bx, "By": By, "h": h,
            "sigma_n": round(sn, 2), "Az_req": round(Az, 3), "Wnu": round(wnu, 2),
            "Mu": round(max(Mu_x, Mu_y), 2), "As_cm2": As_x,
            "As_x": round(As_x, 2), "As_y": round(As_y, 2),
            "barras": prop_x["texto"], "barras_x": prop_x["texto"],
            "barras_y": prop_y["texto"],
            "smax": round(smax_dis, 3), "smin": pb["smin"], "ex": pb["ex"],
            "ey": pb["ey"], "sin_despegue": pb["sin_despegue"],
            "contacto": round(contacto, 3),
            "memoria": mem, "combo": combo}


# ══════════════════════════════════════════════════════════════════════════════
# ZAPATA CONECTADA (viga de conexión) — método de la hoja de Jorge
# ══════════════════════════════════════════════════════════════════════════════

def zapata_conectada(PD1: float, PL1: float, PD2: float, PL2: float,
                     L: float, t1: float, t2: float,
                     sigma_t: float, hf: float, gamma_m: float,
                     fc: float = 210.0, fy: float = 4200.0,
                     combo: tuple = COMBO_NSR10, s_piso: float = 0.4,
                     S1: float | None = None,
                     b_viga: float | None = None,
                     h_viga: float | None = None,
                     M1x: float = 0.0, M1y: float = 0.0,
                     M2x: float = 0.0, M2y: float = 0.0,
                     factor_sismo: float = 1.0, permite_despegue: bool = False,
                     contacto_min: float = 0.5, eje_t1: str = "x") -> dict:
    """
    Zapata conectada: columna EXTERIOR (1, medianera en el lindero) + columna
    INTERIOR (2) unidas por viga de conexión. Cargas de servicio en Tn,
    L = distancia entre ejes de columnas (m), t1/t2 = lado de columna (m).

    M1x,M1y / M2x,M2y = momentos de servicio de la columna exterior / interior
    (Tn·m). Si se dan, cada zapata se CHEQUEA por presión biaxial y se agranda
    si se despegaría (σmin<0). La VIGA de conexión NO cambia (método validado
    contra la hoja); el momento de columna es un chequeo conservador sobre las
    zapatas. Con M=0 el resultado es idéntico al validado.
    """
    mem: list[str] = []
    cd, cl = combo
    sn = presion_neta(sigma_t, hf, gamma_m, s_piso)
    sn_chk = sn * factor_sismo                      # σn admisible (×factor bajo sismo)
    P1, P2 = PD1 + PL1, PD2 + PL2
    P1u = cd * PD1 + cl * PL1
    P2u = cd * PD2 + cl * PL2
    mem.append(f"σn = {sn:.1f} Tn/m² · P1 = {P1:.1f} / P1u = {P1u:.1f} Tn · "
               f"P2 = {P2:.1f} / P2u = {P2u:.1f} Tn · combo {cd}D+{cl}L")

    # ── 1. Viga de conexión (predimensionado empírico de la hoja) ────────────
    h_v = h_viga or _ceil5(L / 7, 0.40)
    b_v = b_viga or _ceil5(P1 / (31 * L), 0.30)
    wv = b_v * h_v * GAMMA_CONCRETO              # Tn/m
    wvu = cd * wv
    mem.append(f"Viga de conexión: h = L/7 = {L:g}/7 → {h_v:.2f} m · "
               f"b = P1/(31·L) → {b_v:.2f} m · peso wv = {wv:.3f} Tn/m")

    # ── 2. Zapata exterior: ancho S1 y equilibrio ΣM₂=0 ─────────────────────
    if S1 is None:
        S1 = _ceil5(math.sqrt(1.2 * P1 / sn / 2))    # ~T1≈2·S1 (medianera)
    Lv = L + t1 / 2                                   # lindero → eje C2

    def _RN(S1v):                                     # RN depende de S1 (vía el brazo)
        return (P1 * L + wv * Lv ** 2 / 2) / max(L - (S1v / 2 - t1 / 2), 0.1)

    RN = _RN(S1)
    Az1 = RN / sn
    T1 = _ceil5(Az1 / S1)
    # T1 corre a lo largo de la VIGA de conexión. presion_biaxial asume Bx∥X, By∥Y
    # (aparea ex=|My|/P con la 1ª dim, ey=|Mx|/P con la 2ª). Si la viga va en Y
    # (T1∥Y), pasar los momentos globales tal cual cruza los ejes → subestima el
    # despegue. Se intercambian M1x↔M1y para que el momento correcto quede con T1.
    _m1x, _m1y = (M1x, M1y) if eje_t1 == "x" else (M1y, M1x)
    pb1 = presion_biaxial(RN, _m1x, _m1y, T1, S1)

    def _ok1(rn, t1v, s1v):                      # ¿cumple la zapata exterior?
        if permite_despegue:                     # sismo: despegue parcial admitido
            pe = presion_biaxial_efectiva(rn, _m1x, _m1y, t1v, s1v)
            return pe["smax"] <= sn_chk and pe["contacto"] >= contacto_min
        p = presion_biaxial(rn, _m1x, _m1y, t1v, s1v)
        return p["smax"] <= sn_chk and p["sin_despegue"]

    if M1x or M1y:        # el momento de columna puede despegar: agranda la dimensión
        _g = 0           # que GOBIERNA (T1 alivia _m1y/ex; S1 alivia _m1x/ey).
        while not _ok1(RN, T1, S1) and max(T1, S1) < 6.0 and _g < 400:
            rx = abs(_m1y) / RN / T1 if RN else 0.0    # término ex/T1
            ry = abs(_m1x) / RN / S1 if RN else 0.0    # término ey/S1
            if ry >= rx:
                S1 = round(S1 + 0.05, 2)
                RN = _RN(S1)                           # S1 cambia el brazo → RN
            else:
                T1 = round(T1 + 0.05, 2)
            pb1 = presion_biaxial(RN, _m1x, _m1y, T1, S1)
            _g += 1
        Az1 = RN / sn
    pe1 = (presion_biaxial_efectiva(RN, _m1x, _m1y, T1, S1)
           if (permite_despegue and (M1x or M1y)) else None)
    smax1 = pe1["smax"] if pe1 else pb1["smax"]
    contacto1 = pe1["contacto"] if pe1 else (1.0 if pb1["sin_despegue"] else 0.0)
    brazo = L - (S1 / 2 - t1 / 2)                     # final (memoria + diseño de viga)
    mem.append(f"ΣM₂=0: RN·{brazo:.3f} = P1·{L:g} + wv·{Lv:.2f}²/2 → "
               f"RN = {RN:.2f} Tn (> P1: la palanca carga más la zapata ext.)")
    mem.append(f"Az = RN/σn = {Az1:.3f} m² → usar T1×S1 = {T1:.2f}×{S1:.2f} m")
    if (M1x or M1y) and permite_despegue:
        mem.append(f"Z.ext sismo: σmax={smax1:.1f}/{sn_chk:.1f} · contacto "
                   f"{contacto1*100:.0f}% (despegue parcial admitido)")
    elif M1x or M1y:
        mem.append(f"Z.ext biaxial (M col {M1x:g}/{M1y:g} Tn·m): σmax="
                   f"{pb1['smax']:.1f}/{sn:.1f} "
                   f"{'sin despegue ✓' if pb1['sin_despegue'] else '⚠ DESPEGUE'}")

    # ── 3. Viga: diseño con últimas ──────────────────────────────────────────
    RNU = (P1u * L + wvu * Lv ** 2 / 2) / brazo
    WNU = RNU / S1                                    # Tn/m bajo la zapata ext
    Xo = P1u / (WNU - wvu)                            # V=0 (desde el lindero)
    Mu_v = (WNU - wvu) * Xo ** 2 / 2 - P1u * (Xo - t1 / 2)   # < 0: tracción ARRIBA
    d_v = _d_util(h_v, 2.54)
    As_sup = _as_flexion(Mu_v, b_v * 100, d_v, fc, fy)
    As_min_v = (14 / fy) * b_v * 100 * d_v            # C.10.5 (14/fy)
    As_inf = max(As_min_v, As_sup / 3)
    prop_sup = _barras_texto(max(As_sup, As_min_v), n_min=2)
    prop_inf = _barras_texto(As_inf, n_min=2)
    mem.append(f"RNU = {RNU:.2f} Tn → WNU = {WNU:.1f} Tn/m · Xo = {Xo:.2f} m "
               f"{'≤' if Xo <= S1 else '> ⚠'} S1")
    mem.append(f"Mu viga = {Mu_v:.1f} Tn·m (negativo → refuerzo principal "
               f"ARRIBA): As sup = {As_sup:.1f} cm² → {prop_sup['texto']} · "
               f"inf {prop_inf['texto']}")

    # cortante de la viga (en la cara interior de la zapata exterior) → DISEÑO de estribos
    V2u = (WNU - wvu) * S1 - P1u
    Vc_v = _vc_uni(b_v * 100, d_v, fc)
    ok_corte = abs(V2u) <= PHI_CORTE * Vc_v
    est_v = _estribos_cortante(abs(V2u), b_v * 100, d_v, fc, fy,
                               _db_min(prop_sup["texto"], prop_inf["texto"]))
    mem.append(f"Vu viga = {abs(V2u):.1f} Tn vs φVc = {PHI_CORTE*Vc_v:.1f} Tn · "
               f"Vs = {est_v['Vs']:.1f} Tn → estribos {est_v['texto']}"
               f"{'' if est_v['seccion_ok'] else ' ⚠ Vs alto: agrandar sección'}")

    # ── 4. Zapata exterior: peralte y refuerzo (volado en dirección T1) ─────
    w_T1 = RNU / T1                                   # Tn/m en la franja T1
    lv1 = T1 / 2 - t1 / 2
    h1 = 0.40
    while h1 < 1.20:
        d1 = _d_util(h1)
        Vud = w_T1 * max(lv1 - d1 / 100, 0)
        if Vud <= PHI_CORTE * _vc_uni(S1 * 100, d1, fc):
            break
        h1 = round(h1 + 0.05, 2)
    d1 = _d_util(h1)
    Mu1 = w_T1 * lv1 ** 2 / 2
    As1 = max(_as_flexion(Mu1, S1 * 100, d1, fc, fy),
              RHO_TEMP * S1 * 100 * h1 * 100)
    As1t = RHO_TEMP * T1 * 100 * h1 * 100             # transversal (retracción)
    prop1 = _barras_texto(As1, n_min=4, ancho=max(T1, S1))   # se usa en ambos sentidos → la dim mayor manda
    prop1t = _barras_texto(As1t, n_min=4, ancho=min(T1, S1))
    mem.append(f"Z.ext: volado {lv1:.2f} m → Mu = {Mu1:.1f} Tn·m → h = "
               f"{h1*100:.0f} cm · As = {As1:.1f} → {prop1['texto']} "
               f"(long.) + {prop1t['texto']} (transv.)")

    # ── 5. Zapata interior: P2 efectivo (la viga le descarga RN−P1) ─────────
    P2ef = P1 + P2 + wv * Lv - RN
    P2uef = P1u + P2u + wvu * Lv - RNU
    Az2 = P2ef / sn
    # Si la viga de conexión alivia tanto el nudo interior que P2ef ≤ 0 (medianera
    # muy pesada vs interior liviano), el área sale negativa: clamp a 0 → B2 cae al
    # mínimo (1.00 m). Evita el math domain error; no afecta casos con P2ef>0.
    B2 = _ceil5(math.sqrt(max(Az2, 0.0)), 1.00)
    pb2 = presion_biaxial(P2ef, M2x, M2y, B2, B2)

    def _ok2(b2v):                          # ¿cumple la zapata interior?
        if permite_despegue:
            pe = presion_biaxial_efectiva(P2ef, M2x, M2y, b2v, b2v)
            return pe["smax"] <= sn_chk and pe["contacto"] >= contacto_min
        p = presion_biaxial(P2ef, M2x, M2y, b2v, b2v)
        return p["smax"] <= sn_chk and p["sin_despegue"]

    if M2x or M2y:                          # agranda B2 si el momento de columna despega
        _g2 = 0
        while not _ok2(B2) and B2 < 6.0 and _g2 < 200:
            B2 = round(B2 + 0.05, 2)
            pb2 = presion_biaxial(P2ef, M2x, M2y, B2, B2)
            _g2 += 1
    pe2 = (presion_biaxial_efectiva(P2ef, M2x, M2y, B2, B2)
           if (permite_despegue and (M2x or M2y) and P2ef > 0) else None)
    smax2 = pe2["smax"] if pe2 else pb2["smax"]
    contacto2 = pe2["contacto"] if pe2 else (1.0 if pb2["sin_despegue"] else 0.0)
    wnu2 = P2uef / (B2 * B2)
    if (M2x or M2y) and P2ef > 0:
        wnu2 *= smax2 / (P2ef / (B2 * B2))   # el momento amplifica la presión
    lv2 = (B2 - t2) / 2
    h2 = 0.40
    while h2 < 1.20:
        d2 = _d_util(h2)
        bo = 4 * (t2 + d2 / 100) * 100
        Vup = P2uef - wnu2 * (t2 + d2 / 100) ** 2
        ok_p = Vup <= PHI_CORTE * (1.06 * math.sqrt(fc) * bo * d2 / 1000)
        ok_1 = wnu2 * B2 * max(lv2 - d2 / 100, 0) <= \
            PHI_CORTE * _vc_uni(B2 * 100, d2, fc)
        if ok_p and ok_1:
            break
        h2 = round(h2 + 0.05, 2)
    d2 = _d_util(h2)
    Mu2 = wnu2 * B2 * lv2 ** 2 / 2
    As2 = max(_as_flexion(Mu2, B2 * 100, d2, fc, fy),
              RHO_TEMP * B2 * 100 * h2 * 100)
    prop2 = _barras_texto(As2, n_min=4, ancho=B2)     # zapata interior cuadrada B2×B2
    mem.append(f"Z.int: P2ef = P1+P2+wv·Lv−RN = {P2ef:.1f} Tn (servicio) / "
               f"{P2uef:.1f} Tn (última) → Az = {Az2:.3f} m² → "
               f"B×B = {B2:.2f}×{B2:.2f} · h = {h2*100:.0f} cm · "
               f"As = {As2:.1f} → {prop2['texto']} (ambos sentidos)")

    return {
        "tipo": "conectada", "sigma_n": round(sn, 2), "combo": combo,
        "sin_despegue": pb1["sin_despegue"] and pb2["sin_despegue"],
        "viga": {"b": b_v, "h": h_v, "Mu": round(Mu_v, 2), "Xo": round(Xo, 3),
                 "As_sup": As_sup, "barras_sup": prop_sup["texto"],
                 "As_inf": round(As_inf, 2), "barras_inf": prop_inf["texto"],
                 "Vu": round(abs(V2u), 2), "phiVc": round(PHI_CORTE * Vc_v, 2),
                 "corte_ok": ok_corte, "barras_transv": est_v["texto"],
                 "Vs": est_v["Vs"]},
        "exterior": {"T1": T1, "S1": S1, "h": h1, "RN": round(RN, 2),
                     "RNU": round(RNU, 2), "Az_req": round(Az1, 3),
                     "Mu": round(Mu1, 2), "As": As1,
                     "barras": prop1["texto"], "barras_transv": prop1t["texto"],
                     "sin_despegue": pb1["sin_despegue"],
                     "contacto": round(contacto1, 3)},
        "interior": {"B": B2, "h": h2, "P2ef": round(P2ef, 2),
                     "P2uef": round(P2uef, 2), "Az_req": round(Az2, 3),
                     "Mu": round(Mu2, 2), "As": As2, "barras": prop2["texto"],
                     "sin_despegue": pb2["sin_despegue"],
                     "contacto": round(contacto2, 3)},
        "memoria": mem,
    }


# ══════════════════════════════════════════════════════════════════════════════
# ZAPATA ESQUINERA (doble excéntrica) — columna en esquina, 2 vigas de conexión
# ══════════════════════════════════════════════════════════════════════════════

def zapata_esquinera(PD: float, PL: float,
                     PDx: float, PLx: float, Lx: float, t_x: float,
                     PDy: float, PLy: float, Ly: float, t_y: float,
                     t_esq: float, sigma_t: float, hf: float, gamma_m: float,
                     fc: float = 210.0, fy: float = 4200.0,
                     combo: tuple = COMBO_NSR10, s_piso: float = 0.4,
                     Mex: float = 0.0, Mey: float = 0.0,
                     Mxx: float = 0.0, Mxy: float = 0.0,
                     Myx: float = 0.0, Myy: float = 0.0,
                     factor_sismo: float = 1.0, permite_despegue: bool = False,
                     contacto_min: float = 0.5) -> dict:
    """Zapata ESQUINERA (doble excéntrica): columna en la esquina del lote, que
    no puede centrarse NI en X NI en Y. Se resuelve con DOS vigas de conexión
    (una hacia la columna interior vecina en X, otra en Y), cada una como
    palanca en su dirección — la extensión directa de la zapata conectada.

    Modelo: cada dirección es una zapata conectada con la carga COMPLETA de la
    esquina (la columna es excéntrica en ambos ejes a la vez, así que cada viga
    debe tomar TODO el momento de su dirección). La zapata esquinera es el
    rectángulo ENVOLVENTE de los dos volados (conservador en área). Las dos
    columnas interiores reciben cada una su descarga (P2ef) de su viga.

    PD,PL          carga de servicio de la columna esquinera (Tn).
    PDx,PLx,Lx,t_x  vecina interior en X: carga, distancia entre ejes (m), lado (m).
    PDy,PLy,Ly,t_y  vecina interior en Y (ídem).
    t_esq           lado de la columna esquinera (m).
    Mex,Mey        momentos de servicio de la columna ESQUINERA (Tn·m); Mxx,Mxy
                   los de la vecina X; Myx,Myy los de la vecina Y. Chequean
                   biaxialmente cada zapata (la esquina es exterior de ambas).
    """
    _sis = dict(factor_sismo=factor_sismo, permite_despegue=permite_despegue,
                contacto_min=contacto_min)
    # pata X: la viga corre en X (T1∥X → eje_t1='x'); pata Y: viga en Y (eje_t1='y')
    rx = zapata_conectada(PD, PL, PDx, PLx, L=Lx, t1=t_esq, t2=t_x,
                          sigma_t=sigma_t, hf=hf, gamma_m=gamma_m,
                          fc=fc, fy=fy, combo=combo, s_piso=s_piso,
                          M1x=Mex, M1y=Mey, M2x=Mxx, M2y=Mxy, eje_t1="x", **_sis)
    ry = zapata_conectada(PD, PL, PDy, PLy, L=Ly, t1=t_esq, t2=t_y,
                          sigma_t=sigma_t, hf=hf, gamma_m=gamma_m,
                          fc=fc, fy=fy, combo=combo, s_piso=s_piso,
                          M1x=Mex, M1y=Mey, M2x=Myx, M2y=Myy, eje_t1="y", **_sis)
    ex, ey = rx["exterior"], ry["exterior"]
    # Rectángulo envolvente: en X manda el volado de la viga X (T1x) y el ancho
    # perpendicular del volado Y (S1y); en Y, simétrico.
    Lx_z = _ceil5(max(ex["T1"], ey["S1"]), 0.80)
    Ly_z = _ceil5(max(ey["T1"], ex["S1"]), 0.80)
    h_z = max(ex["h"], ey["h"])

    mem: list[str] = [
        "ESQUINERA (doble excéntrica): columna en esquina → DOS vigas de "
        "conexión (X e Y). Método tradicional (Calavera/Morales): la carga "
        "axial COMPLETA va a la zapata de esquina y cada viga resuelve el "
        "momento ortogonal de su dirección; la zapata es la envolvente de los "
        "dos volados (presión uniforme por dirección, lado seguro).",
        f"σn = {rx['sigma_n']:.1f} Tn/m² · P esquina = {PD + PL:.1f} Tn",
        f"Dirección X (L={Lx:g} m): viga {rx['viga']['b']*100:.0f}×"
        f"{rx['viga']['h']*100:.0f} cm sup {rx['viga']['barras_sup']} · "
        f"volado ext {ex['T1']:.2f}×{ex['S1']:.2f} m · "
        f"vecina int {rx['interior']['B']:.2f}×{rx['interior']['B']:.2f} m",
        f"Dirección Y (L={Ly:g} m): viga {ry['viga']['b']*100:.0f}×"
        f"{ry['viga']['h']*100:.0f} cm sup {ry['viga']['barras_sup']} · "
        f"volado ext {ey['T1']:.2f}×{ey['S1']:.2f} m · "
        f"vecina int {ry['interior']['B']:.2f}×{ry['interior']['B']:.2f} m",
        f"ZAPATA ESQUINERA (envolvente) = {Lx_z:.2f}×{Ly_z:.2f} m · "
        f"h = {h_z*100:.0f} cm · acero X {ex['barras']} · Y {ey['barras']}",
    ]
    return {
        "tipo": "esquinera", "sigma_n": rx["sigma_n"], "combo": combo,
        "sin_despegue": rx["sin_despegue"] and ry["sin_despegue"],
        "esquinera": {"Lx": Lx_z, "Ly": Ly_z, "h": h_z,
                      "barras_x": ex["barras"], "barras_y": ey["barras"],
                      "RN_x": ex["RN"], "RN_y": ey["RN"]},
        "viga_x": rx["viga"], "viga_y": ry["viga"],
        "interior_x": rx["interior"], "interior_y": ry["interior"],
        "memoria": mem,
    }


def solapes_zapatas(proyecto, tol=0.15):
    """Detecta zapatas que SE SOLAPAN en planta (solape ≥ `tol` en AMBOS ejes). Es una señal de
    DISEÑO: esas columnas quedaron tan juntas para zapatas tan grandes que no caben aisladas →
    deben ir como zapata COMBINADA / mat (no aisladas). El plano 2D dibuja las zapatas como las
    diseñó la suite y NO atrapa este choque; este chequeo sí (lo destapa el modelo 3D). PURO.
    Devuelve clusters de nudos solapados [['A','B','C'], ...] (vacío si ninguno).
    La huella replica la de bim.modelo.extraer_cimentacion (dado centrado; medianero excéntrico)."""
    import re as _re
    cim = (proyecto.get("cimentacion") or {})
    coords = {str(r.get("nudo")): (float(r.get("x", 0.0)), float(r.get("y", 0.0)))
              for r in (cim.get("reacciones") or [])}
    _mc = _re.search(r"(\d+)[xX]", (proyecto.get("geometria", {}).get("secciones", {})
                                    or {}).get("col", "C40x40"))     # lado de columna
    t_col = (int(_mc.group(1)) / 100.0) if _mc else 0.40
    huellas = {}                                  # nodo -> (cx, cy, Bx, By)

    def _set(nodo, cx, cy, Bx, By, propio):
        if not (nodo and Bx and By):
            return
        if nodo in huellas and not propio:        # ya tiene dado PROPIO → no lo pisa el ajeno
            return
        huellas[nodo] = (cx, cy, float(Bx), float(By))

    def _cent(nodo, Bx, By, propio):              # dado centrado en el nudo
        c = coords.get(nodo)
        if c:
            _set(nodo, c[0], c[1], Bx, By, propio)

    def _med(n_ext, n_int, T1, S1):               # dado medianero EXCÉNTRICO (corrido al interior)
        ce, ci = coords.get(n_ext or ""), coords.get(n_int or "")
        if not (ce and T1 and S1):
            return
        if not ci:
            _set(n_ext, ce[0], ce[1], T1, S1, True)
            return
        ux, uy = ci[0] - ce[0], ci[1] - ce[1]
        e = (T1 - t_col) / 2.0                     # cara de la columna al filo (no el centro)
        if abs(ux) >= abs(uy):
            _set(n_ext, ce[0] + (1.0 if ux >= 0 else -1.0) * e, ce[1], T1, S1, True)
        else:
            _set(n_ext, ce[0], ce[1] + (1.0 if uy >= 0 else -1.0) * e, S1, T1, True)

    def _C(nud, i):
        return str(nud[i]) if i < len(nud) else None

    zaps = cim.get("zapatas") or []
    for z in zaps:                                # 1ª pasada: dados propios
        r = z.get("resultado") or {}
        t = z.get("tipo", "aislada")
        nud = z.get("nudos") or []
        if t == "aislada":
            _cent(_C(nud, 0), r.get("Bx", r.get("B")), r.get("By", r.get("B")), True)
        elif t == "conectada":
            ext = r.get("exterior", {})
            _med(_C(nud, 0), _C(nud, 1), ext.get("T1"), ext.get("S1"))
    for z in zaps:                                # 2ª pasada: dados interiores (si el nudo no tiene)
        r = z.get("resultado") or {}
        t = z.get("tipo", "aislada")
        nud = z.get("nudos") or []
        if t == "conectada":
            ina = r.get("interior", {})
            _cent(_C(nud, 1), ina.get("B"), ina.get("B"), False)
        elif t == "esquinera":
            ix, iy = r.get("interior_x", {}), r.get("interior_y", {})
            _cent(_C(nud, 1), ix.get("B"), ix.get("B"), False)
            _cent(_C(nud, 2), iy.get("B"), iy.get("B"), False)

    nodos = list(huellas)
    n = len(nodos)
    padre = list(range(n))

    def find(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    def rect(nodo):
        cx, cy, Bx, By = huellas[nodo]
        return cx - Bx / 2, cy - By / 2, cx + Bx / 2, cy + By / 2

    hay = False
    for i in range(n):
        ax0, ay0, ax1, ay1 = rect(nodos[i])
        for j in range(i + 1, n):
            bx0, by0, bx1, by1 = rect(nodos[j])
            if min(ax1, bx1) - max(ax0, bx0) > tol and min(ay1, by1) - max(ay0, by0) > tol:
                padre[find(i)] = find(j)
                hay = True
    if not hay:
        return []
    grupos = {}
    for i in range(n):
        grupos.setdefault(find(i), []).append(nodos[i])
    return [sorted(g) for g in grupos.values() if len(g) > 1]


def amarre_pares(proyecto):
    """Pares de columnas ADYACENTES en la grilla (misma línea X o Y, consecutivas) que deben
    llevar VIGA DE AMARRE de cimentación — NSR-10 A.3.6.4.2 / H.4.7: en zona sísmica TODAS las
    zapatas se amarran para que la cimentación trabaje como una sola y reparta el sismo. EXCLUYE
    los pares que YA tienen viga de conexión (conectada/esquinera), para no duplicar. PURO.
    Devuelve [(na, nb), ...] (nudos)."""
    from collections import defaultdict
    cim = proyecto.get("cimentacion") or {}
    coords = {str(r.get("nudo")): (round(float(r.get("x", 0.0)), 3), round(float(r.get("y", 0.0)), 3))
              for r in (cim.get("reacciones") or [])}
    ya = set()                                    # pares ya unidos por viga de conexión
    for z in cim.get("zapatas") or []:
        nud = [str(x) for x in (z.get("nudos") or [])]
        if z.get("tipo") == "conectada" and len(nud) >= 2:
            ya.add(frozenset(nud[:2]))
        elif z.get("tipo") == "esquinera" and len(nud) >= 3:
            ya.add(frozenset([nud[0], nud[1]]))
            ya.add(frozenset([nud[0], nud[2]]))
    porX, porY = defaultdict(list), defaultdict(list)
    for n, (x, y) in coords.items():
        porX[x].append((y, n))                    # misma columna (X) → consecutivos en Y
        porY[y].append((x, n))                    # misma fila (Y) → consecutivos en X
    pares, vistos, out = [], set(), []
    for lst in list(porX.values()) + list(porY.values()):
        lst.sort()
        for (_a1, n1), (_a2, n2) in zip(lst, lst[1:]):
            pares.append((n1, n2))
    for a, b in pares:
        k = frozenset([a, b])
        if k in ya or k in vistos:
            continue
        vistos.add(k)
        out.append((a, b))
    return out
