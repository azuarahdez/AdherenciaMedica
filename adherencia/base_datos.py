"""Base de datos SQLite de la app: encuestas, ánimo, tomas, alertas y notas.

Un solo archivo (adherencia.db) en el dispositivo. En el celular (app de Flet) la carpeta de la
app es de solo lectura: se usa la carpeta de datos privada que Flet indica en
FLET_APP_STORAGE_DATA; en la computadora, datos/ junto al proyecto.
"""
import json
import os
import sqlite3
from contextlib import closing
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path

from adherencia.instrumentos import Resultado

_CARPETA = os.environ.get("FLET_APP_STORAGE_DATA")
ARCHIVO = (Path(_CARPETA) if _CARPETA else Path(__file__).resolve().parent.parent / "datos") \
    / "adherencia.db"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS encuestas (
    id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, paciente TEXT NOT NULL,
    codigo TEXT NOT NULL, instrumento TEXT NOT NULL, puntaje REAL, nivel TEXT,
    valor_fcm REAL, alertas TEXT, detalle TEXT, respuestas TEXT);
CREATE INDEX IF NOT EXISTS encuestas_por_paciente ON encuestas (paciente, codigo, fecha);
-- Una carita por paciente y día (índice de movil.paciente.ANIMOS: 0 = enojado … 4 = súper feliz)
CREATE TABLE IF NOT EXISTS animos (
    paciente TEXT NOT NULL, fecha TEXT NOT NULL, indice INTEGER NOT NULL,
    PRIMARY KEY (paciente, fecha));
CREATE TABLE IF NOT EXISTS tomas (
    paciente TEXT NOT NULL, fecha TEXT NOT NULL, hora TEXT NOT NULL, registrada TEXT NOT NULL,
    PRIMARY KEY (paciente, fecha, hora));
