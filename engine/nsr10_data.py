"""
Datos tabulados NSR-10 para la calculadora FHE.
Tablas A.2.4-3 (Fa) y A.2.4-4 (Fv), ciudades, sistemas estructurales.
"""

# ── Ciudades capitales: {nombre: (Aa, Av)} ───────────────────────────────────
# Fuente: NSR-10 Tabla A.2.3-2 "Valor de Aa y de Av para las ciudades
# capitales de departamento" (verificado contra el PDF oficial AIS/SCG,
# Decreto 2010-01-13). Para municipios NO capitales usar Apéndice A-4.
CIUDADES = {
    "Arauca (Arauca)":              (0.15, 0.15),  # Intermedia
    "Armenia (Quindío)":            (0.25, 0.25),  # Alta
    "Barranquilla (Atlántico)":     (0.10, 0.10),  # Baja
    "Bogotá D.C.":                  (0.15, 0.20),  # Intermedia
    "Bucaramanga (Santander)":      (0.25, 0.25),  # Alta
    "Cali (Valle)":                 (0.25, 0.25),  # Alta
    "Cartagena (Bolívar)":          (0.10, 0.10),  # Baja
    "Cúcuta (N. Santander)":        (0.35, 0.30),  # Alta
    "Florencia (Caquetá)":          (0.20, 0.15),  # Intermedia
    "Ibagué (Tolima)":              (0.20, 0.20),  # Intermedia
    "Leticia (Amazonas)":           (0.05, 0.05),  # Baja
    "Manizales (Caldas)":           (0.25, 0.25),  # Alta
    "Medellín (Antioquia)":         (0.15, 0.20),  # Intermedia
    "Mitú (Vaupés)":                (0.05, 0.05),  # Baja
    "Mocoa (Putumayo)":             (0.30, 0.25),  # Alta
    "Montería (Córdoba)":           (0.10, 0.15),  # Intermedia
    "Neiva (Huila)":                (0.25, 0.25),  # Alta
    "Pasto (Nariño)":               (0.25, 0.25),  # Alta
    "Pereira (Risaralda)":          (0.25, 0.25),  # Alta
    "Popayán (Cauca)":              (0.25, 0.20),  # Alta
    "Puerto Carreño (Vichada)":     (0.05, 0.05),  # Baja
    "Puerto Inírida (Guainía)":     (0.05, 0.05),  # Baja
    "Quibdó (Chocó)":               (0.35, 0.35),  # Alta
    "Riohacha (La Guajira)":        (0.10, 0.15),  # Intermedia
    "San Andrés (Isla)":            (0.10, 0.10),  # Baja
    "Santa Marta (Magdalena)":      (0.15, 0.10),  # Intermedia
    "San José del Guaviare (Guav.)":(0.05, 0.05),  # Baja
    "Sincelejo (Sucre)":            (0.10, 0.15),  # Intermedia
    "Tunja (Boyacá)":               (0.20, 0.20),  # Intermedia
    "Valledupar (Cesar)":           (0.10, 0.10),  # Baja
    "Villavicencio (Meta)":         (0.35, 0.30),  # Alta
    "Yopal (Casanare)":             (0.30, 0.20),  # Alta
    "Otra (ingresar manual)":       (None, None),
}

