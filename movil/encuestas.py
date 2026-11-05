"""Encuestas del paciente (funcionales): cada una calcula su valor FCM."""
import flet as ft

from adherencia import instrumentos as ins
from adherencia.base_datos import guardar_encuesta
from movil import ui


# ------------------------------------------------------------------ piezas de formulario
class Pregunta:
    """Opción múltiple sin respuesta por defecto. `opciones` es {valor: etiqueta}."""

    def __init__(self, texto, opciones):
        self.valores = list(opciones)
        self.grupo = ft.RadioGroup(ft.Column(
            [ft.Radio(value=str(i), label=et) for i, et in enumerate(opciones.values())],
            spacing=0))
        self.control = ui.tarjeta([ui.texto(texto, 15, negrita=True), self.grupo])

    @property
    def valor(self):
        return None if self.grupo.value is None else self.valores[int(self.grupo.value)]


class PreguntaPuntos(Pregunta):
    """Opciones {etiqueta: puntos}; `valor` devuelve (etiqueta, puntos) o None."""

    def __init__(self, texto, opciones):
        self.puntos = opciones
        super().__init__(texto, {et: et for et in opciones})

    @property
    def valor(self):
        etiqueta = super().valor
        return None if etiqueta is None else (etiqueta, self.puntos[etiqueta])


def campo_numero(etiqueta, valor=0):
    return ft.TextField(label=etiqueta, value=str(valor), keyboard_type=ft.KeyboardType.NUMBER,
                        input_filter=ft.NumbersOnlyInputFilter(), bgcolor=ft.Colors.WHITE,
                        border_radius=12)


def numero(campo):
    return int(campo.value) if campo.value.strip() else 0


def registrar(app, resultado, respuestas):
    app.resultados[resultado.codigo] = resultado
    if not app.demo:
        guardar_encuesta(app.paciente, resultado, respuestas)
    app.avisar(f"{resultado.instrumento}: guardado ✅")
    app.ir("menu")


def guardar_boton(al_guardar):
    return ui.boton("Guardar", lambda: al_guardar(), ft.Icons.SAVE, principal=True)


def faltan(app):
    app.avisar("Contesta todas las preguntas.", error=True)


# ------------------------------------------------------------------ menú
def pagina_menu(app):
    hechos = len(app.resultados)
    controles = [
        ui.titulo("Encuestas", "Toca una para contestarla. Te toman pocos minutos."),
        ft.Column([ui.sub(f"{hechos} de {len(CUESTIONARIOS)} completadas"),
                   ui.barra(hechos / len(CUESTIONARIOS), ui.TEAL, 8)], spacing=4),
    ]
    if hechos:
        controles.append(ui.boton("Ver mis resultados", lambda: app.ir("resultados"),
                                  ft.Icons.INSIGHTS, principal=True))
    # Primero las pendientes, después las contestadas.
    for codigo, nombre, pagina, duracion, _ in sorted(CUESTIONARIOS,
                                                      key=lambda c: c[0] in app.resultados):
        hecho = codigo in app.resultados
        controles.append(ui.tarjeta(ft.Row([
            ft.Icon(ft.Icons.CHECK_CIRCLE if hecho else ft.Icons.RADIO_BUTTON_UNCHECKED,
                    color=ui.VERDE if hecho else ui.GRIS),
            ft.Column([ui.texto(nombre, 16, negrita=True),
                       ui.sub("contestada" if hecho else duracion)], spacing=0, expand=True),
            ft.Icon(ft.Icons.CHEVRON_RIGHT, color=ui.GRIS),
        ]), on_click=lambda e, p=pagina: app.ir(p), padding=14))
    return controles


# ------------------------------------------------------------------ cuestionarios
def pagina_motivacion(app):
    preguntas = [Pregunta(t, ins.LIKERT_ACUERDO) for t in ins.MOTIVACION_ITEMS]

    def al_guardar():
        resp = [p.valor for p in preguntas]
        if None in resp:
            return faltan(app)
        registrar(app, ins.calcular_motivacion(resp), resp)

    return [ui.sub("Indica qué tan de acuerdo estás con cada frase."),
            *[p.control for p in preguntas], guardar_boton(al_guardar)]


def pagina_salud_mental(app):
    phq = [Pregunta(f"{i + 1}. {t}", ins.PHQ9_OPCIONES) for i, t in enumerate(ins.PHQ9_ITEMS)]
    gad = [Pregunta(f"{i + 1}. {t}", ins.GAD7_OPCIONES) for i, t in enumerate(ins.GAD7_ITEMS)]

    def al_guardar():
        r_phq, r_gad = [p.valor for p in phq], [p.valor for p in gad]
        if None in r_phq or None in r_gad:
            return faltan(app)
        resultado = ins.calcular_salud_mental(r_phq, r_gad)
        if resultado.alertas:
            app.mostrar_apoyo = True
        registrar(app, resultado, {"PHQ-9": r_phq, "GAD-7": r_gad})

    return [ui.texto("PHQ-9", 18, negrita=True), ui.texto(ins.PHQ9_INSTRUCCION),
            *[p.control for p in phq],
            ui.texto("GAD-7", 18, negrita=True), ui.texto(ins.GAD7_INSTRUCCION),
            *[p.control for p in gad],
            guardar_boton(al_guardar),
            ui.sub("PHQ-9 y GAD-7 desarrollados por los Drs. Robert L. Spitzer, Janet B.W. "
                   "Williams, Kurt Kroenke y colegas, con una beca educacional de Pfizer Inc.")]


