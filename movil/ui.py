"""Piezas visuales nativas (tarjetas, anillos, barras, chips) con controles de Flet."""
import math

import flet as ft
import flet.canvas as cv

VERDE, AMBAR, ROJO, TEAL = "#2e9d5b", "#d48a0c", "#c94040", "#0f8a8a"
TEAL_OSCURO, TEXTO, GRIS, BORDE, FONDO = "#0f6e6e", "#1f2933", "#6b7a86", "#e1ecec", "#f5f8f8"
COLOR_ETIQUETA = {"Bueno": VERDE, "Regular": AMBAR, "Malo": ROJO}
CHIP_ETIQUETA = {"Bueno": "ok", "Regular": "warn", "Malo": "bad"}
CHIPS = {"ok": ("#e3f5ea", "#1f7a45"), "warn": ("#fdf1dc", "#9a6200"),
         "bad": ("#fbe4e4", "#a83232"), "info": ("#e3f1f1", TEAL_OSCURO),
         "gris": ("#eef1f3", "#55636e")}


def color_valor(v, inverso=False):
    """Verde/ámbar/rojo con los niveles del modelo (Bajo < 0.375 ≤ Medio < 0.75 ≤ Alto)."""
    if inverso:
        v = 1 - v
    return VERDE if v >= 0.75 else AMBAR if v >= 0.375 else ROJO


def texto(valor, tam=15, color=TEXTO, negrita=False, **kw):
    return ft.Text(valor, size=tam, color=color,
                   weight=ft.FontWeight.BOLD if negrita else None, **kw)


def sub(valor, tam=13, **kw):
    return texto(valor, tam, GRIS, **kw)


def titulo(valor, ayuda=""):
    controles = [texto(valor, 22, negrita=True)]
    if ayuda:
        controles.append(sub(ayuda))
    return ft.Column(controles, spacing=2)


def chip(valor, tipo="info"):
    fondo, color = CHIPS[tipo]
    return ft.Container(texto(valor, 12, color, negrita=True), bgcolor=fondo,
                        border_radius=999, padding=ft.Padding.symmetric(horizontal=10, vertical=3))


def tarjeta(contenido, titulo_sec=None, on_click=None, padding=16):
    controles = contenido if isinstance(contenido, list) else [contenido]
    if titulo_sec:
        controles = [texto(titulo_sec, 16, negrita=True), *controles]
    return ft.Container(
        ft.Column(controles, spacing=8), bgcolor=ft.Colors.WHITE, padding=padding,
        border=ft.Border.all(1, BORDE), border_radius=16, on_click=on_click, ink=bool(on_click),
        shadow=ft.BoxShadow(blur_radius=3, color="#0f102a43", offset=ft.Offset(0, 1)))


def hero(controles):
    return ft.Container(
        ft.Column(controles, spacing=2), padding=18, border_radius=18,
        gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                                   colors=[TEAL, "#22a9a2"]))


def fila(izquierda, derecha=None, divisor=True):
    """Renglón con contenido a la izquierda y un valor/chip a la derecha."""
    izq = texto(izquierda) if isinstance(izquierda, str) else izquierda
    der = texto(derecha, negrita=True) if isinstance(derecha, str) else derecha
    renglon = ft.Row([ft.Container(izq, expand=True), der] if der else [izq],
                     alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                     vertical_alignment=ft.CrossAxisAlignment.CENTER)
    if not divisor:
        return renglon
    return ft.Container(renglon, padding=ft.Padding.symmetric(vertical=8),
                        border=ft.Border.only(bottom=ft.BorderSide(1, "#eef3f3")))


def anillo(fraccion, centro, subtexto="", color=TEAL, tam=112, carita=None):
    """Anillo de avance; con `carita`, el emoji va arriba del número."""
    if carita:
        tam += 12
    contenido = [texto(centro, 18 if carita else 21, negrita=True), sub(subtexto, 11)]
    if carita:
        contenido.insert(0, ft.Text(carita, size=30))
    return ft.Stack([
        ft.ProgressRing(value=max(0, min(1, fraccion)), stroke_width=12, color=color,
                        bgcolor="#e3eded", width=tam, height=tam),
        ft.Container(ft.Column(contenido, spacing=0,
                               horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                               alignment=ft.MainAxisAlignment.CENTER),
                     width=tam, height=tam, alignment=ft.Alignment.CENTER),
    ], width=tam, height=tam)


def barra(valor, color, alto=10):
    return ft.ProgressBar(value=max(0, min(1, valor)), color=color, bgcolor="#e8efef",
                          bar_height=alto, border_radius=999)


# ------------------------------------------------------------------ caritas
# Escala visual de 5 caritas para porcentajes de adherencia (solo ilustrativa).
CARAS = [("😢", "Muy baja"), ("😟", "Baja"), ("😐", "Regular"), ("🙂", "Buena"), ("😄", "Excelente")]
LIMITES_PCT = [50, 65, 80, 90]  # < 50 😢 · < 65 😟 · < 80 😐 · < 90 🙂 · ≥ 90 😄


def nivel_pct(pct):
    return sum(pct >= limite for limite in LIMITES_PCT)


def carita_pct(pct):
    return CARAS[nivel_pct(pct)][0]


def color_pct(pct):
    """Color de la misma escala que las caritas: rojo 😢😟 · ámbar 😐 · verde 🙂😄."""
    return [ROJO, ROJO, AMBAR, VERDE, VERDE][nivel_pct(pct)]


