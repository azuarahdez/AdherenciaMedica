"""Pantallas del paciente: inicio, pastillero, asistente y progreso."""
from datetime import date, datetime, timedelta
from uuid import uuid4

import flet as ft

from adherencia import base_datos as bd
from adherencia import datos_demo as demo
from movil import ui

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
TOTAL_ENCUESTAS = 9


def fecha_larga(d):
    return f"{DIAS_SEMANA[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def proxima_cita():
    return fecha_larga(date.today() + timedelta(days=7))


# ------------------------------------------------------------------ tomas del día
def tomadas(app):
    if app.tomadas is None:
        app.tomadas = {h for h, _, est, _ in demo.DOSIS_HOY if est == "tomada"}
        if not app.demo:
            app.tomadas |= bd.tomas_de_hoy(app.paciente)
    return app.tomadas


def anotar_toma(app, hora):
    tomadas(app).add(hora)
    if not app.demo:
        bd.registrar_toma(app.paciente, hora)


def proxima_dosis(app):
    return next(((h, med) for h, med, _, _ in demo.DOSIS_HOY if h not in tomadas(app)), None)


def registrar_toma(app, hora):
    anotar_toma(app, hora)
    app.avisar(f"Toma de las {hora} registrada ✅")
    app.dibujar()


def estado_dosis(app, hora, nota):
    if hora in tomadas(app):
        return ui.chip("✓ Tomada", "ok"), nota or "Registrada hoy"
    siguiente = proxima_dosis(app)
    if siguiente and siguiente[0] == hora:
        return ui.chip("⏰ Siguiente", "warn"), nota
    return ui.chip("Más tarde", "gris"), nota


# ------------------------------------------------------------------ estado de ánimo
ANIMOS = [  # (emoji, etiqueta, título de la frase, frase al elegirlo)
    ("😠", "Enojado", "Respira profundo",
     "Es normal tener días difíciles. Si algo de tu tratamiento te molesta, platícalo con tu "
     "equipo de salud: estamos para ayudarte."),
    ("😢", "Triste", "No estás solo(a)",
     "Gracias por contárnoslo. Si la tristeza continúa varios días, coméntalo con tu equipo de "
     "salud. Cuidarte también es tomar tu tratamiento."),
    ("😐", "Normal", "Un paso a la vez",
     "Cada dosis que tomas cuenta. ¡Sigue así con tu tratamiento!"),
    ("🙂", "Feliz", "¡Qué gusto!",
     "Nos alegra que te sientas bien. Tu constancia está dando resultados."),
    ("😄", "Súper feliz", "¡Excelente día!",
     "¡Esa energía es contagiosa! Aprovéchala y no olvides tus tomas de hoy."),
]


def elegir_animo(app, indice):
    """Guarda el ánimo y muestra una frase de acompañamiento según la carita elegida."""
    app.animo = indice
    if app.demo:
        app.animos[app.id_paciente()] = indice
    else:
        bd.guardar_animo(app.paciente, indice)
    app.page.pop_dialog()
    app.dibujar()
    emoji, _, titulo_frase, frase = ANIMOS[indice]
    app.despues(lambda: app.page.show_dialog(ft.AlertDialog(
        content=ft.Column([
            ft.Text(emoji, size=64, text_align=ft.TextAlign.CENTER),
            ui.texto(titulo_frase, 22, negrita=True, text_align=ft.TextAlign.CENTER),
            ui.texto(frase, 16, ui.GRIS, text_align=ft.TextAlign.CENTER),
        ], tight=True, spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=320),
        actions=[ft.FilledButton("Continuar", on_click=lambda e: app.page.pop_dialog())],
        actions_alignment=ft.MainAxisAlignment.CENTER)))