def pagina_olvido(app):
    olvidos = campo_numero("En los últimos 7 días, ¿cuántas dosis no pudiste tomar?")

    def al_guardar():
        n = min(numero(olvidos), 50)
        registrar(app, ins.calcular_olvido(n), {"olvidos_semana": n})

    return [ui.sub("Si no usas el pastillero, registra aquí tus tomas de la semana."),
            olvidos, guardar_boton(al_guardar)]


def pagina_habitos(app):
    preguntas = [PreguntaPuntos(t, ops) for t, ops in ins.HABITOS_ITEMS.items()]

    def al_guardar():
        resp = [p.valor for p in preguntas]
        if None in resp:
            return faltan(app)
        registrar(app, ins.calcular_habitos([pt for _, pt in resp]), [e for e, _ in resp])

    return [ui.sub("No hay respuestas buenas ni malas; esta información sirve para darte "
                   "recomendaciones de bienestar."),
            *[p.control for p in preguntas], guardar_boton(al_guardar)]


def _deslizador(sintoma):
    etiqueta = ui.texto(ins.EFECTOS_INTENSIDAD[0], 14, ui.TEAL_OSCURO, negrita=True)

    def al_mover(e):
        etiqueta.value = ins.EFECTOS_INTENSIDAD[int(e.control.value)]
        etiqueta.update()

    deslizador = ft.Slider(value=0, min=0, max=5, divisions=5, on_change=al_mover)
    tarjeta = ui.tarjeta([ft.Row([ui.texto(sintoma, 15, negrita=True), etiqueta],
                                 alignment=ft.MainAxisAlignment.SPACE_BETWEEN), deslizador])
    return tarjeta, deslizador


def pagina_efectos(app):
    deslizadores = [_deslizador(s) for s in ins.EFECTOS_SINTOMAS]
    interfiere = Pregunta("¿Algún síntoma te impidió hacer tus actividades diarias?",
                          {False: "No", True: "Sí"})

    def al_guardar():
        if interfiere.valor is None:
            return app.avisar("Contesta la última pregunta.", error=True)
        intens = [int(d.value) for _, d in deslizadores]
        registrar(app, ins.calcular_efectos(intens, interfiere.valor),
                  {"intensidades": dict(zip(ins.EFECTOS_SINTOMAS, intens)),
                   "interfiere_rutina": interfiere.valor})

    return [ui.sub("En la última semana, ¿tuviste alguno de estos síntomas? ¿Con qué intensidad?"),
            *[t for t, _ in deslizadores], interfiere.control, guardar_boton(al_guardar),
            ui.sub("Si un síntoma es muy fuerte, no suspendas ni cambies tu medicamento por tu "
                   "cuenta: comunícate con tu médico.")]


def pagina_apoyo(app):
    preguntas = [Pregunta(t, ins.LIKERT_FRECUENCIA) for t in ins.APOYO_ITEMS]
    bloque = ft.Column([p.control for p in preguntas], spacing=12)

    def al_cambiar(e):
        bloque.visible = not e.control.value
        bloque.update()

    sin_familia = ft.Checkbox(label="No cuento con familiares cercanos", on_change=al_cambiar)

    def al_guardar():
        resp = [] if sin_familia.value else [p.valor for p in preguntas]
        if None in resp:
            return faltan(app)
        registrar(app, ins.calcular_apoyo(resp, bool(sin_familia.value)),
                  {"respuestas": resp, "sin_familia": bool(sin_familia.value)})

    return [ui.sub("Tus respuestas no se comparten con tus familiares."),
            sin_familia, bloque, guardar_boton(al_guardar)]


def pagina_seguimiento(app):
    programadas = campo_numero("Citas programadas en el periodo", 1)
    asistidas = campo_numero("Citas a las que asististe")

    def al_guardar():
        prog, asis = numero(programadas), numero(asistidas)
        if prog < 1:
            return app.avisar("Escribe al menos 1 cita programada.", error=True)
        if asis > prog:
            return app.avisar("Las citas asistidas no pueden ser más que las programadas.",
                              error=True)
        registrar(app, ins.calcular_seguimiento(prog, asis),
                  {"programadas": prog, "asistidas": asis})

    return [ui.sub("Normalmente este dato lo registra tu clínica."),
            programadas, asistidas, guardar_boton(al_guardar)]


