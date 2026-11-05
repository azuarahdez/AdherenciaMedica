"""Datos SIMULADOS para las pantallas de demostración.

Nada de esto sale de pacientes reales. C28 se estima con la fórmula de etiquetas
(0.25·(C24+C25+C26+C27)), no con el motor FCM, que todavía no está conectado.
"""
import unicodedata

# Conceptos del mapa (project(1).xlsx)
CONCEPTOS = {
    1: "Conocimiento del tratamiento", 2: "Cuestionario de motivación y actitud", 3: "Olvido",
    4: "Hábitos y estilos de vida", 5: "PHQ-9", 6: "GAD-7", 7: "Efectos secundarios",
    8: "Motivación y actitud", 9: "Salud mental", 10: "Comunicación médico-paciente",
    11: "Registro e historial de citas", 12: "Duración del tratamiento",
    13: "Plan de tratamiento", 14: "Registro de síntomas", 15: "Registro del tratamiento",
    16: "Recordatorio digital", 17: "Pastillero inteligente", 18: "Calidad del registro",
    19: "Confirmación de toma", 20: "Comunicación con el paciente",
    21: "Organización del tratamiento", 22: "Apoyo familiar", 23: "Gestión familiar",
    24: "Factores del paciente", 25: "Factores médicos", 26: "Factores tecnológicos",
    27: "Factores familiares", 28: "Adherencia terapéutica",
}

# Concepto compuesto ← conceptos que lo alimentan
ESTRUCTURA = {
    8: [1, 2, 3, 4, 9], 9: [5, 6], 13: [10, 11, 12], 18: [14, 15], 19: [16, 17],
    23: [21, 22], 24: [7, 8], 25: [7, 13], 26: [18, 19], 27: [20, 23], 28: [24, 25, 26, 27],
}

# Entradas agrupadas por el factor final al que llegan
GRUPOS = {
    24: [1, 2, 3, 4, 5, 6, 7, 8, 9],
    25: [10, 11, 12, 13],
    26: [14, 15, 16, 17, 18, 19],
    27: [20, 21, 22, 23],
}

LIMITE_MALO, LIMITE_BUENO = 0.318, 0.6446


def estimar_c28(c24, c25, c26, c27):
    return 0.25 * (c24 + c25 + c26 + c27)


def etiqueta(c28):
    return "Malo" if c28 < LIMITE_MALO else "Regular" if c28 < LIMITE_BUENO else "Bueno"


RECOMENDACION = {
    24: "Reforzar educación sobre el tratamiento y motivación; revisar salud mental.",
    25: "Revisar el plan de tratamiento y la comunicación médico-paciente.",
    26: "Verificar el uso del pastillero y de los recordatorios digitales.",
    27: "Involucrar a la red familiar, solo con autorización del paciente.",
}

_DESVIOS = [0.08, -0.05, 0.12, -0.1, 0.03, -0.07, 0.1, -0.02, 0.05]


def _paciente(id_, nombre, edad, tratamiento, finales, semanas, alertas):
    c24, c25, c26, c27 = finales
    valores = {24: c24, 25: c25, 26: c26, 27: c27}
    for final, entradas in GRUPOS.items():
        for i, c in enumerate(entradas):
            valores[c] = round(max(0.05, min(0.95, valores[final] + _DESVIOS[i % 9])), 2)
    c28 = estimar_c28(*finales)
    return {"id": id_, "nombre": nombre, "edad": edad, "tratamiento": tratamiento,
            "valores": valores, "c28": c28, "etiqueta": etiqueta(c28),
            "semanas": semanas, "alertas": alertas}


PACIENTES = [
    _paciente("P1", "Ramón Aguilar", 67, "Hipertensión · Losartán 50 mg",
              (0.25, 0.35, 0.30, 0.20), [70, 62, 58, 55, 50, 46, 44, 40],
              [("alta", "Respuesta positiva en el ítem 9 del PHQ-9", "hace 2 h")]),
    _paciente("P2", "Josefina Ramírez", 54, "Diabetes tipo 2 e hipertensión · Metformina y Losartán",
              (0.70, 0.75, 0.65, 0.80), [72, 78, 81, 76, 85, 88, 83, 90], []),
    _paciente("P3", "Alicia Mendoza", 45, "Hipotiroidismo · Levotiroxina 100 µg",
              (0.80, 0.70, 0.85, 0.75), [88, 90, 92, 91, 94, 95, 93, 96], []),
    _paciente("P4", "Eduardo Cruz", 61, "Dislipidemia · Atorvastatina 20 mg",
              (0.50, 0.55, 0.45, 0.60), [75, 72, 70, 68, 71, 66, 64, 65],
              [("media", "Efectos secundarios graves reportados", "ayer")]),
    _paciente("P5", "Patricia Luna", 39, "Asma · Budesonida inhalada",
              (0.60, 0.50, 0.70, 0.40), [65, 70, 68, 72, 74, 70, 73, 75], []),
    _paciente("P6", "Jorge Hernández", 72, "Insuficiencia cardiaca · Enalapril 10 mg",
              (0.35, 0.45, 0.40, 0.30), [68, 64, 60, 62, 57, 55, 52, 50],
              [("media", "5 dosis olvidadas esta semana", "hoy")]),
]

