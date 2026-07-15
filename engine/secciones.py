"""
engine/secciones.py — parser ÚNICO del nombre dimensional de sección.

Auditoría 2026-07-11 (A10): el nombre de sección ('C30x30', 'V25x50') es el
BUS DE DATOS del producto y ~13 módulos lo re-parseaban cada uno con su propia
regex, con gramáticas divergentes: el constructor de ETABS solo aceptaba
enteros y sobre 'C27.5x30' enganchaba «5x30» → columna de 5×30 cm en el modelo
(bug silencioso), mientras el linter y el exportador .e2k sí aceptaban
decimales. Este módulo es LA gramática; los parsers locales quedan como
wrappers finos (cada uno conserva su firma/unidades/defaults) y
tests/test_secciones.py::TestConsistenciaEntreModulos exige que TODOS
coincidan — una divergencia futura rompe la batería.

Gramática canónica: prefijo de letras OPCIONAL + número (con decimales) +
'x'/'X' + número, tolerando espacios: 'C30x30', 'V25x35', '40x60',
' c27.5 X 30 '. Nombres sin 'NxN' ('Muro20') → None (el que llama decide su
default — eso es dato del dominio de cada consumidor, no de la gramática).

Módulo PURO (sin streamlit/clr).
"""
from __future__ import annotations

import re

_PATRON = re.compile(r"([A-Za-z]*)\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)")


def parse(nombre) -> tuple[str, float, float] | None:
    """'C30x30' → ('C', 30.0, 30.0) [cm]; '40x60' → ('', 40.0, 60.0);
    'C27.5x30' → ('C', 27.5, 30.0). None si no hay patrón 'NxN'."""
    m = _PATRON.search(str(nombre or ""))
    if not m:
        return None
    return m.group(1), float(m.group(2)), float(m.group(3))


def dims_cm(nombre, default: tuple[float, float] = (30.0, 30.0)) -> tuple[float, float]:
    """(b, h) en CENTÍMETROS. `default` si el nombre no parsea."""
    p = parse(nombre)
    return (p[1], p[2]) if p else default


def dims_m(nombre, default: tuple[float, float] = (0.30, 0.30)) -> tuple[float, float]:
    """(b, h) en METROS. `default` si el nombre no parsea."""
    p = parse(nombre)
    return (p[1] / 100.0, p[2] / 100.0) if p else default
