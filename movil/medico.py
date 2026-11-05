"""Pantallas del personal de salud: pacientes, detalle, alertas y modelo FCM."""
import flet as ft
import flet.canvas as cv

from adherencia import base_datos as bd
from adherencia import datos_demo as demo
from movil import paciente, ui

SEVERIDAD = {"alta": ("Alta", "bad"), "media": ("Media", "warn")}
# Conceptos de entrada del mapa (los que no se calculan a partir de otros).
ENTRADAS = [c for ents in demo.GRUPOS.values() for c in ents if c not in demo.ESTRUCTURA]


def alertas(app, id_paciente=None):
    """[(clave, id, nombre, nivel, texto, cuando)]: primero lo que reportaron los pacientes
    desde su app (el más reciente arriba), luego las del expediente."""
    lista = [(r["clave"], r["id"], r["nombre"], r["nivel"], r["texto"], r["cuando"])
             for r in app.reportes]
    lista += [(a["clave"], a["id"], a["nombre"], a["nivel"], a["texto"], a["cuando"])
              for a in bd.alertas()]
    lista += [(f"{p['id']}-{texto}", p["id"], p["nombre"], nivel, texto, cuando)
              for p in demo.PACIENTES for nivel, texto, cuando in p["alertas"]]
    return [a for a in lista if id_paciente in (None, a[1])]


def _pendientes(app, id_paciente=None):
    atendidas = bd.atendidas()
    return [a for a in alertas(app, id_paciente) if a[0] not in atendidas]


def _kpis(app):
    cuenta = {e: sum(p["etiqueta"] == e for p in demo.PACIENTES) for e in ("Bueno", "Regular", "Malo")}
    datos = [("Pacientes", len(demo.PACIENTES), ui.TEAL), ("Bueno", cuenta["Bueno"], ui.VERDE),
             ("Regular", cuenta["Regular"], ui.AMBAR), ("Malo", cuenta["Malo"], ui.ROJO)]
    controles = [ft.Row([
        ft.Container(ft.Column([ui.sub(t, 11), ui.texto(str(v), 24, c, negrita=True)], spacing=0,
                               horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                     bgcolor=ft.Colors.WHITE, border=ft.Border.all(1, ui.BORDE),
                     border_radius=14, padding=8, expand=True)
        for t, v, c in datos], spacing=6)]
    pendientes = len(_pendientes(app))
    if pendientes > 0:
        controles.append(ui.boton(f"{pendientes} alertas sin atender", lambda: app.ir("m_alertas"),
                                  ft.Icons.NOTIFICATIONS_ACTIVE, principal=True))
    return controles


def aviso_alertas(app):
    """Al entrar al panel: si hay alertas sin atender, lo dice y lleva a la sección Alertas."""
    pendientes = _pendientes(app)
    if not pendientes:
        return
    altas = sum(nivel == "alta" for _, _, _, nivel, _, _ in pendientes)
    n = len(pendientes)

    def ver():
        app.page.pop_dialog()
        app.ir("m_alertas")

    app.page.show_dialog(ft.AlertDialog(
        icon=ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE, color=ui.ROJO, size=40),
        title=ft.Text(f"Tienes {n} {'alerta' if n == 1 else 'alertas'}",
                      text_align=ft.TextAlign.CENTER),
        content=ft.Column([
            ui.texto("Puedes revisarlas en la sección Alertas.", 16,
                     text_align=ft.TextAlign.CENTER),
            *([ui.chip(f"{altas} de prioridad alta", "bad")] if altas else []),
        ], tight=True, spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER, width=300),
        actions=[ft.TextButton("Después", on_click=lambda e: app.page.pop_dialog()),
                 ft.FilledButton("Ver alertas", icon=ft.Icons.NOTIFICATIONS,
                                 on_click=lambda e: ver())],
        actions_alignment=ft.MainAxisAlignment.CENTER))