def encuesta_animo(app):
    """Diálogo sobrepuesto con 5 caritas, de enojado a súper feliz."""
    def carita(i):
        emoji, etiqueta, *_ = ANIMOS[i]
        elegida = app.animo == i
        return ft.Container(
            ft.Column([ft.Text(emoji, size=34), ui.texto(etiqueta, 11, ui.TEXTO,
                                                          text_align=ft.TextAlign.CENTER)],
                      spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            expand=True, padding=ft.Padding.symmetric(vertical=8), border_radius=14,
            bgcolor="#e3f1f1" if elegida else None,
            border=ft.Border.all(2, ui.TEAL) if elegida else None,
            on_click=lambda e: elegir_animo(app, i), ink=True)

    app.page.show_dialog(ft.AlertDialog(
        title=ft.Text("¿Cómo te sientes hoy?", text_align=ft.TextAlign.CENTER),
        content=ft.Container(ft.Column([ft.Row([carita(i) for i in range(len(ANIMOS))],
                                               spacing=2,
                                               vertical_alignment=ft.CrossAxisAlignment.START)],
                                       tight=True),
                             width=360),
        actions=[ft.TextButton("Ahora no", on_click=lambda e: app.page.pop_dialog())],
        actions_alignment=ft.MainAxisAlignment.CENTER))


# ------------------------------------------------------------------ síntomas
SINTOMAS = ["Mareo", "Náusea", "Dolor de cabeza", "Cansancio", "Dolor de estómago", "Otro"]
INTENSIDADES = ["Muy leve", "Leve", "Moderado", "Fuerte", "Muy fuerte"]


def reportar_sintoma(app):
    """Diálogo para avisar al equipo de salud de un síntoma; de 4/5 en adelante es alerta alta."""
    elegido = {"sintoma": None, "intensidad": 3}
    opciones = ft.Row(wrap=True, spacing=6, run_spacing=6)
    nivel = ui.texto(INTENSIDADES[2], 14, ui.TEAL_OSCURO, negrita=True)

    def pintar_opciones():
        opciones.controls = [ft.Container(
            ui.texto(s, 14, ft.Colors.WHITE if s == elegido["sintoma"] else ui.TEXTO),
            bgcolor=ui.TEAL if s == elegido["sintoma"] else "#eef1f3", border_radius=999,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8), ink=True,
            on_click=lambda e, s=s: elegir(s)) for s in SINTOMAS]

    def elegir(sintoma):
        elegido["sintoma"] = sintoma
        pintar_opciones()
        app.page.update()

    def mover(e):
        elegido["intensidad"] = int(e.control.value)
        nivel.value = INTENSIDADES[elegido["intensidad"] - 1]
        app.page.update()

    def enviar(e):
        if elegido["sintoma"] is None:
            app.avisar("Elige qué sientes.", error=True)
            return
        n = elegido["intensidad"]
        texto = f"Síntoma: {elegido['sintoma'].lower()} ({INTENSIDADES[n - 1].lower()}, {n}/5)"
        nivel_alerta = "alta" if n >= 4 else "media"
        if app.demo:
            app.reportes.insert(0, {"clave": f"R{uuid4().hex[:8]}", "id": app.id_paciente(),
                                    "nombre": app.nombre, "texto": texto, "nivel": nivel_alerta,
                                    "cuando": f"hoy {datetime.now():%H:%M}"})
        else:
            bd.agregar_alerta(app.paciente, None, nivel_alerta, texto)
        app.page.pop_dialog()
        app.avisar("Listo, tu equipo de salud ya lo puede ver 🩺")

    pintar_opciones()
    app.page.show_dialog(ft.AlertDialog(
        title=ft.Text("¿Qué sientes?"),
        content=ft.Column([
            opciones, ft.Row([ui.sub("¿Qué tan fuerte es?"), nivel], spacing=6),
            ft.Slider(value=3, min=1, max=5, divisions=4, on_change=mover),
            ui.sub("No suspendas tu medicamento sin hablar antes con tu médico.", 12),
        ], tight=True, spacing=8, width=340),
        actions=[ft.TextButton("Cancelar", on_click=lambda e: app.page.pop_dialog()),
                 ft.FilledButton("Avisar a mi equipo", on_click=enviar)]))


