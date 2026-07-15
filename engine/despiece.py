"""
Despiece global — convierte las áreas de acero requeridas (del diseño ETABS)
en configuraciones de barras comerciales, verifica cuantías NSR-10 y estima
el peso total de acero.

Barras (denominación colombiana, diámetros en octavos de pulgada):
  Ø3/8"(#3)=0.71 cm² · Ø1/2"(#4)=1.29 · Ø5/8"(#5)=1.99 · Ø3/4"(#6)=2.84
  Ø7/8"(#7)=3.87 · Ø1"(#8)=5.10

Cuantías NSR-10:
  Columnas (C.10.9.1): 1% ≤ ρ ≤ 4% del área bruta
  Vigas (C.10.5):      As_min = max(0.25·√f'c/fy, 1.4/fy)·b·d  (≈0.0033·b·d con
                       f'c=21, fy=414)

Módulo PURO.
"""
from __future__ import annotations

import math
import re
from engine import secciones as SEC

# (nombre, área cm²) — orden preferido para proponer
BARRAS = [
    ("Ø1/2\"", 1.29),
    ("Ø5/8\"", 1.99),
    ("Ø3/4\"", 2.84),
    ("Ø7/8\"", 3.87),
    ("Ø1\"",   5.10),
]
DENSIDAD_ACERO = 7850.0   # kg/m³

# Diámetros nominales (mm) por nº de barra US — ÚNICA fuente (la comparte bim.refuerzo para
# pesar IGUAL). El peso de fábrica del acero se calcula por la SECCIÓN GEOMÉTRICA del Ø
# (π/4·Ø²·ρ = el kg/m de catálogo), NO por el área NOMINAL redondeada (#4 = 1.29 cm² es solo
# para As/resistencia; pesar con ella sobre-reporta ~1.9%).
NUM_DIAM_MM = {2: 6.4, 3: 9.5, 4: 12.7, 5: 15.9, 6: 19.05, 7: 22.2,
               8: 25.4, 9: 28.65, 10: 32.26, 11: 35.81}


def kg_m_barra(num: int) -> float:
    """Peso lineal REAL (kg/m) de UNA barra #num por su sección geométrica (peso de fábrica)."""
    d = NUM_DIAM_MM.get(int(num), 19.05) / 1000.0
    return math.pi / 4.0 * d * d * DENSIDAD_ACERO


def _n_barras(txt: str) -> int:
    """Nº de barras al inicio del texto ('4Ø1/2\" (#4)' -> 4)."""
    m = re.match(r"\s*(\d+)", txt or "")
    return int(m.group(1)) if m else 0

# Estribo estándar Ø3/8" (#3): área de UNA rama y diámetro
ESTRIBO_AREA = 0.71    # cm²
ESTRIBO_DE   = 0.95    # cm
ESTRIBO_KG_M = 0.557   # kg/m

# Diámetro de barra longitudinal (cm) por denominación
DB_CM = {'Ø1/2"': 1.27, 'Ø5/8"': 1.59, 'Ø3/4"': 1.91, 'Ø7/8"': 2.22, 'Ø1"': 2.54}

# Número de barra (octavos de pulgada): Ø1/2"=#4 · Ø5/8"=#5 · Ø3/4"=#6 ...
NUM_BARRA = {'Ø3/8"': 3, 'Ø1/2"': 4, 'Ø5/8"': 5, 'Ø3/4"': 6, 'Ø7/8"': 7, 'Ø1"': 8}


def _floor_cm(v_cm: float, paso: float = 2.5, minimo: float = 5.0) -> float:
    """Redondea HACIA ABAJO a múltiplos de 2.5 cm (espaciamientos prácticos)."""
    return max(minimo, math.floor(v_cm / paso) * paso)