def _tarjeta_paciente(app, p):
    color = ui.COLOR_ETIQUETA[p["etiqueta"]]
    chips = [ui.chip(p["etiqueta"], ui.CHIP_ETIQUETA[p["etiqueta"]])]
    pendientes = len(_pendientes(app, p["id"]))
    if pendientes:
        chips.append(ui.chip(f"🔔 {pendientes}", "bad"))

    def abrir():
        app.paciente_sel = p["id"]
        app.ir("m_detalle")

    return ui.tarjeta([
        ft.Row([
            ft.Text(ui.CARITA_ETIQUETA[p["etiqueta"]], size=34),
            ft.Column([ui.texto(f"{p['nombre']}", 16, negrita=True),
                       ui.sub(f"{p['edad']} años · {p['tratamiento']}")], spacing=0, expand=True),
            ft.Column([ft.Row(chips, spacing=4),
                       ui.texto(f"C28 = {p['c28']:.3f}", 14, color, negrita=True)],
                      spacing=4, horizontal_alignment=ft.CrossAxisAlignment.END),
        ], vertical_alignment=ft.CrossAxisAlignment.START),
        ui.barra(p["c28"], color),
        ft.Row([ui.sub("Últimos 7 días", 11), ft.Container(
            ui.mini_barras([v for _, v in demo.tomas_ultimos_dias(p)]), expand=True)],
            spacing=10, vertical_alignment=ft.CrossAxisAlignment.END),
    ], on_click=lambda: abrir())


def pagina_panel(app):
    lista = ft.Column(spacing=12)
    criterio = {"nivel": "Todos", "texto": ""}

    def filtrar():
        buscado = demo._normalizar(criterio["texto"].strip())
        lista.controls = [_tarjeta_paciente(app, p)
                          for p in sorted(demo.PACIENTES, key=lambda p: p["c28"])
                          if criterio["nivel"] in ("Todos", p["etiqueta"])
                          and buscado in demo._normalizar(p["nombre"])]
        if not lista.controls:
            lista.controls = [ui.sub("Ningún paciente coincide con la búsqueda.")]

    def al_cambiar(clave, valor):
        criterio[clave] = valor
        filtrar()
        lista.update()

    filtrar()
    filtro = ft.SegmentedButton(
        segments=[ft.Segment(f, label=f) for f in ("Todos", "Bueno", "Regular", "Malo")],
        selected=["Todos"], show_selected_icon=False,
        on_change=lambda e: al_cambiar("nivel", e.control.selected[0]))
    buscador = ft.TextField(hint_text="Buscar paciente por nombre", prefix_icon=ft.Icons.SEARCH,
                            bgcolor=ft.Colors.WHITE, border_radius=12, dense=True,
                            on_change=lambda e: al_cambiar("texto", e.control.value))
    return [ui.titulo("Mis pacientes", "Ordenados del que más atención necesita al que menos. "
                                       "Toca uno para ver su ficha."),
            *_kpis(app), buscador, filtro, lista, *_registrados(app)]


def _registrados(app):
    """Pacientes que entraron con su folio y contestaron encuestas en este dispositivo."""
    registrados = bd.pacientes_registrados()
    if not registrados:
        return []

    def abrir(folio):
        app.paciente_sel = folio
        app.ir("m_detalle")

    filas = [ft.Container(ui.fila(
        ft.Column([ui.texto(f"Folio {folio}", negrita=True),
                   ui.sub(f"Última encuesta: {bd.cuando(ultima)}")], spacing=0),
        ui.chip(f"{n}/9 encuestas", "ok" if n == 9 else "info"), divisor=False),
        on_click=lambda e, f=folio: abrir(f), ink=True, border_radius=8)
        for folio, n, ultima in registrados]
    return [ui.texto("📱 Usan la app en este dispositivo", 16, negrita=True),
            ui.tarjeta(filas)]