-- Síntomas que reporta el paciente y alertas de sus encuestas (ítem 9, efectos graves)
CREATE TABLE IF NOT EXISTS alertas (
    id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, paciente TEXT NOT NULL, nombre TEXT,
    nivel TEXT NOT NULL, texto TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notas (
    id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, paciente TEXT NOT NULL, texto TEXT NOT NULL);
-- Claves de alertas que el personal de salud marcó como atendidas
CREATE TABLE IF NOT EXISTS atendidas (clave TEXT PRIMARY KEY, fecha TEXT NOT NULL);
"""

_preparadas = set()  # archivos a los que ya se les aplicó el esquema


def _ahora():
    return datetime.now().isoformat(timespec="seconds")


def _conectar():
    ARCHIVO.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ARCHIVO)
    con.row_factory = sqlite3.Row
    if ARCHIVO not in _preparadas:
        con.executescript(ESQUEMA)
        _importar_jsonl(con)
        _preparadas.add(ARCHIVO)
    return con


def _ejecutar(sql, parametros=()):
    with closing(_conectar()) as con, con:
        return con.execute(sql, parametros).lastrowid


def _consultar(sql, parametros=()):
    with closing(_conectar()) as con:
        return con.execute(sql, parametros).fetchall()


def _importar_jsonl(con):
    """Las versiones anteriores guardaban las encuestas en respuestas.jsonl; se copian una vez."""
    anterior = ARCHIVO.with_name("respuestas.jsonl")
    if not anterior.exists() or con.execute("SELECT COUNT(*) FROM encuestas").fetchone()[0]:
        return
    with con:
        for linea in anterior.read_text(encoding="utf-8").splitlines():
            if linea.strip():
                r = json.loads(linea)
                con.execute(
                    "INSERT INTO encuestas (fecha, paciente, codigo, instrumento, puntaje, nivel, "
                    "valor_fcm, alertas, detalle, respuestas) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (r["fecha"], r["paciente"], r["codigo"], r["instrumento"], r["puntaje"],
                     r["nivel"], r["valor_fcm"], json.dumps(r.get("alertas", [])),
                     json.dumps(r.get("detalle", {})), json.dumps(r.get("respuestas"))))


# ------------------------------------------------------------------ encuestas
def guardar_encuesta(paciente, resultado, respuestas):
    """Guarda la encuesta; sus alertas (ítem 9 del PHQ-9, efectos graves) llegan al médico."""
    r = asdict(resultado)
    _ejecutar("INSERT INTO encuestas (fecha, paciente, codigo, instrumento, puntaje, nivel, "
              "valor_fcm, alertas, detalle, respuestas) VALUES (?,?,?,?,?,?,?,?,?,?)",
              (_ahora(), paciente, r["codigo"], r["instrumento"], r["puntaje"], r["nivel"],
               r["valor_fcm"], json.dumps(r["alertas"], ensure_ascii=False),
               json.dumps(r["detalle"], ensure_ascii=False),
               json.dumps(respuestas, ensure_ascii=False)))
    for texto in resultado.alertas:
        agregar_alerta(paciente, None, "alta", texto)


def ultimos_resultados(paciente):
    """{código: Resultado} con la respuesta más reciente de cada encuesta del paciente."""
    filas = _consultar("SELECT * FROM encuestas WHERE paciente = ? ORDER BY fecha, id",
                       (paciente,))
    return {f["codigo"]: Resultado(f["instrumento"], f["codigo"], f["puntaje"], f["nivel"],
                                   f["valor_fcm"], json.loads(f["alertas"] or "[]"),
                                   json.loads(f["detalle"] or "{}"))
            for f in filas}


def pacientes_registrados():
    """[(folio, encuestas contestadas, fecha de la última)] de quienes usan la app aquí."""
    return [(f["paciente"], f["n"], f["ultima"]) for f in _consultar(
        "SELECT paciente, COUNT(DISTINCT codigo) AS n, MAX(fecha) AS ultima FROM encuestas "
        "GROUP BY paciente ORDER BY ultima DESC")]


# ------------------------------------------------------------------ ánimo y tomas
def guardar_animo(paciente, indice):
    _ejecutar("INSERT OR REPLACE INTO animos (paciente, fecha, indice) VALUES (?,?,?)",
              (paciente, date.today().isoformat(), indice))


def animo_de_hoy(paciente):
    filas = _consultar("SELECT indice FROM animos WHERE paciente = ? AND fecha = ?",
                       (paciente, date.today().isoformat()))
    return filas[0]["indice"] if filas else None


def registrar_toma(paciente, hora):
    _ejecutar("INSERT OR IGNORE INTO tomas (paciente, fecha, hora, registrada) VALUES (?,?,?,?)",
              (paciente, date.today().isoformat(), hora, _ahora()))


def tomas_de_hoy(paciente):
    return {f["hora"] for f in _consultar("SELECT hora FROM tomas WHERE paciente = ? AND fecha = ?",
                                          (paciente, date.today().isoformat()))}


def tomas_ultimos_dias(paciente, dias=7):
    """[(fecha, tomas registradas)] de los últimos `dias` días completos (hoy no cuenta)."""
    hoy = date.today()
    fechas = [(hoy - timedelta(days=n)).isoformat() for n in range(dias, 0, -1)]
    cuenta = {f["fecha"]: f["n"] for f in _consultar(
        "SELECT fecha, COUNT(*) AS n FROM tomas WHERE paciente = ? AND fecha >= ? GROUP BY fecha",
        (paciente, fechas[0]))}
    return [(f, cuenta.get(f, 0)) for f in fechas]


# ------------------------------------------------------------------ alertas y notas
def agregar_alerta(paciente, nombre, nivel, texto):
    _ejecutar("INSERT INTO alertas (fecha, paciente, nombre, nivel, texto) VALUES (?,?,?,?,?)",
              (_ahora(), paciente, nombre, nivel, texto))


def alertas():
    """Alertas guardadas, la más reciente primero, con la clave para marcarlas atendidas."""
    return [{"clave": f"A{f['id']}", "id": f["paciente"],
             "nombre": f["nombre"] or f"Folio {f['paciente']}", "nivel": f["nivel"],
             "texto": f["texto"], "cuando": cuando(f["fecha"])}
            for f in _consultar("SELECT * FROM alertas ORDER BY fecha DESC, id DESC")]


def marcar_atendida(clave):
    _ejecutar("INSERT OR IGNORE INTO atendidas (clave, fecha) VALUES (?,?)", (clave, _ahora()))


def atendidas():
    return {f["clave"] for f in _consultar("SELECT clave FROM atendidas")}


def agregar_nota(paciente, texto):
    _ejecutar("INSERT INTO notas (fecha, paciente, texto) VALUES (?,?,?)",
              (_ahora(), paciente, texto))


def notas(paciente):
    """[(fecha corta, nota)], la más reciente primero."""
    return [(cuando(f["fecha"]), f["texto"]) for f in _consultar(
        "SELECT fecha, texto FROM notas WHERE paciente = ? ORDER BY fecha DESC, id DESC",
        (paciente,))]


def cuando(fecha_iso):
    """'hoy 17:35' o '28/10 09:12'."""
    f = datetime.fromisoformat(fecha_iso)
    return f"hoy {f:%H:%M}" if f.date() == date.today() else f"{f:%d/%m %H:%M}"