def pagina_carga(app):
    ingreso = campo_numero("¿Cuál es su ingreso mensual aproximado? ($)")
    costo = campo_numero("¿Cuál es el costo mensual aproximado de su tratamiento? ($)")

    def al_guardar():
        i, c = numero(ingreso), numero(costo)
        if i <= 0:
            return app.avisar("Escribe un ingreso mayor a 0.", error=True)
        app.ingreso = i
        registrar(app, ins.calcular_carga(i, c), {"ingreso": i, "costo": c})

    return [ui.sub("Basta con cantidades aproximadas. Esta información solo se usa para "
                   "orientarte hacia programas de apoyo, nunca para limitar tu tratamiento."),
            ingreso, costo, guardar_boton(al_guardar)]


def pagina_socio(app):
    preguntas = {}
    for t, ops in ins.SOCIO_ITEMS.items():
        if t == "Ingreso mensual aproximado" and app.ingreso is not None:
            # Ya se preguntó en "Costo del tratamiento": no se vuelve a pedir.
            continue
        preguntas[t] = PreguntaPuntos(t, ops)

    def al_guardar():
        resp = {}
        for t, ops in ins.SOCIO_ITEMS.items():
            if t in preguntas:
                resp[t] = preguntas[t].valor
            else:
                rango = ins.rango_ingreso(app.ingreso)
                resp[t] = (rango, ops[rango])
        if None in resp.values():
            return faltan(app)
        registrar(app, ins.calcular_socioeconomico([p for _, p in resp.values()]),
                  {t: e for t, (e, _) in resp.items()})

    return [ui.sub("Solo se usa para adaptar el acompañamiento, nunca para decidir tu acceso al "
                   "tratamiento."),
            *[p.control for p in preguntas.values()], guardar_boton(al_guardar)]


# ------------------------------------------------------------------ resultados
def pagina_resultados(app):
    resultados = sorted(app.resultados.values(), key=lambda r: int(r.codigo[1:]))
    filas = [ui.fila(ft.Column([ui.texto(r.instrumento, negrita=True),
                                ui.sub(f"{r.codigo} · {r.nivel}")], spacing=0),
                     ui.texto(f"{r.valor_fcm:.3f}", 18, negrita=True),
                     divisor=r is not resultados[-1])
             for r in resultados]

    async def exportar():
        csv = "Factor,Valor FCM\n" + "\n".join(f"{r.codigo},{r.valor_fcm:.3f}"
                                               for r in resultados)
        ruta = await ft.FilePicker().save_file(file_name=f"fcm_{app.paciente}.csv",
                                               src_bytes=csv.encode("utf-8"))
        if ruta:
            app.avisar("Archivo guardado ✅")

    return [ui.sub("Valores que se envían al mapa cognitivo difuso (FCM). Indican posibles "
                   "riesgos, no diagnósticos."),
            *[ui.aviso(a) for r in resultados for a in r.alertas],
            ui.tarjeta(filas) if filas else ui.tarjeta(ui.sub("Aún no hay encuestas contestadas.")),
            ui.boton("Descargar valores (CSV)", exportar, ft.Icons.DOWNLOAD)]


def aviso_apoyo(app):
    async def llamar_linea():
        await ft.UrlLauncher().launch_url("tel:8009112000")

    async def llamar_911():
        await ft.UrlLauncher().launch_url("tel:911")

    return ui.aviso(ft.Column([
        ft.Markdown("Gracias por tu honestidad. Tu equipo de salud será notificado para darte "
                    "acompañamiento. Si sientes que estás en peligro, llama al **911** o a la "
                    "**Línea de la Vida: 800 911 2000** (gratuita, 24 horas)."),
        ft.Row([ft.FilledButton("Llamar a la Línea de la Vida", icon=ft.Icons.CALL,
                                bgcolor=ui.ROJO, on_click=llamar_linea),
                ft.TextButton("911", icon=ft.Icons.CALL, on_click=llamar_911)],
               wrap=True),
    ], spacing=8), "warn")


CUESTIONARIOS = [
    ("C1", "Motivación y actitud", "motivacion", "2–3 min", pagina_motivacion),
    ("C3", "Estado de ánimo", "salud_mental", "5–7 min", pagina_salud_mental),
    ("C4", "Tomas de medicamento", "olvido", "1 min", pagina_olvido),
    ("C5", "Hábitos y estilo de vida", "habitos", "3–4 min", pagina_habitos),
    ("C7", "Efectos secundarios", "efectos", "2 min", pagina_efectos),
    ("C9", "Apoyo familiar", "apoyo", "2 min", pagina_apoyo),
    ("C14", "Citas médicas", "seguimiento", "1 min", pagina_seguimiento),
    ("C16", "Costo del tratamiento", "carga", "1 min", pagina_carga),
    ("C17", "Situación socioeconómica", "socio", "3 min", pagina_socio),
]