def pagina_detalle(app):
    p = next((x for x in demo.PACIENTES if x["id"] == app.paciente_sel), None)
    if p is None:
        return _detalle_registrado(app, app.paciente_sel)
    color = ui.COLOR_ETIQUETA[p["etiqueta"]]
    controles = [ui.tarjeta(ft.Row([
        ui.anillo(p["c28"], f"{p['c28']:.2f}", "C28", color,
                  carita=ui.CARITA_ETIQUETA[p["etiqueta"]]),
        ft.Column([ui.texto(p["nombre"], 17, negrita=True),
                   ui.sub(f"{p['edad']} años · {p['tratamiento']}"),
                   ft.Row([ui.texto("Adherencia:"),
                           ui.chip(p["etiqueta"], ui.CHIP_ETIQUETA[p["etiqueta"]])])],
                  expand=True, spacing=4),
    ], spacing=16))]

    for _, _, _, nivel, texto, cuando in _pendientes(app, p["id"]):
        etiqueta, _ = SEVERIDAD[nivel]
        controles.append(ui.aviso(f"**Alerta {etiqueta.lower()}** · {texto} · {cuando}"))

    # Explicación: los conceptos de entrada más bajos son los que más jalan C28 hacia abajo.
    debiles = sorted(ENTRADAS, key=lambda c: p["valores"][c])[:3]
    controles.append(ui.tarjeta([
        ui.sub("Son los 3 aspectos con valor más bajo; trabajar en ellos es lo que más ayuda a "
               "subir su adherencia."),
        ui.barras_h([(f"C{c} · {demo.CONCEPTOS[c]}", p["valores"][c], c) for c in debiles]),
    ], "🔍 Lo que más puede mejorar" if p["etiqueta"] == "Bueno"
        else f"🔍 ¿Por qué está en {p['etiqueta']}?"))

    dias = demo.tomas_ultimos_dias(p)
    tomadas = sum(round(v * len(demo.HORARIOS) / 100) for _, v in dias)
    controles.append(ui.tarjeta([
        ui.sub(f"Tomó {tomadas} de {7 * len(demo.HORARIOS)} dosis "
               f"({100 * tomadas / (7 * len(demo.HORARIOS)):.0f}%)."),
        ui.barras_v([v for _, v in dias], [d for d, _ in dias], caritas=False),
    ], "💊 Tomas de los últimos 7 días"))
    if p["id"] == "P2":  # Josefina usa la app: también se ve su ánimo
        controles.append(ui.tarjeta(_animo_paciente(app, p["id"]), "💭 Ánimo de esta semana"))

    finales = [(f"C{c} · {demo.CONCEPTOS[c]}", p["valores"][c], c) for c in (24, 25, 26, 27)]
    controles.append(ui.tarjeta(ui.barras_h(finales), "Factores que alimentan C28"))

    peor = min((24, 25, 26, 27), key=lambda c: p["valores"][c])
    controles.append(ui.tarjeta([ui.texto(f"Prioridad: {demo.CONCEPTOS[peor]}", negrita=True),
                                 ui.sub(demo.RECOMENDACION[peor])], "💡 Recomendación sugerida"))

    grupos = []
    for final, entradas in demo.GRUPOS.items():
        items = [(f"C{c} · {demo.CONCEPTOS[c]}", p["valores"][c], c) for c in entradas]
        grupos += [ui.texto(f"C{final} · {demo.CONCEPTOS[final]}", 15, negrita=True),
                   ui.barras_h(items)]
    controles.append(ft.Container(
        ft.ExpansionTile(title="Ver los 23 conceptos de entrada", controls=grupos,
                         controls_padding=16, shape=ft.RoundedRectangleBorder(radius=16),
                         collapsed_shape=ft.RoundedRectangleBorder(radius=16)),
        bgcolor=ft.Colors.WHITE, border=ft.Border.all(1, ui.BORDE), border_radius=16))

    semanas = p["semanas"]
    controles.append(ui.tarjeta(ui.barras_v(semanas, [f"S{i + 1}" for i in range(len(semanas))],
                                            caritas=False),
                                "Adherencia semanal (pastillero)"))
    controles.append(_notas(app, p["id"]))
    controles.append(ft.Row([
        ui.boton("Generar reporte", lambda: app.avisar("Próximamente"), ft.Icons.DESCRIPTION,
                 expand=True),
        ui.boton("Enviar mensaje", lambda: app.avisar("Próximamente"), ft.Icons.MESSAGE,
                 expand=True),
    ]))
    return controles