# ── Ae y Ad por ciudad: {nombre: (Ae, Ad)} ───────────────────────────────────
# Ae = aceleración para edificaciones EXISTENTES / seguridad limitada
#      (NSR-10 Cap. A.10, Tabla A.10.3-2).
# Ad = aceleración del UMBRAL DE DAÑO (NSR-10 Cap. A.12, Tabla A.12.2-2),
#      usada en la verificación de daño de edificaciones Grupo III y IV.
# Ninguna afecta el espectro de DISEÑO (que sale de Aa, Av, Fa, Fv, I).
# Mismas claves que CIUDADES. Verificado contra el PDF oficial AIS/SCG.
AE_AD = {
    "Arauca (Arauca)":              (0.10, 0.04),
    "Armenia (Quindío)":            (0.15, 0.10),
    "Barranquilla (Atlántico)":     (0.05, 0.03),
    "Bogotá D.C.":                  (0.13, 0.06),
    "Bucaramanga (Santander)":      (0.15, 0.09),
    "Cali (Valle)":                 (0.15, 0.09),
    "Cartagena (Bolívar)":          (0.05, 0.03),
    "Cúcuta (N. Santander)":        (0.25, 0.10),
    "Florencia (Caquetá)":          (0.10, 0.05),
    "Ibagué (Tolima)":              (0.15, 0.06),
    "Leticia (Amazonas)":           (0.04, 0.02),
    "Manizales (Caldas)":           (0.20, 0.10),
    "Medellín (Antioquia)":         (0.13, 0.07),
    "Mitú (Vaupés)":                (0.04, 0.02),
    "Mocoa (Putumayo)":             (0.20, 0.10),
    "Montería (Córdoba)":           (0.07, 0.04),
    "Neiva (Huila)":                (0.20, 0.08),
    "Pasto (Nariño)":               (0.15, 0.08),
    "Pereira (Risaralda)":          (0.20, 0.10),
    "Popayán (Cauca)":              (0.15, 0.08),
    "Puerto Carreño (Vichada)":     (0.04, 0.02),
    "Puerto Inírida (Guainía)":     (0.04, 0.02),
    "Quibdó (Chocó)":               (0.25, 0.13),
    "Riohacha (La Guajira)":        (0.07, 0.04),
    "San Andrés (Isla)":            (0.05, 0.03),
    "Santa Marta (Magdalena)":      (0.10, 0.04),
    "San José del Guaviare (Guav.)":(0.04, 0.02),
    "Sincelejo (Sucre)":            (0.07, 0.04),
    "Tunja (Boyacá)":               (0.15, 0.07),
    "Valledupar (Cesar)":           (0.05, 0.03),
    "Villavicencio (Meta)":         (0.20, 0.07),
    "Yopal (Casanare)":             (0.15, 0.06),
    "Otra (ingresar manual)":       (None, None),
}

# ── Tabla Fa — NSR-10 Tabla A.2.4-3 (ANCLAS OFICIALES) ──────────────────────
# Columnas oficiales: Aa ≤ 0.1, 0.2, 0.3, 0.4, ≥ 0.5 — interpolación lineal
# entre ellas (la permite la norma); _interpolar acota en los extremos.
# ⚠ Corregida 2026-07-05 (auditoría): la versión anterior usaba una grilla
# 0.05–0.40 con las filas C y E CORRIDAS una columna (espectro subestimado
# hasta −17%: INSEGURO en suelos blandos) y la fila D de Fa con valores que no
# son de la norma (1.48 en Aa=0.2 vs 1.40 oficial — conservador).
FA_AA    = [0.10, 0.20, 0.30, 0.40, 0.50]
FA_TABLE = {
    "A": [0.8, 0.8, 0.8, 0.8, 0.8],
    "B": [1.0, 1.0, 1.0, 1.0, 1.0],
    "C": [1.2, 1.2, 1.1, 1.0, 1.0],
    "D": [1.6, 1.4, 1.2, 1.1, 1.0],
    "E": [2.5, 1.7, 1.2, 0.9, 0.9],
}

# ── Tabla Fv — NSR-10 Tabla A.2.4-4 (ANCLAS OFICIALES) ──────────────────────
# Columnas oficiales: Av ≤ 0.1, 0.2, 0.3, 0.4, ≥ 0.5.
FV_AV    = [0.10, 0.20, 0.30, 0.40, 0.50]
FV_TABLE = {
    "A": [0.8, 0.8, 0.8, 0.8, 0.8],
    "B": [1.0, 1.0, 1.0, 1.0, 1.0],
    "C": [1.7, 1.6, 1.5, 1.4, 1.3],
    "D": [2.4, 2.0, 1.8, 1.6, 1.5],
    "E": [3.5, 3.2, 2.8, 2.4, 2.4],
}

