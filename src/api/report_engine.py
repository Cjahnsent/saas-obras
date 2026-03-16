import datetime
import os

class ConstructionReportEngine:
    JARGON_MAP = {
        "echar el cemento": "Vertido de hormigón estructural",
        "pegar ladrillos": "Levantamiento de mampostería",
        "hacer el hoyo": "Excavación de fundaciones/zanjas",
        "fierros": "Enfierradura de refuerzo",
        "la mezcla": "Mortero de pega/relleno"
    }

    def __init__(self, raw_data: str, foreman_name: str = "No reportado"):
        self.raw_data = raw_data.lower()
        self.foreman = foreman_name
        self.report_date = datetime.date.today().strftime("%Y-%m-%d")

    def translate_jargon(self, text: str) -> str:
        for colloquial, technical in self.JARGON_MAP.items():
            text = text.replace(colloquial, technical)
        return text

    def generate_html(self, output_path: str):
        # Lógica de detección de riesgos
        is_critical = "accidente" in self.raw_data or "paralización" in self.raw_data
        risk_color = "text-red-600 font-bold" if is_critical else "text-green-600 font-semibold"
        risk_tag = "[🔴 CRÍTICO] - Atención inmediata requerida" if is_critical else "Sin incidentes reportados"
        
        # Lógica de clima
        clima = "Soleado" if "sol" in self.raw_data else ("Lluvia" if "lluvia" in self.raw_data else "No reportado explícitamente")

        # Traducción de la jerga
        texto_traducido = self.translate_jargon(self.raw_data)

        # Plantilla HTML con los datos insertados
        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte Dinámico - {self.report_date}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 font-sans p-8">
    <main class="max-w-4xl mx-auto bg-white shadow-xl rounded-lg overflow-hidden border border-slate-200">
        <header class="bg-blue-900 text-white p-6">
            <h1 class="text-2xl font-bold tracking-tight uppercase">Reporte Diario Automático</h1>
            <p class="text-blue-200 mt-1">Fecha: {self.report_date} | Capataz: {self.foreman}</p>
        </header>
        
        <section class="p-8 prose prose-slate max-w-none">
            <h2 class="text-xl font-bold border-b-2 border-slate-200 pb-2 mt-6">1. CONDICIONES CLIMÁTICAS</h2>
            <p>{clima}</p>

            <h2 class="text-xl font-bold border-b-2 border-slate-200 pb-2 mt-6">2. AVANCE DE PARTIDAS (HITOS DEL DÍA)</h2>
            <ul class="list-disc pl-5">
                <li class="capitalize">{texto_traducido}</li>
            </ul>

            <h2 class="text-xl font-bold border-b-2 border-slate-200 pb-2 mt-6">3. INCIDENTES Y SEGURIDAD</h2>
            <p class="{risk_color}">{risk_tag}</p>
        </section>
    </main>
</body>
</html>"""

        # Escribir el contenido en el archivo HTML
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(html_content)
        
        print(f"✅ ¡Exito! El dashboard ha sido actualizado en: {output_path}")

# --- PUNTO DE ENTRADA ---
import os

if __name__ == "__main__":
    ruta_entrada = "data/transcripcion.txt"
    ruta_salida = "src/ui/dashboard.html"
    
    # 1. Verificamos si el archivo de texto existe
    if os.path.exists(ruta_entrada):
        print(f"Buscando nuevos reportes en: {ruta_entrada}...")
        
        # 2. Leemos el contenido del archivo
        with open(ruta_entrada, "r", encoding="utf-8") as file:
            texto_capataz = file.read()
            
        print("Procesando la información...")
        
        # 3. Generamos el reporte con los datos leídos
        engine = ConstructionReportEngine(texto_capataz, "Pedro (Capataz Sector C)")
        engine.generate_html(ruta_salida)
        
    else:
        print(f"❌ Error: No se encontró el archivo de transcripción en {ruta_entrada}")
        print("Asegúrate de haber creado el archivo transcripcion.txt dentro de la carpeta data.")