def _animo_paciente(app, id_paciente):
    """Caritas de lunes a hoy; la de hoy es la que el paciente eligió al entrar a su app."""
    animos = demo.ANIMO_SEMANA + [app.animos.get(id_paciente)]
    dias = []
    for i, dia in enumerate(demo.DIAS):
        if i < len(animos) and animos[i] is not None:
            cara = paciente.ANIMOS[animos[i]][0]
        else:
            cara = "❔" if i == paciente.HOY else "·"
        dias.append(ft.Column([ft.Text(cara, size=26), ui.sub(dia, 12, negrita=i == paciente.HOY)],
                              spacing=2, expand=True,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER))
    controles = [ft.Row(dias, spacing=0)]
    if any(a is not None and a <= 1 for a in animos):
        controles.append(ui.sub("Reportó sentirse enojado(a) o triste esta semana; conviene "
                                "preguntarle en la próxima consulta."))
    return controles


def _detalle_registrado(app, folio):
    """Ficha de un paciente con folio: sus encuestas guardadas, alertas, ánimo y notas."""
    resultados = bd.ultimos_resultados(folio)
    animo = bd.animo_de_hoy(folio)
    controles = [ui.tarjeta([
        ui.texto(f"Folio {folio}", 18, negrita=True),
        ui.sub(f"{len(resultados)} de 9 encuestas contestadas"),
        ft.Row([ui.texto("Ánimo de hoy:"),
                ft.Text(paciente.ANIMOS[animo][0], size=24) if animo is not None
                else ui.sub("sin registrar")]),
    ])]
    for _, _, _, nivel, texto, cuando in _pendientes(app, folio):
        etiqueta, _ = SEVERIDAD[nivel]
        controles.append(ui.aviso(f"**Alerta {etiqueta.lower()}** · {texto} · {cuando}"))
    if resultados:
        items = [(r.instrumento, r.valor_fcm, r.codigo)
                 for r in sorted(resultados.values(), key=lambda r: int(r.codigo[1:]))]
        # En olvido, salud mental y efectos secundarios un valor alto es desfavorable.
        controles.append(ui.tarjeta(ui.barras_h(items, inversos={"C3", "C4", "C7"}),
                                    "🧩 Resultados de sus encuestas"))
    tomas = bd.tomas_ultimos_dias(folio)
    if any(n for _, n in tomas):
        pcts = [round(100 * n / len(demo.HORARIOS)) for _, n in tomas]
        controles.append(ui.tarjeta(ui.barras_v(pcts, [f[8:] for f, _ in tomas], caritas=False),
                                    "💊 Tomas registradas, últimos 7 días"))
    controles.append(_notas(app, folio))
    return controles


def _notas(app, id_paciente):
    notas = bd.notas(id_paciente)
    campo = ft.TextField(hint_text="Ej. Llamar el lunes para revisar horarios", multiline=True,
                         min_lines=1, max_lines=4, bgcolor=ft.Colors.WHITE, border_radius=12)

    def guardar():
        if not (campo.value or "").strip():
            app.avisar("Escribe la nota.", error=True)
            return
        bd.agregar_nota(id_paciente, campo.value.strip())
        app.avisar("Nota guardada")
        app.dibujar()

    lista = [ui.fila(ft.Container(ui.texto(n, 14), expand=True), ui.sub(f, 12))
             for f, n in notas]
    return ui.tarjeta([*lista, campo,
                       ui.boton("Guardar nota", lambda: guardar(), ft.Icons.NOTE_ADD)],
                      "📝 Notas y plan de acción")