PERFIL_SUELO = {
    "A — Roca dura (Vs > 1500 m/s)": "A",
    "B — Roca (760 < Vs ≤ 1500 m/s)": "B",
    "C — Suelo muy denso (360 < Vs ≤ 760 m/s)": "C",
    "D — Suelo rígido (180 < Vs ≤ 360 m/s)": "D",
    "E — Suelo blando (Vs < 180 m/s)": "E",
    "F — Requiere evaluación específica": "F",
}

# ── Grupo de uso → I (NSR-10 A.2.5.1 + Tabla A.2.5-1) ────────────────────────
# ⚠ Auditoría 2026-07-11: los ejemplos estaban ROTADOS un grupo (hospitales en
# III, bomberos en IV, colegios en II) y el I de Grupo III decía 1.3 (oficial:
# 1.25) → subdimensionaba edificaciones esenciales. Clasificación oficial:
# IV = indispensables (A.2.5.1.1: hospitales con cirugía/urgencias, líneas
# vitales); III = atención a la comunidad (A.2.5.1.2: bomberos, policía,
# colegios, guarderías); II = ocupación especial (A.2.5.1.3: >200 personas en
# un salón, graderías, almacenes >500 m²). Test 1:1 en
# tests/test_datos_nsr10.py::TestGrupoUso. Los proyectos guardan la etiqueta
# como texto y el I numérico aparte → el cambio no los rompe; el I viejo queda
# obsoleto y se corrige al re-guardar el paso Sismo.
GRUPO_USO = {
    "Grupo I — Ocupación normal (vivienda, comercio, industria)":            1.00,
    "Grupo II — Ocupación especial (>200 personas en un salón, graderías)":  1.10,
    "Grupo III — Atención a la comunidad (colegios, bomberos, policía)":     1.25,
    "Grupo IV — Indispensables (hospitales, líneas vitales)":                1.50,
}

# ── Sistemas estructurales → R₀ (coeficiente BÁSICO de disipación) ───────────
# Fuente: NSR-10 Tabla A.3-1 (muros de carga), A.3-2 (combinado), A.3-3 (pórtico).
# Verificado contra el PDF oficial AIS/SCG. El nivel de disipación (DMI/DMO/DES)
# define el R₀ del MISMO sistema. El R efectivo = R₀·φa·φp·φr (irregularidades),
# que la suite reduce aparte (página Sismo). Ej.: muro DMI R₀=2.5 con φ=0.7 → R=1.75.
SISTEMAS = {
    # Pórtico resistente a momentos de concreto (Tabla A.3-3)
    "Pórtico de concreto — DES (R₀=7)":                   7.0,
    "Pórtico de concreto — DMO (R₀=5)":                   5.0,
    "Pórtico de concreto — DMI (R₀=2.5)":                 2.5,
    # Muros de carga de concreto (Tabla A.3-1)
    "Muro de concreto — DES (R₀=5)":                      5.0,
    "Muro de concreto — DMO (R₀=4)":                      4.0,
    "Muro de concreto — DMI (R₀=2.5)":                    2.5,
    # Sistema dual pórtico-muro de concreto (Tabla A.3-2)
    "Dual pórtico-muro concreto — DES (R₀=7)":            7.0,
    "Dual pórtico-muro concreto — DMO (R₀=5)":            5.0,
    # Mampostería estructural (Tabla A.3-1)
    "Mampostería reforzada celdas llenas — DES (R₀=3.5)": 3.5,
    "Mampostería reforzada — DMO (R₀=2.5)":               2.5,
    "Mampostería confinada (R₀=2)":                       2.0,
    "Mampostería no reforzada (R₀=1)":                    1.0,
    # Pórtico resistente a momentos de acero (Tabla A.3-3)
    "Pórtico de acero — DES (R₀=7)":                      7.0,
    "Pórtico de acero — DMO (R₀=5)":                      5.0,
    "Otro (ingresar manual)":                             None,
}

