from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import datetime
import sqlite3 # <-- NUEVO: Importamos el motor de base de datos

app = FastAPI(title="API de Gestión de Obras SaaS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- NUEVO: PREPARAMOS LA BASE DE DATOS ---
def iniciar_base_datos():
    conexion = sqlite3.connect("data/obras.db")
    cursor = conexion.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reportes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            obra_id TEXT,
            capataz TEXT,
            texto_original TEXT,
            hitos_traducidos TEXT,
            riesgo_critico BOOLEAN
        )
    ''')
    conexion.commit()
    conexion.close()

iniciar_base_datos()

# --- NUESTRO MOTOR (Sin cambios) ---
class ConstructionReportEngine:
    JARGON_MAP = {
        "echar el cemento": "Vertido de hormigón estructural",
        "pegar ladrillos": "Levantamiento de mampostería",
        "hacer el hoyo": "Excavación de fundaciones/zanjas",
        "fierros": "Enfierradura de refuerzo"
    }

    def process(self, raw_data: str) -> dict:
        raw_data = raw_data.lower()
        is_critical = "accidente" in raw_data
        
        texto_traducido = raw_data
        for colloquial, technical in self.JARGON_MAP.items():
            texto_traducido = texto_traducido.replace(colloquial, technical)

        return {
            "fecha": datetime.date.today().strftime("%Y-%m-%d"),
            "riesgo_critico": is_critical,
            "hitos_del_dia": texto_traducido
        }

class TranscripcionEntrada(BaseModel):
    nombre_capataz: str
    obra_id: str
    texto: str

# --- NUEVO: GUARDAR EN LA BASE DE DATOS ---
@app.post("/procesar-reporte")
def procesar_reporte(datos: TranscripcionEntrada):
    engine = ConstructionReportEngine()
    resultado = engine.process(datos.texto)
    
    conexion = sqlite3.connect("data/obras.db")
    cursor = conexion.cursor()
    cursor.execute('''
        INSERT INTO reportes (fecha, obra_id, capataz, texto_original, hitos_traducidos, riesgo_critico)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (resultado["fecha"], datos.obra_id, datos.nombre_capataz, datos.texto, resultado["hitos_del_dia"], resultado["riesgo_critico"]))
    conexion.commit()
    conexion.close()
    
    return {"mensaje": "Guardado exitoso", "datos": resultado}

# --- NUEVO: LEER EL HISTORIAL ---
@app.get("/historial")
def obtener_historial():
    conexion = sqlite3.connect("data/obras.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT fecha, obra_id, capataz, hitos_traducidos, riesgo_critico FROM reportes ORDER BY id DESC")
    filas = cursor.fetchall()
    conexion.close()

    lista_historial = []
    for fila in filas:
        lista_historial.append({
            "fecha": fila[0],
            "obra": fila[1],
            "capataz": fila[2],
            "hitos": fila[3],
            "riesgo": bool(fila[4])
        })
        
    return lista_historial
# --- NUEVO: RUTA PRINCIPAL (ENTREGA EL HTML) ---
@app.get("/")
def mostrar_dashboard():
    # Le decimos a Python que devuelva tu archivo HTML
    return FileResponse("src/ui/dashboard.html")