def pagina_alertas(app):
    controles = [ui.titulo("Alertas", "Requieren atención del personal de salud.")]

    def atender(clave):
        bd.marcar_atendida(clave)
        app.dibujar()

    def abrir(id_paciente):
        app.paciente_sel = id_paciente
        app.ir("m_detalle")

    ids = {p["id"] for p in demo.PACIENTES} | {f for f, _, _ in bd.pacientes_registrados()}
    atendidas = bd.atendidas()
    for clave, id_paciente, nombre, nivel, texto, cuando in alertas(app):
        etiqueta, tipo = SEVERIDAD[nivel]
        atendida = clave in atendidas
        contenido = [ui.fila(ft.Column([ui.texto(texto, negrita=True),
                                        ui.sub(f"{nombre} · {cuando}")], spacing=0, expand=True),
                             ui.chip("Atendida", "ok") if atendida else ui.chip(etiqueta, tipo),
                             divisor=False)]
        acciones = []
        if not atendida:
            acciones.append(ft.TextButton("Marcar como atendida", icon=ft.Icons.DONE,
                                          on_click=lambda e, c=clave: atender(c)))
        if id_paciente in ids:
            acciones.append(ft.TextButton("Ver ficha", icon=ft.Icons.PERSON,
                                          on_click=lambda e, i=id_paciente: abrir(i)))
        if acciones:
            contenido.append(ft.Row(acciones, wrap=True, spacing=0))
        controles.append(ui.tarjeta(contenido))
    controles.append(ui.sub("Protocolo: una respuesta positiva en el ítem 9 del PHQ-9 genera una "
                            "alerta inmediata al personal de salud, sin importar el puntaje total."))
    return controles


# ------------------------------------------------------------------ modelo FCM
COLOR_GRUPO = {24: ui.TEAL, 25: "#5b47b5", 26: ui.AMBAR, 27: ui.VERDE}


def _diagrama():
    """Diagrama por capas del mapa: entradas → intermedios → factores → C28."""
    capas = [[1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 14, 15, 16, 17, 20, 21, 22],
             [8, 9, 13, 18, 19, 23], [24, 25, 26, 27], [28]]
    ancho, alto = 340, 470
    xs = [30, 120, 220, 305]
    pos = {}
    for x, capa in zip(xs, capas):
        paso = (alto - 20) / (len(capa) + 1)
        for i, c in enumerate(capa):
            pos[c] = (x, 20 + paso * (i + 1))

    def grupo(c):
        return next((g for g, ents in demo.GRUPOS.items() if c in ents), c)

    formas = [cv.Text(x, 8, t, ft.TextStyle(size=10, color=ui.GRIS),
                      alignment=ft.Alignment.CENTER)
              for x, t in zip(xs, ["Entradas", "Intermedios", "Factores", "Decisión"])]
    for d, origenes in demo.ESTRUCTURA.items():
        for o in origenes:
            formas.append(cv.Line(*pos[o], *pos[d], paint=ft.Paint(
                color=ft.Colors.with_opacity(0.45, COLOR_GRUPO.get(grupo(o), "#9fb3b3")),
                stroke_width=1.4)))
    for c, (x, y) in pos.items():
        relleno = ui.TEXTO if c == 28 else COLOR_GRUPO.get(grupo(c), ui.TEAL)
        formas += [cv.Circle(x, y, 18 if c == 28 else 13, paint=ft.Paint(color=relleno)),
                   cv.Text(x, y, f"C{c}", ft.TextStyle(size=9.5, color=ft.Colors.WHITE,
                                                      weight=ft.FontWeight.BOLD),
                           alignment=ft.Alignment.CENTER)]
    return ft.Row([cv.Canvas(formas, width=ancho, height=alto)],
                  alignment=ft.MainAxisAlignment.CENTER)


