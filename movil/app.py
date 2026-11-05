"""Estado de la sesión, navegación (barra inferior + botón Atrás de Android) y pantalla de entrada."""
import asyncio

import flet as ft

from adherencia import base_datos as bd
from adherencia import instrumentos as ins
from movil import encuestas, medico, paciente
from movil import ui

SECCIONES_PACIENTE = {
    "p_inicio": ("Inicio", ft.Icons.HOME_OUTLINED, ft.Icons.HOME),
    "p_pastillero": ("Pastillero", ft.Icons.MEDICATION_OUTLINED, ft.Icons.MEDICATION),
    "p_asistente": ("Asistente", ft.Icons.CHAT_OUTLINED, ft.Icons.CHAT),
    "menu": ("Encuestas", ft.Icons.ASSIGNMENT_OUTLINED, ft.Icons.ASSIGNMENT),
    "p_progreso": ("Progreso", ft.Icons.TRENDING_UP, ft.Icons.TRENDING_UP),
}
SECCIONES_MEDICO = {
    "m_panel": ("Pacientes", ft.Icons.GROUPS_OUTLINED, ft.Icons.GROUPS),
    "m_alertas": ("Alertas", ft.Icons.NOTIFICATIONS_OUTLINED, ft.Icons.NOTIFICATIONS),
    "m_modelo": ("Modelo", ft.Icons.HUB_OUTLINED, ft.Icons.HUB),
}

PAGINAS = {
    "p_inicio": paciente.pagina_inicio, "p_pastillero": paciente.pagina_pastillero,
    "p_asistente": paciente.pagina_asistente, "p_progreso": paciente.pagina_progreso,
    "menu": encuestas.pagina_menu, "resultados": encuestas.pagina_resultados,
    **{pagina: funcion for _, _, pagina, _, funcion in encuestas.CUESTIONARIOS},
    "m_panel": medico.pagina_panel, "m_detalle": medico.pagina_detalle,
    "m_alertas": medico.pagina_alertas, "m_modelo": medico.pagina_modelo,
}
# Pantallas internas: a qué sección regresan con la flecha o el botón Atrás.
PADRE = {**{p: "menu" for _, _, p, _, _ in encuestas.CUESTIONARIOS}, "resultados": "menu",
         "m_detalle": "m_panel"}
TITULO_INTERNO = {**{p: nombre for _, nombre, p, _, _ in encuestas.CUESTIONARIOS},
                  "resultados": "Mis resultados", "m_detalle": "Ficha del paciente"}


