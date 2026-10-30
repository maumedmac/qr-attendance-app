import os
import datetime
from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import qrcode
from fastapi.responses import StreamingResponse
import psycopg2

app = FastAPI(title="Control de Asistencia QR", debug=False)

# ==========================================
# CONFIGURACIÓN DE POSTGRESQL (RENDER)
# ==========================================
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://qr_attendance_db_rih4_user:lgg4UlNdjSSpGnaLmkniCgKHMtBnH8xk@dpg-dbi5psifngtc73cck770-a.oregon-postgres.render.com/qr_attendance_db_rih4"
)

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

# Crear carpetas necesarias automáticamente
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Inicializar Base de Datos PostgreSQL
def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS asistentes (
                codigo VARCHAR(255) PRIMARY KEY,
                nombre TEXT NOT NULL,
                ingresado INTEGER DEFAULT 0,
                timestamp TEXT
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("¡Base de datos inicializada correctamente en PostgreSQL!")
    except Exception as e:
        print(f"Error al inicializar la base de datos: {e}")

init_db()

# ==========================================
# API ENDPOINTS
# ==========================================

@app.post("/api/consultar")
def consultar_asistencia(codigo: str = Form(...)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, ingresado FROM asistentes WHERE codigo = %s", (codigo,))
    asistente = cursor.fetchone()
    cursor.close()
    conn.close()

    if not asistente:
        return JSONResponse(status_code=404, content={"status": "not_found", "message": "El código no existe"})
    
    nombre, ingresado = asistente
    return {"status": "success", "nombre": nombre, "ya_ingreso": bool(ingresado)}

@app.post("/api/registrar")
def registrar_asistencia(codigo: str = Form(...)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, ingresado FROM asistentes WHERE codigo = %s", (codigo,))
    asistente = cursor.fetchone()

    if not asistente:
        cursor.close()
        conn.close()
        return JSONResponse(status_code=404, content={"status": "not_found", "message": "El código no existe"})

    nombre, ingresado = asistente

    if ingresado:
        cursor.close()
        conn.close()
        return JSONResponse(status_code=400, content={"status": "duplicate", "message": "¡La invitación ya fue usada!"})

    hora_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE asistentes SET ingresado = 1, timestamp = %s WHERE codigo = %s", (hora_actual, codigo))
    conn.commit()
    cursor.close()
    conn.close()
    
    hora_corta = datetime.datetime.now().strftime("%H:%M:%S")
    return {"status": "registered", "nombre": nombre, "hora": hora_corta, "message": f"Ingreso registrado para {nombre}"}

@app.get("/api/dashboard-data")
def dashboard_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, nombre, ingresado, timestamp FROM asistentes")
    filas = cursor.fetchall()
    cursor.close()
    conn.close()

    asistentes_lista = []
    for fila in filas:
        codigo, nombre, ingresado, timestamp = fila
        asistentes_lista.append({
            "codigo": codigo,
            "name": nombre,
            "status": "Entró" if ingresado == 1 else "Pendiente",
            "timestamp": timestamp if timestamp else "-"
        })

    return {"asistentes": asistentes_lista}
# Endpoint para generar el QR visualmente desde el navegador
@app.get("/api/generar-qr/{codigo}")
def generar_qr(codigo: str):
    img = qrcode.make(codigo)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

# ==========================================
# VISTAS WEB
# ==========================================
# Endpoint para registrar un nuevo asistente desde la interfaz web de creación
@app.post("/api/crear-asistente")
def crear_asistente(codigo: str = Form(...), nombre: str = Form(...)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO asistentes (codigo, nombre, ingresado) 
            VALUES (%s, %s, 0)
            ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre;
        """, (codigo, nombre))
        conn.commit()
        cursor.close()
        conn.close()
        return {"status": "success", "message": f"Asistente {nombre} registrado correctamente"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    
@app.get("/", response_class=HTMLResponse)
def leer_raiz(request: Request):
    try:
        template = templates.get_template("scanner.html")
        return HTMLResponse(content=template.render({"request": request}))
    except Exception:
        with open("templates/scanner.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())

@app.get("/dashboard", response_class=HTMLResponse)
def ver_dashboard(request: Request):
    try:
        template = templates.get_template("admin.html")
        return HTMLResponse(content=template.render({"request": request}))
    except Exception:
        with open("templates/admin.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
        @app.get("/generador", response_class=HTMLResponse)
def ver_generador(request: Request):
    try:
        template = templates.get_template("generador.html")
        return HTMLResponse(content=template.render({"request": request}))
    except Exception:
        with open("templates/generador.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())

# Archivos estáticos básicos para PWA
@app.get("/favicon.ico")
def favicon():
    return JSONResponse(status_code=204, content={})