from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from twilio.twiml.messaging_response import MessagingResponse
import datetime
import sqlite3
import requests # <-- Nueva herramienta para hablar con AssemblyAI
import time     # <-- Nueva herramienta para esperar la transcripción

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

# --- 5. RUTA MÁGICA DE WHATSAPP (CON AUDIOS) ---
@app.post("/whatsapp")
async def recibir_whatsapp(request: Request):
    form_data = await request.form()
    numero_celular = form_data.get('From', '')
    num_media = int(form_data.get('NumMedia', 0)) # ¿Cuántos archivos adjuntos hay?
    mensaje_capataz = form_data.get('Body', '')

    # SI HAY UN AUDIO...
    if num_media > 0:
        audio_url = form_data.get('MediaUrl0')
        
        # --- ¡REEMPLAZA ESTO CON TU LLAVE DE ASSEMBLYAI! ---
        api_key_assembly = "919f589e55504d69ad3054f87465b938" 
        
        headers = {"authorization": api_key_assembly}
        
        # 1. Le pasamos el link del audio a la IA
        respuesta_ia = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            json={"audio_url": audio_url, "language_code": "es"},
            headers=headers
        ).json()
        
        transcript_id = respuesta_ia.get('id')

        # 2. Esperamos unos segundos a que termine de escuchar (Polling)
        if transcript_id:
            while True:
                estado = requests.get(f"https://api.assemblyai.com/v2/transcript/{transcript_id}", headers=headers).json()
                if estado['status'] == 'completed':
                    mensaje_capataz = estado['text'] # ¡El audio convertido a texto!
                    break
                elif estado['status'] == 'error':
                    mensaje_capataz = "Error: No se pudo transcribir el audio."
                    break
                time.sleep(2) # Espera 2 segundos y vuelve a preguntar

    # 3. Procesamos el texto (ya sea que vino escrito o transcrito del audio)
    engine = ConstructionReportEngine()
    resultado = engine.process(mensaje_capataz)

    # 4. Lo guardamos en la base de datos
    conexion = sqlite3.connect("data/obras.db")
    cursor = conexion.cursor()
    cursor.execute('''
        INSERT INTO reportes (usuario_id, fecha, obra_id, capataz, hitos_traducidos, riesgo_critico)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (1, resultado["fecha"], "Reporte Móvil", numero_celular, resultado["hitos_del_dia"], resultado["riesgo_critico"]))
    conexion.commit()
    conexion.close()

    # 5. Preparamos el mensaje de respuesta para WhatsApp
    alerta = "🔴 PELIGRO / INCIDENTE REGISTRADO" if resultado["riesgo_critico"] else "✅ TODO EN ORDEN"
    respuesta_texto = f"SaaS Obras:\n\nAudio/Texto procesado y guardado en la bóveda.\nEstado: {alerta}\nTraducción: {resultado['hitos_del_dia']}"

    # 6. Le respondemos a Twilio
    respuesta_twilio = MessagingResponse()
    respuesta_twilio.message(respuesta_texto)

    return Response(content=str(respuesta_twilio), media_type="application/xml")