# ── Irregularidades NSR-10 A.3.3 ─────────────────────────────────────────────
# (descripcion, factor_phi, ayuda)
# Cada entrada: (nombre, factor_phi, ayuda_texto, pasos_etabs_o_None)
# ayuda_texto usa \n\n para separar secciones: ¿Qué es? / ¿Cómo verifico? / Casos típicos
IRREG_ALTURA = [
    ("A1 — Piso blando",
     0.90,
     "¿Qué es? Un piso es mucho más flexible que el de arriba — como un primer piso "
     "con columnas muy delgadas y los demás con muros.\n\n"
     "¿Cómo verifico? Necesitas ETABS: compara la rigidez lateral de cada piso. "
     "Si Ki < 70% de Ki+1 (piso de arriba) → aplica. "
     "También si Ki < 80% del promedio de los 3 pisos superiores.\n\n"
     "Casos típicos: primer piso abierto para estacionamiento (pilotis), "
     "piso con ventanas muy grandes sin muros.",
     [
         "Corre el análisis: Run → Run Analysis (F5)",
         "Ve a: Display → Show Tables",
         "En el árbol: Analysis Results → Story Results → Story Stiffness",
         "La tabla muestra la rigidez Ki de cada piso en X y en Y",
         "Calcula: Ki / Ki+1 — si el resultado < 0.70 → aplica A1",
         "Verifica también: Ki / promedio(Ki+1, Ki+2, Ki+3) < 0.80 → también aplica",
     ]),

    ("A2 — Masa irregular",
     0.90,
     "¿Qué es? Un piso pesa más del 150% que el piso adyacente de arriba o abajo.\n\n"
     "¿Cómo verifico? Con los Wi que ya ingresaste en esta calculadora: "
     "compara cada piso con el inmediatamente superior e inferior. "
     "Si Wi > 1.50 × Wi±1 → aplica. También puedes sacar los Wi de ETABS.\n\n"
     "Casos típicos: piso con tanque de agua, mezzanine muy cargado, "
     "piso de maquinaria pesada.",
     [
         "Corre el análisis: Run → Run Analysis (F5)",
         "Ve a: Display → Show Tables",
         "En el árbol: Analysis Results → Story Results → Story Masses",
         "La columna 'Mass X' (o Mass Y) muestra la masa de cada piso en toneladas",
         "Multiplica por 9.81 para obtener Wi en kN",
         "Calcula: Wi / Wi+1 — si el resultado > 1.50 → aplica A2",
     ]),

    ("A3 — Irregularidad geométrica vertical",
     0.90,
     "¿Qué es? Un piso vuela o se retira más del 30% respecto al piso adyacente.\n\n"
     "¿Cómo verifico? Solo con los planos de planta: mide la dimensión en planta "
     "del sistema resistente en cada piso. Si un piso tiene dimensión > 130% "
     "del piso inmediatamente encima o abajo → aplica.\n\n"
     "Casos típicos: edificio escalonado, pisos que vuelan hacia afuera, "
     "torre sobre podio.",
     None),  # Solo planos, no requiere ETABS

    ("A4 — Discontinuidad en el sistema resistente",
     0.80,
     "¿Qué es? Una columna o muro que termina en el aire (apoyado en una viga) "
     "en lugar de llegar hasta la cimentación.\n\n"
     "¿Cómo verifico? Solo con los planos estructurales: ¿hay columnas que no bajan "
     "hasta la cimentación? ¿Muros que terminan a mitad de altura? → aplica.\n\n"
     "Casos típicos: columnas que arrancan desde una viga de transferencia, "
     "muros que desaparecen en planta baja.",
     None),  # Solo planos, no requiere ETABS
]