class App:
    def __init__(self, page: ft.Page):
        self.page = page
        page.title = "Adherencia"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.theme = ft.Theme(color_scheme_seed=ui.TEAL)
        page.on_view_pop = lambda e: self.ir(PADRE.get(self.pagina, self.pagina))
        self._base = None  # vista raíz "/" (ver dibujar)
        # Los pacientes con folio guardan todo en la base de datos (adherencia/base_datos.py).
        # El paciente de ejemplo no se guarda: lo que reporta vive aquí y sobrevive a "Salir"
        # para que el personal de salud lo vea en el mismo dispositivo.
        self.reportes = []  # síntomas del paciente de ejemplo: dict(clave, id, nombre, ...)
        self.animos = {}    # "P2" → índice de paciente.ANIMOS elegido hoy por el ejemplo
        self.reiniciar()

    # ------------------------------------------------------------- estado
    def reiniciar(self):
        self.rol = None
        self.paciente = self.nombre = None
        self.demo = False
        self.ingreso = None
        self.resultados = {}
        self.tomadas = None
        self.chat = None
        self.mostrar_apoyo = False
        self.animo = None  # índice de paciente.ANIMOS elegido hoy
        self.paciente_sel = None
        self.pagina = "entrada"
        self.dibujar()

    def id_paciente(self):
        """El paciente de ejemplo es Josefina (P2); los demás se identifican por su folio."""
        return "P2" if self.demo else self.paciente

    def salir(self):
        self.reiniciar()

    def ir(self, pagina):
        self.pagina = pagina
        self.dibujar()

    def despues(self, funcion, segundos=0.4):
        """Ejecuta `funcion` cuando ya se dibujó la pantalla nueva. Un diálogo abierto en el
        mismo instante en que cambia la pantalla no llega a mostrarse."""
        async def tarea():
            await asyncio.sleep(segundos)
            funcion()
        self.page.run_task(tarea)

    def avisar(self, mensaje, error=False):
        self.page.show_dialog(ft.SnackBar(ft.Text(mensaje), bgcolor=ui.ROJO if error else None))

    # ------------------------------------------------------------- dibujo
    def dibujar(self):
        if self.rol is None:
            base = ft.View(route="/", controls=[pagina_entrada(self)], bgcolor=ui.FONDO,
                           padding=0)
        else:
            # Las secciones de la barra comparten la ruta "/" para cambiar sin animación;
            # las pantallas internas se apilan encima y se deslizan como en Android.
            base = self._vista(PADRE.get(self.pagina, self.pagina), "/")
        # La vista "/" se reutiliza (solo cambia su contenido): si se reemplazara, Android
        # cerraría los diálogos abiertos, como la pregunta de ánimo al entrar.
        if self._base is None:
            self._base = base
        else:
            self._base.controls = base.controls
            self._base.appbar, self._base.navigation_bar = base.appbar, base.navigation_bar
        vistas = [self._base]
        if self.rol is not None and self.pagina in PADRE:
            vistas.append(self._vista(self.pagina, f"/{self.pagina}"))
        self.page.views.clear()
        self.page.views.extend(vistas)
        self.page.update()

    def _vista(self, pagina, ruta):
        secciones = SECCIONES_MEDICO if self.rol == "medico" else SECCIONES_PACIENTE
        seccion = PADRE.get(pagina, pagina)
        if pagina in TITULO_INTERNO:
            barra_sup = ft.AppBar(title=ft.Text(TITULO_INTERNO[pagina]), bgcolor=ft.Colors.WHITE)
        else:
            nombre = ("Panel clínico", self.paciente) if self.rol == "medico" else \
                ("Mi tratamiento", self.nombre or f"Folio {self.paciente}")
            barra_sup = ft.AppBar(
                title=ft.Column([ui.texto(nombre[0], 18, ui.TEAL_OSCURO, negrita=True),
                                 ui.sub(nombre[1], 12)], spacing=0),
                bgcolor=ft.Colors.WHITE, automatically_imply_leading=False,
                actions=[ft.TextButton("Salir", icon=ft.Icons.LOGOUT,
                                       on_click=lambda: self.salir())])
        claves = list(secciones)
        navegacion = ft.NavigationBar(
            selected_index=claves.index(seccion), bgcolor=ft.Colors.WHITE,
            destinations=[ft.NavigationBarDestination(icon=ico, selected_icon=ico_sel, label=et)
                          for et, ico, ico_sel in secciones.values()],
            on_change=lambda e: self.ir(claves[e.control.selected_index]))

        controles = PAGINAS[pagina](self)
        if self.mostrar_apoyo:
            controles.insert(0, encuestas.aviso_apoyo(self))
        cuerpo = ft.ListView(controles, spacing=12, padding=16, expand=True,
                             auto_scroll=pagina == "p_asistente")
        return ft.View(route=ruta, controls=[cuerpo], appbar=barra_sup,
                       navigation_bar=navegacion, bgcolor=ui.FONDO, padding=0)

    # ------------------------------------------------------------- ejemplo
    def cargar_ejemplo(self):
        """Paciente de ejemplo (Josefina); sus respuestas no se guardan en datos/."""
        self.rol, self.paciente, self.nombre = "paciente", "DEMO-001", "Josefina"
        self.demo, self.ingreso = True, 12000
        ejemplo = [
            ins.calcular_motivacion([4, 4, 5, 3, 4]),
            ins.calcular_salud_mental([1, 1, 0, 1, 0, 0, 1, 0, 0], [1, 1, 1, 0, 0, 1, 0]),
            ins.calcular_olvido(2),
            ins.calcular_habitos([15, 20, 15, 20, 8]),
            ins.calcular_efectos([2, 0, 0, 0, 2], interfiere_rutina=False),
            ins.calcular_apoyo([4, 3, 4, 4]),
            ins.calcular_seguimiento(10, 8),
            ins.calcular_carga(12000, 2400),
            ins.calcular_socioeconomico([15, 20, 20, 10, 15]),
        ]
        self.resultados = {r.codigo: r for r in ejemplo}
        self.entrar_paciente()

    def entrar_con_folio(self, folio):
        """Recupera de la base de datos lo que el paciente ya contestó en este dispositivo."""
        self.rol, self.paciente = "paciente", folio
        self.resultados = bd.ultimos_resultados(folio)
        self.animo = bd.animo_de_hoy(folio)
        self.entrar_paciente()

    def entrar_paciente(self):
        """Abre Inicio y, encima, la pregunta de cómo se siente hoy si aún no la contesta."""
        self.ir("p_inicio")
        if self.animo is None:
            self.despues(lambda: paciente.encuesta_animo(self))


