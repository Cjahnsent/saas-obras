from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from twilio.twiml.messaging_response import MessagingResponse # <-- Nueva herramienta de WhatsApp
import datetime
import sqlite3

app = FastAPI(title="API de Gestión de Obras SaaS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. BASE DE DATOS ---
def iniciar_base_datos():
    conexion = sqlite3.connect("data/obras.db")
    cursor = conexion.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS reportes (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, fecha TEXT, obra_id TEXT, capataz TEXT, hitos_traducidos TEXT, riesgo_critico BOOLEAN, FOREIGN KEY(usuario_id) REFERENCES usuarios(id))''')
    conexion.commit()
    conexion.close()

iniciar_base_datos()

def crear_usuario_maestro():
    conexion = sqlite3.connect("data/obras.db")
    cursor = conexion.cursor()
    try:
        cursor.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", ("admin", "1234"))
        conexion.commit()
    except:
        pass
    conexion.close()

crear_usuario_maestro()

# --- 2. MOTOR DE PROCESAMIENTO ---
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

# --- 3. MODELOS ---
class LoginDatos(BaseModel):
    username: str
    password: str

class TranscripcionEntrada(BaseModel):
    usuario_id: int
    nombre_capataz: str
    obra_id: str
    texto: str

# --- 4. RUTAS WEB NORMALES ---
@app.post("/login")
def login(datos: LoginDatos):
    conexion = sqlite3.connect("data/obras.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE username = ? AND password = ?", (datos.username, datos.password))
    usuario = cursor.fetchone()
    conexion.close()
    if usuario: return {"success": True, "usuario_id": usuario[0], "mensaje": "Bienvenido"}
    else: return {"success": False, "mensaje": "Usuario o clave incorrecta"}

@app.post("/procesar-reporte")
def procesar_reporte(datos: TranscripcionEntrada):
    engine = ConstructionReportEngine()
    resultado = engine.process(datos.texto)
    conexion = sqlite3.connect("data/obras.db")
    cursor = conexion.cursor()
    cursor.execute('''INSERT INTO reportes (usuario_id, fecha, obra_id, capataz, hitos_traducidos, riesgo_critico) VALUES (?, ?, ?, ?, ?, ?)''', (datos.usuario_id, resultado["fecha"], datos.obra_id, datos.nombre_capataz, resultado["hitos_del_dia"], resultado["riesgo_critico"]))
    conexion.commit()
    conexion.close()
    return {"mensaje": "Guardado exitoso", "datos": resultado}

@app.get("/historial/{usuario_id}")
def obtener_historial(usuario_id: int):
    conexion = sqlite3.connect("data/obras.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT fecha, obra_id, capataz, hitos_traducidos, riesgo_critico FROM reportes WHERE usuario_id = ? ORDER BY id DESC", (usuario_id,))
    filas = cursor.fetchall()
    conexion.close()
    return [{"fecha": f[0], "obra": f[1], "capataz": f[2], "hitos": f[3], "riesgo": bool(f[4])} for f in filas]

@app.get("/")
def mostrar_dashboard():
    return FileResponse("src/ui/dashboard.html")

# --- 5. ¡LA NUEVA RUTA MÁGICA DE WHATSAPP! ---
@app.post("/whatsapp")
async def recibir_whatsapp(request: Request):
    # 1. Twilio nos envía los datos del celular
    form_data = await request.form()
    mensaje_capataz = form_data.get('Body', '')
    numero_celular = form_data.get('From', '')

    # 2. Procesamos el texto con nuestra Inteligencia de la Construcción
    engine = ConstructionReportEngine()
    resultado = engine.process(mensaje_capataz)

    # 3. Lo guardamos en la base de datos automáticamente (Asignado al usuario Admin ID: 1)
    conexion = sqlite3.connect("data/obras.db")
    cursor = conexion.cursor()
    cursor.execute('''
        INSERT INTO reportes (usuario_id, fecha, obra_id, capataz, hitos_traducidos, riesgo_critico)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (1, resultado["fecha"], "Reporte Móvil", numero_celular, resultado["hitos_del_dia"], resultado["riesgo_critico"]))
    conexion.commit()
    conexion.close()

    # 4. Preparamos el mensaje de respuesta para el celular
    alerta = "🔴 PELIGRO / INCIDENTE REGISTRADO" if resultado["riesgo_critico"] else "✅ TODO EN ORDEN"
    respuesta_texto = f"SaaS Obras:\n\nTu reporte ha sido guardado en la bóveda de gerencia.\nEstado: {alerta}\nTraducción: {resultado['hitos_del_dia']}"

    # 5. Le respondemos a Twilio en su idioma (XML/TwiML)
    respuesta_twilio = MessagingResponse()
    respuesta_twilio.message(respuesta_texto)

    return Response(content=str(respuesta_twilio), media_type="application/xml")