IRREG_PLANTA = [
    ("P1 — Torsión",
     0.90,
     "¿Qué es? El edificio tiende a girar cuando vibra porque el centro de masa "
     "y el centro de rigidez no coinciden.\n\n"
     "¿Cómo verifico? Necesitas ETABS: compara la deriva máxima en un extremo del piso "
     "con la deriva promedio del mismo piso. "
     "Si δ_max > 1.2 × δ_prom → aplica P1.\n\n"
     "Casos típicos: edificio con muros solo en un lado, planta asimétrica, "
     "escalera o ascensor en esquina.",
     [
         "Corre el análisis: Run → Run Analysis (F5)",
         "Ve a: Display → Show Tables",
         "En el árbol: Analysis Results → Story Results → Story Drifts",
         "Filtra por caso sísmico (SismoX o SismoY)",
         "Busca los valores 'Max Drift' y 'Avg Drift' de cada piso",
         "Calcula: Max Drift / Avg Drift — si > 1.20 → aplica P1",
         "Repite para ambas direcciones (X e Y)",
     ]),

    ("P2 — Torsión extrema",
     0.80,
     "¿Qué es? Igual que P1 pero más grave — el edificio gira excesivamente.\n\n"
     "¿Cómo verifico? En ETABS: Max Drift / Avg Drift > 1.40 → aplica P2. "
     "NSR-10 prohíbe esta irregularidad con sistemas DMO en zona de amenaza alta.\n\n"
     "Si tienes P2, debes redistribuir la rigidez — agregar muros o cambiar "
     "la posición de los elementos resistentes.",
     [
         "Mismo procedimiento que P1 (Display → Show Tables → Story Drifts)",
         "Si Max Drift / Avg Drift > 1.40 → aplica P2 (no solo P1)",
         "Verifica también en ETABS: Design → Seismic Checks → Torsional Irregularity",
         "ETABS puede reportar automáticamente si hay P1 o P2 en el reporte de diseño",
     ]),

    ("P3 — Esquinas entrantes",
     0.90,
     "¿Qué es? La planta tiene forma de L, T, U, C o similar con esquinas "
     "entrantes grandes.\n\n"
     "¿Cómo verifico? Solo con el plano de planta: mide la esquina entrante. "
     "Si la entrante > 15% de la dimensión total en esa dirección → aplica.\n\n"
     "Ejemplo: edificio de 20 m con entrante de 4 m → 4/20 = 20% > 15% → aplica. "
     "Edificio rectangular simple → NO aplica.",
     None),  # Solo planos

    ("P4 — Discontinuidad de diafragma",
     0.90,
     "¿Qué es? La losa de piso tiene huecos o aberturas muy grandes que impiden "
     "que actúe como un diafragma rígido.\n\n"
     "¿Cómo verifico? Solo con el plano de planta: suma el área de todos los vacíos "
     "(patios, atrios, vanos). Si supera el 50% del área bruta del piso → aplica.\n\n"
     "Casos típicos: edificio con patio central grande, rampas vehiculares, "
     "atrios en centros comerciales.",
     None),  # Solo planos

    ("P5 — Sistemas no paralelos",
     0.90,
     "¿Qué es? Las columnas, vigas o muros están en ángulo — no son paralelos "
     "a los ejes X o Y del edificio.\n\n"
     "¿Cómo verifico? Solo con el plano estructural: ¿hay elementos inclinados "
     "en planta? Si los ejes no son ortogonales → aplica.\n\n"
     "Casos típicos: edificio en esquina con fachada en ángulo, plantas con "
     "ejes rotados. Edificio rectangular ortogonal → NO aplica.",
     None),  # Solo planos
]

# ── Método período aproximado NSR-10 A.4.2.1 ─────────────────────────────────
# Ta = Ct × hn^x
COEF_PERIODO = {
    "Pórtico de concreto":  (0.047, 0.9),
    "Pórtico de acero":     (0.072, 0.8),
    # Tabla A.4.2-1: los sistemas basados en MUROS (concreto o mampostería)
    # usan Ct=0.049, α=0.75. (Antes duplicaba la fila de pórtico 0.047/0.9 →
    # Ta inflado ~44% → Cs en la rama descendente → V del FHE hasta 35-45%
    # MENOR de lo que exige A.4.2: inseguro. Auditoría 2026-07-05.)
    "Muros de concreto":    (0.049, 0.75),
    "Mampostería":          (0.049, 0.75),
}


def coef_periodo(sistema: str) -> tuple[float, float]:
    """(Ct, α) de la Tabla A.4.2-1 según el NOMBRE del sistema estructural de
    la suite ('Muro de concreto — DES', 'Pórtico de concreto — DMO', dual...).
    Los sistemas de MUROS (muro/mampostería/dual con muros) van con 0.049/0.75;
    pórticos de concreto 0.047/0.9; acero 0.072/0.8."""
    s = (sistema or "").lower()
    if "acero" in s and "pórtico" in s:
        return COEF_PERIODO["Pórtico de acero"]
    if "muro" in s or "mamposter" in s or "dual" in s or "combinado" in s:
        return COEF_PERIODO["Muros de concreto"]
    return COEF_PERIODO["Pórtico de concreto"]