def estribos_viga(Av_m2m: float, b_cm: float, h_cm: float,
                  db_long_cm: float, L_m: float) -> dict:
    """
    Estribos de viga DMO — NSR-10 C.21.3.4:
      Zona confinada 2h desde la cara: s ≤ mín(d/4, 8·db, 24·de, 30 cm),
      primer estribo a 5 cm. Resto: s ≤ d/2 (C.11) y lo que pida el cortante.
    Av_m2m = área de cortante requerida por metro (de ETABS, 2 ramas).
    """
    d = h_cm - 6.0
    # RAMAS del estribo (C.21.3.3 / C.7.10.5): ninguna barra longitudinal a > 150 mm (libre) de
    # una rama soportada → vigas angostas = 2 ramas; anchas = ganchos/ramas suplementarias.
    b_util = max(b_cm - 2 * 4.0 - 2 * ESTRIBO_DE, 4.0)         # ancho útil (cm)
    n_ramas = max(2, int(math.ceil(b_util / 30.0)) + 1)        # ramas cada ≤ 30 cm
    s_conf = min(d / 4, 8 * db_long_cm, 24 * ESTRIBO_DE, 30.0)
    Av_cm2m = Av_m2m * 1e4
    s_cort = (n_ramas * ESTRIBO_AREA) / Av_cm2m * 100 if Av_cm2m > 0.01 else 999.0  # más ramas → +Av
    s_zona  = _floor_cm(min(s_conf, s_cort))
    s_resto = _floor_cm(min(d / 2, s_cort, 30.0))
    Lconf = 2 * h_cm / 100          # m por extremo
    n_est = (2 * Lconf / (s_zona / 100)
             + max(L_m - 2 * Lconf, 0) / (s_resto / 100)) + 2
    long_estribo = 2 * ((b_cm - 8) + (h_cm - 8)) / 100 + 0.15           # estribo rectang. (2 ramas)
    long_rama = (h_cm - 8) / 100 + 0.15                                 # gancho/rama suplementaria
    long_set = long_estribo + max(n_ramas - 2, 0) * long_rama          # estribo + ganchos suplem.
    rama_txt = "" if n_ramas <= 2 else f" + {n_ramas - 2} gancho(s) suplem. ({n_ramas} ramas)"
    return {
        "texto": f'Ø3/8" (#3): 1@5, @{s_zona:g} en 2h={2*h_cm:g} cm, resto @{s_resto:g} cm{rama_txt}',
        "s_conf_cm": s_zona, "s_resto_cm": s_resto, "n_ramas": n_ramas,
        "kg": round(n_est * long_set * ESTRIBO_KG_M, 1),
    }


def estribos_columna(Av_m2m: float, b_cm: float, h_cm: float,
                     db_long_cm: float, L_m: float) -> dict:
    """
    Estribos de columna DMO — NSR-10 C.21.4.4 (confinamiento):
      Zona lo = máx(b, h, L/6, 45 cm) en ambos extremos,
      s ≤ mín(8·db, b/2, 15 cm)  ·  Resto: s ≤ mín(16·db, 48·de, b, 30 cm).
    """
    lado_min = min(b_cm, h_cm)
    s_conf = min(8 * db_long_cm, lado_min / 2, 15.0)
    Av_cm2m = Av_m2m * 1e4
    s_cort = (2 * ESTRIBO_AREA) / Av_cm2m * 100 if Av_cm2m > 0.01 else 999.0
    s_zona  = _floor_cm(min(s_conf, s_cort))
    s_resto = _floor_cm(min(16 * db_long_cm, 48 * ESTRIBO_DE, lado_min, 30.0, s_cort))
    lo = max(b_cm, h_cm, L_m * 100 / 6, 45.0) / 100      # m
    n_est = (2 * lo / (s_zona / 100)
             + max(L_m - 2 * lo, 0) / (s_resto / 100)) + 2
    long_estribo = 2 * ((b_cm - 8) + (h_cm - 8)) / 100 + 0.15
    return {
        "texto": f'Ø3/8" (#3): @{s_zona:g} en lo={lo*100:.0f} cm, resto @{s_resto:g} cm',
        "s_conf_cm": s_zona, "s_resto_cm": s_resto, "lo_cm": round(lo * 100),
        "kg": round(n_est * long_estribo * ESTRIBO_KG_M, 1),
    }