def pagina_entrada(app):
    folio = ft.TextField(label="Folio de paciente", hint_text="Ej. MTZ-0423",
                         helper="Usa el folio que te dio tu clínica, no tu nombre.",
                         bgcolor=ft.Colors.WHITE, border_radius=12)
    acepta = ft.Checkbox(label="He leído y acepto participar")

    def entrar_paciente():
        if not folio.value.strip():
            app.avisar("Escribe tu folio de paciente.", error=True)
        elif not acepta.value:
            app.avisar("Necesitamos tu consentimiento para continuar.", error=True)
        else:
            app.entrar_con_folio(folio.value.strip())

    def entrar_medico():
        app.rol, app.paciente = "medico", "Dra. López"
        app.ir("m_panel")
        app.despues(lambda: medico.aviso_alertas(app))

    formulario_paciente = ft.Column([
        folio,
        ui.sub("Tus respuestas son confidenciales y solo las verá tu equipo de salud. Se usan "
               "para generar recomendaciones de acompañamiento; no sustituyen la valoración de "
               "tu médico. Puedes dejar de contestar en cualquier momento."),
        acepta,
        ui.boton("Entrar", lambda: entrar_paciente(), ft.Icons.LOGIN, principal=True),
        ui.boton("Entrar con un paciente de ejemplo", lambda: app.cargar_ejemplo(),
                 ft.Icons.PERSON),
    ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    formulario_medico = ft.Column([
        ui.tarjeta(ui.sub("Consulta la adherencia de tus pacientes, sus alertas y el modelo FCM.")),
        ui.boton("Entrar al panel clínico", lambda: entrar_medico(),
                 ft.Icons.MEDICAL_SERVICES, principal=True),
    ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, visible=False)

    def cambiar_perfil(e):
        es_medico = e.control.selected[0] == "medico"
        formulario_medico.visible, formulario_paciente.visible = es_medico, not es_medico
        app.page.update()

    perfil = ft.SegmentedButton(
        segments=[ft.Segment("paciente", label="Soy paciente", icon=ft.Icons.PERSON),
                  ft.Segment("medico", label="Soy personal de salud",
                             icon=ft.Icons.MEDICAL_SERVICES)],
        selected=["paciente"], show_selected_icon=False, on_change=cambiar_perfil)

    encabezado = ui.hero([
        ft.Text("💊", size=42, text_align=ft.TextAlign.CENTER),
        ui.texto("Adherencia terapéutica", 24, ft.Colors.WHITE, negrita=True,
                 text_align=ft.TextAlign.CENTER),
        ui.texto("Acompañamiento para seguir tu tratamiento", 14, "#d9f3f1",
                 text_align=ft.TextAlign.CENTER),
    ])
    encabezado.content.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    return ft.SafeArea(ft.ListView([
        encabezado, ui.sub("¿Cómo quieres entrar?"), perfil, formulario_paciente,
        formulario_medico,
    ], spacing=14, padding=16), expand=True)