def pagina_inicio(app):
    nombre = app.nombre or app.paciente
    # La pregunta "¿Cómo te sientes hoy?" aparece sola al entrar (ver App.entrar_paciente).
    controles = [ui.hero([
        ui.texto(fecha_larga(date.today()).capitalize(), 13, "#d9f3f1"),
        ui.texto(f"Hola, {nombre} 👋", 24, ft.Colors.WHITE, negrita=True),
    ])]

    siguiente = proxima_dosis(app)
    if siguiente:
        hora, med = siguiente
        controles += [
            ui.tarjeta([ui.sub("Tu próxima toma"), ui.texto(f"{hora} · {med}", 20, negrita=True)]),
            ui.boton("Ya me la tomé", lambda: registrar_toma(app, hora), ft.Icons.CHECK_CIRCLE,
                     principal=True),
        ]
    else:
        controles.append(ui.tarjeta(ui.sub("Ya registraste todas tus tomas de hoy."),
                                    "🎉 ¡Listo por hoy!"))

    filas = []
    for hora, med, _, nota in demo.DOSIS_HOY:
        chip, detalle = estado_dosis(app, hora, nota)
        izq = ft.Column([ui.texto(f"{hora} · {med}", negrita=True)] +
                        ([ui.sub(detalle)] if detalle else []), spacing=0)
        filas.append(ui.fila(izq, chip, divisor=hora != demo.DOSIS_HOY[-1][0]))
    controles.append(ui.tarjeta(filas, "💊 Tus tomas de hoy"))

    adherencia = demo.SEMANAS_PACIENTE[-1]
    controles.append(ui.tarjeta(ft.Row([
        ui.anillo(adherencia / 100, f"{adherencia}%", "esta semana", ui.VERDE,
                  carita=ui.carita_pct(adherencia)),
        ft.Column([ui.texto("¡Vas muy bien!", 16, negrita=True),
                   ui.sub("Tomaste 19 de 21 dosis en los últimos 7 días, 7 puntos más que la "
                          "semana pasada."),
                   ft.Row([ui.chip("🔥 3 días seguidos", "ok")])], expand=True, spacing=6),
    ], spacing=16)))

    controles.append(ui.boton("Reportar un síntoma", lambda: reportar_sintoma(app),
                              ft.Icons.HEALTH_AND_SAFETY))
    pendientes = TOTAL_ENCUESTAS - len(app.resultados)
    if pendientes:
        controles.append(ui.boton(f"Tienes {pendientes} encuestas pendientes",
                                  lambda: app.ir("menu"), ft.Icons.ASSIGNMENT))
    controles += [
        ui.tarjeta([
            ui.fila(ft.Column([ui.sub("📅 Próxima cita"),
                               ui.texto(proxima_cita().capitalize(), negrita=True)], spacing=0),
                    "10:30", divisor=False),
            ui.sub("Consulta de control en tu clínica"),
        ]),
        ui.tarjeta([ui.sub("💡 Consejo del día"),
                    ui.texto("Deja tu pastillero junto a algo que uses todas las mañanas, como el "
                             "cepillo de dientes o la cafetera.")]),
    ]
    return controles


# ------------------------------------------------------------------ pastillero
COLOR_CELDA = {"t": (ui.VERDE, "✓"), "o": (ui.ROJO, "✕"), "p": (ui.AMBAR, "•"),
               "f": ("#dde7e7", "")}
HORA_POR_HORARIO = dict(zip(demo.HORARIOS, [h for h, *_ in demo.DOSIS_HOY]))
HOY = 3  # índice del jueves en la cuadrícula


def _celda(contenido, color=None, ancho=None, expand=True):
    return ft.Container(contenido, bgcolor=color, height=32, border_radius=8, width=ancho,
                        expand=expand, alignment=ft.Alignment.CENTER)


def caritas_dia(app):
    """😄 todas las tomas del día · 😟 alguna sin abrir · ⏳ hoy con tomas pendientes."""
    caritas = []
    for d in range(len(demo.DIAS)):
        estados = [fila[d] for fila in demo.PASTILLERO]
        if d == HOY:
            estados = ["t" if HORA_POR_HORARIO[h] in tomadas(app) else e
                       for h, e in zip(demo.HORARIOS, estados)]
        if "o" in estados:
            caritas.append("😟")
        elif all(e == "t" for e in estados):
            caritas.append("😄")
        elif d == HOY:
            caritas.append("⏳")
        else:
            caritas.append("")
    return caritas