def _dims_cm(seccion: str) -> tuple[float, float]:
    """'C30x30' / 'V30x60' → (b, h) en cm. Fallback 30×30."""
    return SEC.dims_cm(seccion)      # gramática ÚNICA (engine/secciones, A10)


def proponer_barras(As_cm2: float, n_min: int = 2, n_max: int = 20,
                    simetrica: bool = False) -> dict:
    """
    Elige la combinación de barras de UN diámetro que cubre As_cm2 con el
    menor exceso. simetrica=True fuerza número par (columnas).
    Devuelve {texto, n, barra, As_prop_cm2}.
    """
    if As_cm2 <= 0:
        return {"texto": "—", "n": 0, "barra": "", "As_prop_cm2": 0.0}
    mejor = None
    for nombre, area in BARRAS:
        n = max(n_min, math.ceil(As_cm2 / area))
        if simetrica and n % 2:
            n += 1
        if n > n_max:
            continue
        As_prop = n * area
        exceso = As_prop - As_cm2
        if mejor is None or exceso < mejor[0]:
            mejor = (exceso, nombre, n, As_prop)
    if mejor is None:   # ni la barra más grande alcanza con n_max
        nombre, area = BARRAS[-1]
        n = math.ceil(As_cm2 / area)
        if simetrica and n % 2:
            n += 1
        mejor = (n * area - As_cm2, nombre, n, n * area)
    _, nombre, n, As_prop = mejor
    num = NUM_BARRA.get(nombre)
    return {"texto": f"{n}{nombre}" + (f" (#{num})" if num else ""),
            "n": n, "barra": nombre,
            "As_prop_cm2": round(As_prop, 2)}


def renombrar_por_dims(datos: dict) -> dict:
    """Reetiqueta `seccion` en columnas/vigas por las DIMS REALES que el script
    de diseño leyó del modelo (`props_dims`: {nombre: [b_cm, h_cm]}).

    Bug real 2026-07-12: tras la iteración, el NOMBRE de la prop en ETABS es el
    viejo (el iterador redimensiona SIN renombrar) — «Correr diseño» reportaba
    columnas 'C120x120' que medían 45×45 y la cuantía salía con dims falsas
    (ρ 7× subestimada, estado «ok» mentiroso). Los nombres pueden mentir; las
    dimensiones del modelo no. Sin `props_dims` (script viejo) no toca nada.
    Muta y devuelve `datos`. PURO."""
    pd_ = datos.get("props_dims") or {}
    mapa = {}
    for nombre, dims in pd_.items():
        try:
            b, h = float(dims[0]), float(dims[1])
        except (TypeError, ValueError, IndexError):
            continue
        mm = re.match(r"([A-Za-z]+)", str(nombre))
        pre = mm.group(1) if mm else "C"
        nuevo = f"{pre}{b:g}x{h:g}"
        if nuevo != str(nombre):
            mapa[str(nombre)] = nuevo
    if mapa:
        for c in datos.get("columnas", []) or []:
            c["seccion"] = mapa.get(str(c.get("seccion")), c.get("seccion"))
        for v in datos.get("vigas", []) or []:
            v["seccion"] = mapa.get(str(v.get("seccion")), v.get("seccion"))
    return datos