# ── Zona de amenaza sísmica y disipación mínima (A.2.3 + A.3.1.1) ────────────
# La zona la define el MAYOR de Aa/Av (Tabla A.2.3-1); la zona dicta la
# capacidad de disipación de energía MÍNIMA del sistema (Tabla A.3-2).
# Siempre se puede usar una capacidad MAYOR que la mínima, nunca menor.

DISIPACION_MINIMA = {"baja": "DMI", "intermedia": "DMO", "alta": "DES"}
_RANGO_DISIPACION = {"DMI": 1, "DMO": 2, "DES": 3}


def nivel_disipacion(sistema: str | None) -> str | None:
    """DES/DMO/DMI leído del nombre del sistema, o None si no lo trae ('Otro')."""
    import re
    m = re.search(r"(DES|DMO|DMI)", sistema or "")
    return m.group(1) if m else None


def es_des(proyecto: dict) -> bool:
    """¿El proyecto usa disipación ESPECIAL (DES)? Los chequeos C.21.6.2 (columna
    fuerte-viga débil) y C.21.7 (cortante de nudo) SOLO se exigen en pórticos DES;
    en DMO/DMI no aplican. Lee el sistema; si es 'Otro' (sin nivel), cae a R₀≥6.5."""
    sis = proyecto.get("sismo", {}) or {}
    niv = nivel_disipacion(sis.get("sistema"))
    if niv:
        return niv == "DES"
    return float(sis.get("R", 0) or 0) >= 6.5


def zona_amenaza(Aa: float, Av: float) -> str:
    """'baja' (≤0.10) · 'intermedia' (≤0.20) · 'alta' (>0.20), por el mayor."""
    peor = max(float(Aa or 0), float(Av or 0))
    if peor <= 0.10:
        return "baja"
    if peor <= 0.20:
        return "intermedia"
    return "alta"


def validar_disipacion(sistema: str, Aa: float, Av: float) -> dict:
    """
    Valida la capacidad de disipación del sistema elegido contra el mínimo de
    la zona. Devuelve:
      {zona, minima, disipacion (DMI/DMO/DES o None si el nombre no la trae),
       valida (True/False/None), mensaje}
    """
    import re
    zona = zona_amenaza(Aa, Av)
    minima = DISIPACION_MINIMA[zona]
    m = re.search(r"(DES|DMO|DMI)", sistema or "")
    disip = m.group(1) if m else None
    if disip is None:
        return {"zona": zona, "minima": minima, "disipacion": None,
                "valida": None,
                "mensaje": (f"Zona {zona} → mínimo {minima}. No pude leer la "
                            "capacidad de tu sistema; verifícala manualmente "
                            "(Tabla A.3-2).")}
    rd, rm = _RANGO_DISIPACION[disip], _RANGO_DISIPACION[minima]
    if rd < rm:
        return {"zona": zona, "minima": minima, "disipacion": disip,
                "valida": False,
                "mensaje": (f"VIOLA NSR-10 A.3.1.1: en zona de amenaza {zona} "
                            f"el mínimo es {minima}; elegiste {disip}. "
                            "Cambia el sistema estructural.")}
    if rd > rm:
        return {"zona": zona, "minima": minima, "disipacion": disip,
                "valida": True,
                "mensaje": (f"Zona {zona} (mínimo {minima}): {disip} es válido, "
                            f"pero te OBLIGA al detallado {disip} del C.21 "
                            "(estribos, nudos, empalmes). Si no vas a construir "
                            f"ese detallado, usa {minima}.")}
    return {"zona": zona, "minima": minima, "disipacion": disip,
            "valida": True,
            "mensaje": f"Zona {zona} → mínimo {minima} ✓ (tu sistema: {disip})."}