def pagina_pastillero(app):
    siguiente = proxima_dosis(app)
    estado = ui.tarjeta([
        ui.fila(ft.Column([ui.texto("Pastillero inteligente", 16, negrita=True),
                           ui.sub("Sincronizado hace 5 min")], spacing=0),
                ui.chip("● Conectado", "ok")),
        ui.fila(ui.sub("Batería"), "78%"),
        ui.fila(ui.sub("Próxima apertura"), siguiente[0] if siguiente else "Mañana 08:00",
                divisor=False),
    ])

    renglones = [ft.Row([_celda(None, ancho=56, expand=False)] +
                        [_celda(ui.sub(d, 12)) for d in demo.DIAS], spacing=4)]
    for horario, fila in zip(demo.HORARIOS, demo.PASTILLERO):
        fila = list(fila)
        if HORA_POR_HORARIO[horario] in tomadas(app):
            fila[HOY] = "t"
        renglones.append(ft.Row(
            [_celda(ui.sub(horario, 12), ancho=56, expand=False)] +
            [_celda(ui.texto(COLOR_CELDA[c][1], 13, ft.Colors.WHITE, negrita=True),
                    COLOR_CELDA[c][0]) for c in fila], spacing=4))
    renglones.append(ft.Row([_celda(ui.sub("Día", 12), ancho=56, expand=False)] +
                            [_celda(ft.Text(c, size=20)) for c in caritas_dia(app)], spacing=4))
    leyenda = ft.Row([ui.chip("✓ A tiempo", "ok"), ui.chip("✕ Sin abrir", "bad"),
                      ui.chip("• Pendiente", "warn")], wrap=True, spacing=6)
    cuadricula = ui.tarjeta([ft.Column(renglones, spacing=4), leyenda], "📅 Esta semana")

    controles = [ui.titulo("Pastillero", "Se registra solo cuando abres el compartimento a tu hora."),
                 estado, cuadricula]
    if siguiente:
        controles.append(ui.boton(f"Abrir compartimento de las {siguiente[0]}",
                                  lambda: registrar_toma(app, siguiente[0]),
                                  ft.Icons.MEDICATION))
    controles.append(ui.sub("El pastillero detecta que se abrió el compartimento, no que se haya "
                            "ingerido la pastilla. También puedes registrar tus tomas desde Inicio "
                            "o el Asistente."))
    return controles


# ------------------------------------------------------------------ asistente
def _burbuja(rol, mensaje):
    es_usuario = rol == "user"
    return ft.Row([ft.Container(
        ft.Markdown(mensaje), padding=12, width=290,
        bgcolor="#d7efed" if es_usuario else ft.Colors.WHITE,
        border=None if es_usuario else ft.Border.all(1, ui.BORDE),
        border_radius=ft.BorderRadius.only(top_left=16, top_right=16,
                                           bottom_left=16 if es_usuario else 4,
                                           bottom_right=4 if es_usuario else 16))],
        alignment=ft.MainAxisAlignment.END if es_usuario else ft.MainAxisAlignment.START)


def pagina_asistente(app):
    if app.chat is None:
        app.chat = [("assistant", "¡Hola! Soy tu asistente de tratamiento 🤖. "
                                  "¿En qué te puedo ayudar hoy?")]

    def enviar(mensaje):
        mensaje = (mensaje or "").strip()
        if not mensaje:
            return
        if mensaje == demo.RESPUESTAS_RAPIDAS[0] and proxima_dosis(app):
            anotar_toma(app, proxima_dosis(app)[0])
        app.chat.append(("user", mensaje))
        app.chat.append(("assistant", demo.responder(mensaje, proxima_cita())))
        app.dibujar()

    entrada = ft.TextField(hint_text="Escribe un mensaje…", expand=True, border_radius=24,
                           bgcolor=ft.Colors.WHITE, on_submit=lambda e: enviar(e.control.value))
    rapidas = ft.Row([ft.OutlinedButton(r, on_click=lambda e, r=r: enviar(r))
                      for r in demo.RESPUESTAS_RAPIDAS], wrap=True, spacing=6, run_spacing=6)
    return [
        ui.titulo("Asistente", "Pregúntame sobre tus tomas, síntomas o citas."),
        *[_burbuja(rol, m) for rol, m in app.chat],
        rapidas,
        ft.Row([entrada, ft.IconButton(ft.Icons.SEND, icon_color=ui.TEAL,
                                       on_click=lambda: enviar(entrada.value))]),
    ]