def procesar_columnas(columnas: list[dict]) -> list[dict]:
    """Diseño de columnas: As requerida vs mínimos NSR-10 + propuesta de barras."""
    out = []
    for c in columnas:
        b, h = _dims_cm(c.get("seccion", ""))
        Ag = b * h                                  # cm²
        As_req = float(c.get("As_pmm_m2", 0)) * 1e4   # m² → cm²
        As_min = 0.01 * Ag                          # C.10.9.1
        As_max = 0.04 * Ag
        As_diseno = max(As_req, As_min)
        # Máx de barras ESCALA con el perímetro de la sección: barras a ~12 cm
        # c.a.c. (separación libre ~10 cm ≥ máx(1.5·db, 4 cm), C.7.6.3 — vibrable
        # en obra). C30→8 · C40→10 · C45→12 · C60→16. Así se prefieren MÁS
        # barras de MENOR calibre (#5-#7) en vez de pocas #8, como se arma en
        # vivienda; el #8 queda solo para demandas que de verdad lo exijan.
        per_util = 2 * ((b - 8) + (h - 8))            # cm, descontando recubr.
        n_max = max(8, min(20, int(per_util / 12) // 2 * 2))
        # Mínimo de barras: 4 (esquinas) solo si la cara libre ≤ 35 cm; si la
        # columna es más grande, C.21 pide barra intermedia arriostrada por cara
        # (hx ≤ 35 cm) → mínimo 8. Evita el '4Ø1\"' en una C45 (cara de 37 cm).
        n_min = 4 if (max(b, h) - 8) <= 35 else 8
        prop = proponer_barras(As_diseno, n_min=n_min, n_max=n_max, simetrica=True)
        cuantia = prop["As_prop_cm2"] / Ag
        estado = "ok"
        if c.get("error"):
            estado = "error"
        elif cuantia > 0.04:
            estado = "error"
        elif As_req > As_min:
            estado = "warn" if cuantia > 0.03 else "ok"
        est = estribos_columna(float(c.get("Av_m2m", 0)), b, h,
                               DB_CM.get(prop["barra"], 1.59),
                               float(c.get("L", 3.0)))
        out.append({
            **c,
            "Ag_cm2": round(Ag, 1),
            "As_req_cm2": round(As_req, 2),
            "As_min_cm2": round(As_min, 2),
            "As_max_cm2": round(As_max, 2),
            "propuesta": prop["texto"],
            "As_prop_cm2": prop["As_prop_cm2"],
            "cuantia_pct": round(cuantia * 100, 2),
            "estribos": est["texto"],
            "kg_estribos": est["kg"],
            "estado": estado,
        })
    return out


def procesar_vigas(vigas: list[dict], fc: float = 21.0, fy: float = 414.0) -> list[dict]:
    """Diseño de vigas: As top/bot vs mínimo C.10.5 + propuesta de barras."""
    out = []
    for v in vigas:
        b, h = _dims_cm(v.get("seccion", ""))
        d = max(h - 6.0, 0.8 * h)                   # peralte efectivo aprox (cm)
        As_min = max(0.25 * math.sqrt(fc) / fy, 1.4 / fy) * b * d   # cm²
        # Nº MÁX de barras que CABEN en una capa por el ancho (C.7.6.1: c.a.c. ≥ Ø + máx(Ø,2.5cm)).
        # Pitch repr. ~4.4 cm (#6 + 2.5 libre); si pide más As, proponer_barras usa barras MÁS grandes.
        b_util = max(b - 2 * 4.0 - 2 * 0.95, 4.0)   # ancho − 2·recubr − 2·Ø estribo (cm)
        n_cabe = max(2, min(12, int((b_util + 2.5) / 4.4)))
        filas = {}
        for cara, clave in (("sup", "As_top_m2"), ("inf", "As_bot_m2")):
            As_req = float(v.get(clave, 0)) * 1e4
            As_dis = max(As_req, As_min)
            prop = proponer_barras(As_dis, n_min=2, n_max=n_cabe)
            filas[cara] = {"req": round(As_req, 2), "prop": prop}
        estado = "error" if v.get("error") else "ok"
        db_sup = DB_CM.get(filas["sup"]["prop"]["barra"], 1.59)
        est = estribos_viga(float(v.get("Av_m2m", 0)), b, h, db_sup,
                            float(v.get("L", 5.0)))
        out.append({
            **v,
            "As_min_cm2": round(As_min, 2),
            "As_sup_req": filas["sup"]["req"],
            "sup_propuesta": filas["sup"]["prop"]["texto"],
            "As_sup_prop": filas["sup"]["prop"]["As_prop_cm2"],
            "As_inf_req": filas["inf"]["req"],
            "inf_propuesta": filas["inf"]["prop"]["texto"],
            "As_inf_prop": filas["inf"]["prop"]["As_prop_cm2"],
            "estribos": est["texto"],
            "kg_estribos": est["kg"],
            "n_ramas": est.get("n_ramas", 2),
            "estado": estado,
        })
    return out


# Traslapos clase B (m) — f'c=21 MPa, fy≈420 (NSR-10 C.12; mismo cuadro del plano)
TRASLAPO_M = {"#3": 0.35, "#4": 0.45, "#5": 0.60, "#6": 0.75, "#7": 1.05, "#8": 1.35}


def _lap_m(barra_txt: str) -> float:
    """Longitud de traslapo clase B (m) según el #N que trae el texto de barra."""
    m = re.search(r"#(\d+)", barra_txt or "")
    return TRASLAPO_M.get("#" + m.group(1), 0.0) if m else 0.0


def resumen_acero(cols_proc: list[dict], vigas_proc: list[dict]) -> dict:
    """Peso de acero longitudinal por diámetro y total (kg).

    `total_kg` = NETO (barra a lo largo del elemento, sin empalmes). Además se
    calcula el peso de los TRASLAPOS clase B aparte (`kg_traslapos`): columnas
    +1 empalme por piso, vigas +1 empalme por corrida (sup e inf). El total con
    empalmes (cantidad de COMPRA) va en `total_con_traslapos`.
    """
    kg_por_barra: dict[str, float] = {}
    kg_lap = 0.0

    def acum(barra_txt: str, n_bars: float, L: float, n_laps: int = 0):
        # Pesa por Nº de barras × kg/m REAL (Ø geométrico = peso de fábrica), NO por área
        # nominal × densidad (que sobre-reporta ~1.9%). Así el cuadro pesa lo MISMO que el
        # modelo de Revit (bim.refuerzo), que dibuja la barra real → reconcilian EXACTO.
        nonlocal kg_lap
        if not barra_txt or barra_txt == "—" or n_bars <= 0:
            return
        nombre = barra_txt.lstrip("0123456789")
        mn = re.search(r"#(\d+)", barra_txt)
        klm = kg_m_barra(int(mn.group(1)) if mn else 6)
        kg_por_barra[nombre] = kg_por_barra.get(nombre, 0.0) + klm * n_bars * L
        kg_lap += klm * n_bars * n_laps * _lap_m(barra_txt)

    for c in cols_proc:
        acum(c.get("propuesta", ""), _n_barras(c.get("propuesta", "")),
             float(c.get("L", 3.0)), n_laps=1)
    for v in vigas_proc:
        L = float(v.get("L", 5.0))
        # SUP: perchas CORRIDAS (toda la luz) + bastones CORTADOS ~L/3 sobre cada apoyo —
        # IGUAL que el BIM (bim.refuerzo) y que la minuta. Antes corría TODO el As_sup a la
        # luz completa → sobrecontaba los bastones (~2% de más en el pórtico vs el modelo).
        sup_txt = v.get("sup_propuesta", "")
        n_sup = _n_barras(sup_txt)
        if n_sup >= 1:
            n_per = min(2, n_sup); n_bas = n_sup - n_per                  # 2 perchas + resto bastones
            acum(sup_txt, n_per, L, n_laps=1)                            # perchas corridas
            if n_bas > 0:
                acum(sup_txt, n_bas, 2.0 * L / 3.0)                      # bastones (2 apoyos × L/3)
        acum(v.get("inf_propuesta", ""), _n_barras(v.get("inf_propuesta", "")), L, n_laps=1)

    # Estribos Ø3/8" (ya calculados por elemento; no llevan traslapo)
    kg_est = sum(float(e.get("kg_estribos", 0)) for e in cols_proc + vigas_proc)
    if kg_est > 0:
        kg_por_barra['Ø3/8" (#3) estribos'] = kg_est   # sin redondear → cuadra con el BIM al gramo

    total = round(sum(kg_por_barra.values()), 1)
    lap = round(kg_lap, 1)
    return {
        "total_kg": total,
        "kg_traslapos": lap,
        "total_con_traslapos": round(total + lap, 1),   # = total_kg + kg_traslapos (sin desfase)
        "por_diametro": {k: round(v, 1) for k, v in sorted(kg_por_barra.items())},
    }