def carita_valor(v, inverso=False):
    """Carita con los niveles del modelo (Bajo < 0.375 ≤ Medio < 0.75 ≤ Alto)."""
    if inverso:
        v = 1 - v
    return "😄" if v >= 0.75 else "😐" if v >= 0.375 else "😟"


CARITA_ETIQUETA = {"Bueno": "😄", "Regular": "😐", "Malo": "😟"}


def termometro_caritas(pct):
    """Las 5 caritas en fila: la que corresponde a `pct` grande y resaltada, las demás tenues."""
    actual = nivel_pct(pct)
    caritas = []
    for i, (cara, etiqueta) in enumerate(CARAS):
        elegida = i == actual
        caritas.append(ft.Container(
            ft.Column([ft.Text(cara, size=40 if elegida else 24),
                       texto(etiqueta, 11, color_pct([0, 50, 65, 80, 90][i]) if elegida else GRIS, negrita=elegida)],
                      spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                      alignment=ft.MainAxisAlignment.END),
            expand=True, opacity=1 if elegida else 0.35, alignment=ft.Alignment.BOTTOM_CENTER,
            padding=ft.Padding.symmetric(vertical=6), border_radius=14,
            bgcolor=CHIPS["ok" if i >= 3 else "warn" if i == 2 else "bad"][0] if elegida else None))
    return ft.Row(caritas, spacing=2, vertical_alignment=ft.CrossAxisAlignment.END)


def barras_h(items, inversos=()):
    """items: [(etiqueta, valor 0–1, clave)]; las claves en `inversos` se colorean al revés."""
    return ft.Column([
        ft.Row([ft.Text(carita_valor(v, clave in inversos), size=26),
                ft.Column([ft.Row([ft.Container(texto(et, 14), expand=True),
                                   texto(f"{v:.2f}", 14, negrita=True)]),
                           barra(v, color_valor(v, clave in inversos))], spacing=4, expand=True)],
               spacing=10)
        for et, v, clave in items], spacing=12)


def barras_v(valores, etiquetas, sufijo="%", alto=110, caritas=True):
    """Columnas verticales; valores en 0–100. Sin `caritas` (vista del médico) es una gráfica
    plana: solo el porcentaje encima de cada barra."""
    return ft.Row([
        ft.Column(([ft.Text(carita_pct(v), size=20, text_align=ft.TextAlign.CENTER)]
                   if caritas else []) +
                  [texto(f"{v:.0f}{sufijo}", 11, text_align=ft.TextAlign.CENTER),
                   ft.Container(height=alto * v / 100, bgcolor=color_pct(v),
                                border_radius=ft.BorderRadius.only(top_left=6, top_right=6)),
                   sub(e, 11, text_align=ft.TextAlign.CENTER)],
                  expand=True, spacing=2, alignment=ft.MainAxisAlignment.END,
                  horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        for v, e in zip(valores, etiquetas)], spacing=6, height=alto + (68 if caritas else 42),
        vertical_alignment=ft.CrossAxisAlignment.END)


def mini_barras(valores, alto=26):
    """Siete barritas para ver de un vistazo la semana de un paciente en la lista del médico."""
    return ft.Row([ft.Container(height=max(3, alto * v / 100), bgcolor=color_pct(v), expand=True,
                                border_radius=3) for v in valores],
                  spacing=3, height=alto, vertical_alignment=ft.CrossAxisAlignment.END)


def pastel(segmentos, tam=190):
    """Gráfica de pastel con una carita en cada rebanada.

    segmentos: [(cantidad, color, carita)]; las rebanadas en 0 no se dibujan.
    """
    total = sum(n for n, _, _ in segmentos) or 1
    centro, radio = tam / 2, tam / 2
    formas, inicio = [], -math.pi / 2  # se empieza arriba, a las 12
    for n, color, carita in segmentos:
        if not n:
            continue
        barrido = 2 * math.pi * n / total
        formas.append(cv.Arc(0, 0, tam, tam, inicio, barrido, use_center=True,
                             paint=ft.Paint(color=color)))
        if n < total:  # línea blanca entre rebanadas
            formas.append(cv.Arc(0, 0, tam, tam, inicio, barrido, use_center=True,
                                 paint=ft.Paint(color=ft.Colors.WHITE, stroke_width=3,
                                                style=ft.PaintingStyle.STROKE)))
        medio = inicio + barrido / 2
        distancia = 0 if n == total else radio * 0.58
        formas.append(cv.Text(centro + distancia * math.cos(medio),
                              centro + distancia * math.sin(medio), carita,
                              ft.TextStyle(size=30 if n == total else 26),
                              alignment=ft.Alignment.CENTER))
        inicio += barrido
    return ft.Row([cv.Canvas(formas, width=tam, height=tam)],
                  alignment=ft.MainAxisAlignment.CENTER)


def aviso(contenido, tipo="bad", icono=ft.Icons.WARNING_AMBER_ROUNDED):
    fondo, color = CHIPS[tipo]
    cuerpo = ft.Markdown(contenido) if isinstance(contenido, str) else contenido
    return ft.Container(ft.Row([ft.Icon(icono, color=color), ft.Container(cuerpo, expand=True)],
                               vertical_alignment=ft.CrossAxisAlignment.START),
                        bgcolor=fondo, border_radius=12, padding=12)


def boton(valor, on_click, icono=None, principal=False, **kw):
    clase = ft.FilledButton if principal else ft.OutlinedButton
    return clase(valor, icon=icono, on_click=on_click, height=50,
                 style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)), **kw)