# ------------------------------------------------------------------ progreso
def animo_semana(app):
    """Caritas de ánimo de lunes a hoy (jueves); los días que faltan quedan vacíos."""
    animos = demo.ANIMO_SEMANA + [app.animo]
    dias = []
    for i, dia in enumerate(demo.DIAS):
        if i < len(animos) and animos[i] is not None:
            cara = ANIMOS[animos[i]][0]
        else:
            cara = "❔" if i == HOY else "·"
        dias.append(ft.Column([ft.Text(cara, size=28), ui.sub(dia, 12, negrita=i == HOY)],
                              spacing=2, expand=True,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER))
    controles = [ft.Row(dias, spacing=0)]
    if app.animo is None:
        controles.append(ui.boton("Registrar cómo me siento hoy", lambda: encuesta_animo(app),
                                  ft.Icons.MOOD))
    return controles


# Rebanadas del pastel: (dosis tomadas en el día, carita, color, texto de la leyenda)
TIPOS_DIA = [(3, "😄", ui.VERDE, "Tomaste todas tus dosis"),
             (2, "😐", ui.AMBAR, "Te faltó una dosis"),
             (0, "😟", ui.ROJO, "Te faltaron 2 o más")]


def tipo_dia(pct):
    tomadas = round(pct * len(demo.HORARIOS) / 100)
    return next(i for i, (minimo, *_) in enumerate(TIPOS_DIA) if tomadas >= minimo)


def pastel_dias(dias):
    """Pastel de los últimos 7 días agrupados por cuántas dosis se tomaron cada día."""
    cuenta = [0] * len(TIPOS_DIA)
    for _, pct in dias:
        cuenta[tipo_dia(pct)] += 1
    leyenda = [ft.Row([ft.Container(width=12, height=12, border_radius=6, bgcolor=color),
                       ft.Text(carita, size=18), ft.Container(ui.texto(texto, 14), expand=True),
                       ui.texto(f"{n} {'día' if n == 1 else 'días'}", 14, negrita=True)],
                      spacing=8)
               for n, (_, carita, color, texto) in zip(cuenta, TIPOS_DIA)]
    return [ui.pastel([(n, color, carita) for n, (_, carita, color, _) in zip(cuenta, TIPOS_DIA)]),
            ft.Column(leyenda, spacing=6)]


def pagina_progreso(app):
    semanas = demo.SEMANAS_PACIENTE
    esta_semana = semanas[-1]
    dias = demo.adherencia_ultimos_dias()
    controles = [ui.titulo("Mi progreso"),
                 ui.tarjeta([ui.termometro_caritas(esta_semana),
                             ui.sub(f"Esta semana tomaste el {esta_semana}% de tus dosis. "
                                    f"La semana pasada: {semanas[-2]}% {ui.carita_pct(semanas[-2])}",
                                    text_align=ft.TextAlign.CENTER)],
                            "😊 ¿Cómo va tu adherencia?"),
                 ui.tarjeta(pastel_dias(dias), "📅 Tus últimos 7 días"),
                 ui.tarjeta(animo_semana(app), "💭 Tu ánimo esta semana")]
    if app.resultados:
        items = [(r.instrumento, r.valor_fcm, r.codigo)
                 for r in sorted(app.resultados.values(), key=lambda r: int(r.codigo[1:]))]
        # En olvido, salud mental y efectos secundarios un valor alto es desfavorable.
        controles.append(ui.tarjeta(ui.barras_h(items, inversos={"C3", "C4", "C7"}),
                                    "🧩 Resultados de tus encuestas"))
    else:
        controles.append(ui.tarjeta(ui.sub("Contesta tus encuestas para ver aquí tus resultados."),
                                    "🧩 Resultados de tus encuestas"))
    logros = [ui.chip("🔥 3 días seguidos", "ok"), ui.chip("📋 Primera encuesta", "info"),
              ui.chip("📅 Asististe a 4 citas", "info"), ui.chip("🏆 90% en una semana", "ok")]
    controles.append(ui.tarjeta(ft.Row(logros, wrap=True, spacing=6, run_spacing=6), "🏅 Logros"))
    return controles