# ------------------------------------------------------------ vista del paciente
# El paciente de ejemplo de la vista móvil es Josefina Ramírez (P2).
DOSIS_HOY = [
    ("08:00", "Losartán 50 mg", "tomada", "Pastillero · 08:04"),
    ("14:00", "Metformina 850 mg", "pendiente", "Recordatorio a las 14:00"),
    ("21:00", "Losartán 50 mg", "programada", ""),
]

SEMANAS_PACIENTE = PACIENTES[1]["semanas"]

# Ánimo registrado lunes a miércoles (índices de movil.paciente.ANIMOS: 0 = enojado …
# 4 = súper feliz). El jueves (hoy) lo elige el paciente al tocar el saludo.
ANIMO_SEMANA = [3, 2, 3]

DIAS = ["L", "M", "M", "J", "V", "S", "D"]
HORARIOS = ["Mañana", "Tarde", "Noche"]
# Una fila por horario, una letra por día (L..D); la demo supone que hoy es jueves.
# t = tomada, o = olvidada, p = pendiente, f = futura
PASTILLERO = [
    "ttttfff",
    "tttpfff",
    "ottffff",  # la noche de hoy (21:00) todavía no toca
]

# Tomas registradas (de 3) de jueves a domingo de la semana pasada; con lunes a miércoles
# de PASTILLERO suman 19 de 21 en los últimos 7 días, como dice Inicio.
TOMAS_SEMANA_PASADA = [("Jue", 3), ("Vie", 3), ("Sáb", 2), ("Dom", 3)]
DIAS_CORTOS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def adherencia_ultimos_dias():
    """(día, % de dosis tomadas) de los últimos 7 días completos; hoy aún no cuenta."""
    dias = [(d, round(100 * n / len(HORARIOS))) for d, n in TOMAS_SEMANA_PASADA]
    for i, dia in enumerate(DIAS_CORTOS):
        estados = [fila[i] for fila in PASTILLERO]
        if all(e in "to" for e in estados):
            dias.append((dia, round(100 * estados.count("t") / len(estados))))
    return dias[-7:]


# Días en que faltan tomas cuando se reparte el porcentaje semanal de un paciente (orden fijo,
# no aleatorio, para que su gráfica sea siempre la misma).
_ORDEN_FALTAS = [5, 2, 6, 0, 3, 1, 4]


def tomas_ultimos_dias(p):
    """(día, % de dosis tomadas) de los últimos 7 días de un paciente del panel.

    Josefina (P2) usa el registro del pastillero; a los demás se les reparten las dosis
    de su última semana (`semanas[-1]` % de 21) sobre los 7 días.
    """
    if p["id"] == "P2":
        return adherencia_ultimos_dias()
    por_dia = [len(HORARIOS)] * 7
    faltan = 21 - round(p["semanas"][-1] * 21 / 100)
    i = 0
    while faltan > 0:
        dia = _ORDEN_FALTAS[i % 7]
        if por_dia[dia]:
            por_dia[dia] -= 1
            faltan -= 1
        i += 1
    etiquetas = [d for d, _ in adherencia_ultimos_dias()]
    return [(d, round(100 * n / len(HORARIOS))) for d, n in zip(etiquetas, por_dia)]


def _normalizar(texto):
    sin_acentos = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin_acentos if unicodedata.category(c) != "Mn")


RESPUESTAS_RAPIDAS = ["Ya tomé mi medicamento", "Tengo un efecto secundario",
                      "¿Cuándo es mi próxima cita?", "Quiero contestar una encuesta"]

MENSAJE_CRISIS = (
    "Gracias por contármelo. No estás solo(a). **He avisado a tu equipo de salud** para que "
    "se comunique contigo. Si sientes que estás en peligro, llama ahora al **911** o a la "
    "**Línea de la Vida: 800 911 2000** (gratuita, 24 horas).")


def responder(mensaje, proxima_cita):
    """Respuestas predefinidas del asistente simulado (sin IA)."""
    t = _normalizar(mensaje)
    if any(p in t for p in ("morir", "muerto", "lastimar", "suicid", "matarme",
                            "no quiero vivir")):
        return MENSAJE_CRISIS
    if "tom" in t and ("ya" in t or "medic" in t or "pastilla" in t):
        return ("¡Muy bien! 💊 Registré tu toma de las **14:00**. Llevas **3 días seguidos** "
                "sin olvidar ninguna dosis.")
    if any(p in t for p in ("efecto", "nausea", "mareo", "dolor", "vomit", "sueno",
                            "somnolencia")):
        return ("Lamento que te sientas así. ¿Qué tan fuerte es, del 1 al 5? Puedes registrarlo "
                "en **📋 Encuestas → Efectos secundarios**. Recuerda no suspender ni cambiar "
                "tu medicamento sin hablar antes con tu médico.")
    if "cita" in t:
        return f"Tu próxima cita es el **{proxima_cita}** a las **10:30** en tu clínica. 📅"
    if "cuestionario" in t or "encuesta" in t:
        return "Ve a **📋 Encuestas**, abajo; ahí verás las que tienes pendientes."
    if any(p in t for p in ("hola", "buen")):
        return "¡Hola! 😊 ¿Cómo te has sentido hoy con tu tratamiento?"
    if "gracias" in t:
        return "¡Con gusto! Aquí estoy cuando me necesites."
    return ("Todavía estoy aprendiendo 😊. Prueba con una de las opciones de abajo.")