def pagina_modelo(app):
    leyenda = ft.Row([
        ft.Row([ft.Container(width=10, height=10, border_radius=5, bgcolor=c), ui.sub(t)],
               spacing=4)
        for t, c in [("Paciente", ui.TEAL), ("Médicos", "#5b47b5"), ("Tecnológicos", ui.AMBAR),
                     ("Familiares", ui.VERDE)]], wrap=True, spacing=10)
    estructura = ui.tarjeta([
        _diagrama(), leyenda,
        ui.sub("28 conceptos. Las entradas vienen de los cuestionarios, el pastillero y el "
               "expediente; C28 decide si la adherencia es Mala, Regular o Buena."),
    ], "Estructura del mapa")

    # Simulador: los deslizadores actualizan el resultado sin redibujar la pantalla.
    resultado = ft.Container()
    valores = {c: 0.6 for c in (24, 25, 26, 27)}

    def pintar_resultado():
        c28 = demo.estimar_c28(*valores.values())
        et = demo.etiqueta(c28)
        resultado.content = ui.tarjeta(ft.Row([
            ui.anillo(c28, f"{c28:.3f}", "C28", ui.COLOR_ETIQUETA[et],
                      carita=ui.CARITA_ETIQUETA[et]),
            ft.Column([ui.texto(f"Adherencia: {et}", 16, negrita=True),
                       ui.sub("Malo < 0.318 ≤ Regular < 0.6446 ≤ Bueno")], expand=True),
        ], spacing=16))

    def deslizador(c):
        valor = ui.texto(f"{valores[c]:.2f}", 14, negrita=True)

        def al_mover(e):
            valores[c] = round(e.control.value, 2)
            valor.value = f"{valores[c]:.2f}"
            pintar_resultado()
            app.page.update()

        return ft.Column([
            ft.Row([ft.Container(ui.texto(f"C{c} · {demo.CONCEPTOS[c]}", 14), expand=True), valor]),
            ft.Slider(value=valores[c], min=0, max=1, divisions=20, on_change=al_mover),
        ], spacing=0)

    pintar_resultado()
    simulador = ui.tarjeta([
        ui.sub("Mueve los factores para ver cómo cambia la clasificación (fórmula de etiquetas: "
               "C28 = 0.25 · (C24 + C25 + C26 + C27))."),
        *[deslizador(c) for c in (24, 25, 26, 27)],
    ], "Simulador de C28")

    inferencia = ft.Container(ft.ExpansionTile(
        title="¿Cómo infiere el mapa?", controls_padding=16,
        shape=ft.RoundedRectangleBorder(radius=16),
        collapsed_shape=ft.RoundedRectangleBorder(radius=16),
        controls=[ft.Markdown(
            "- Regla de Kosko con memoria, actualización síncrona:  \n"
            "  **Aᵢ(t+1) = tanh( Σⱼ wⱼᵢ·Aⱼ(t) + Aᵢ(t) )**\n"
            "- Se detiene cuando el cambio máximo es menor que 0.001 o tras ~100 iteraciones.\n"
            "- Los pesos wⱼᵢ se aprenden con PSO (optimización por enjambre de partículas).")]),
        bgcolor=ft.Colors.WHITE, border=ft.Border.all(1, ui.BORDE), border_radius=16)

    entrenamiento = ui.tarjeta([
        ui.fila(ui.sub("Precisión actual (FCM Expert)"), "65–70%"),
        ui.fila(ui.sub("IC 95% (réplica en Python, t de Student)"), "56.5–66.9%"),
        ui.fila(ui.sub("Meta"), "≈ 95%"),
        ui.fila(ui.sub("Estado"), ui.chip("En ajuste", "warn"), divisor=False),
    ], "Estado del entrenamiento")

    return [ui.titulo("Modelo FCM", "Cómo se calcula la adherencia de cada paciente."),
            estructura, simulador, resultado, inferencia, entrenamiento]
