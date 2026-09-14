from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
from google import genai

app = Flask(__name__)
app.secret_key = "ucss_transparency_professional_secret_2026"

USERS_FILE = "ucss_flask_users.json"
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({"admin": "admin123"}, f)

DOCS_DIR = "documentos"
if not os.path.exists(DOCS_DIR):
    os.makedirs(DOCS_DIR)

# Obtener la API key de las variables de entorno de Render
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "AQ.Ab8RN6KPZmKZVK3pGRYzINsgwMyjMobfUxjAbPEOD1GpOmpHRQ") 

# Inicializar el cliente oficial de Google GenAI
client = genai.Client(api_key=GOOGLE_API_KEY)

@app.route("/")
def index_route():
    if "user" in session:
        return redirect(url_for("chat"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        if username in users and users[username] == password:
            session["user"] = username
            return redirect(url_for("chat"))
        else:
            error = "Usuario o contraseña incorrectos."
    return render_template("login.html", error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    success = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            error = "Por favor completa todos los campos."
        else:
            with open(USERS_FILE, "r") as f:
                users = json.load(f)
            if username in users:
                error = "El nombre de usuario ya está registrado."
            else:
                users[username] = password
                with open(USERS_FILE, "w") as f:
                    json.dump(users, f)
                success = "¡Registro exitoso! Ya puedes iniciar sesión."
    return render_template("register.html", error=error, success=success)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/chat")
def chat():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("chat.html", username=session["user"])

@app.route("/api/ask", methods=["POST"])
def ask():
    if "user" not in session:
        return jsonify({"error": "No autorizado"}), 401
    
    data = request.get_json()
    query = data.get("query", "").strip()
    
    if not query:
        return jsonify({"response": "Por favor ingresa una consulta válida."})

    # Leer los documentos institucionales solo al momento de la consulta (Evita saturar la RAM al iniciar)
    documentos_texto = ""
    try:
        if os.path.exists(DOCS_DIR):
            for nombre_archivo in os.listdir(DOCS_DIR):
                ruta_archivo = os.path.join(DOCS_DIR, nombre_archivo)
                if os.path.isfile(ruta_archivo) and nombre_archivo.endswith(".txt"):
                    with open(ruta_archivo, "r", encoding="utf-8", errors="ignore") as f:
                        documentos_texto += f"\n--- [{nombre_archivo}] ---\n" + f.read()[:5000]
    except Exception as e:
        print(f"Error leyendo documentos: {e}")
    
    system_instruction = """
    Eres el Asistente Ejecutivo e Inteligente de Transparencia de la UCSS (Universidad Católica Sedes Sapientiae). 
    Tu objetivo es ser proactivo, formal, analítico y basarte estrictamente en los documentos institucionales provistos.
    - Si el usuario pregunta por carreras, mallas, normativas o procesos institucionales, entrégale la información con precisión.
    - Sé proactivo: Termina siempre sugiriendo una acción adicional de valor.
    - Cuando menciones el portal oficial, incluye el enlace: [Portal de Transparencia UCSS](https://www.ucss.edu.pe/nosotros/transparencia).
    """

    prompt_final = f"""
    {system_instruction}

    Contexto institucional:
    {documentos_texto if documentos_texto else "No hay documentos cargados aún, responde con conocimiento general de la UCSS."}

    Pregunta del usuario: {query}
    """

    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt_final,
        )
        return jsonify({"response": response.text})

    except Exception as e:
        print(f"Error procesando la consulta con Gemini: {e}")
        return jsonify({
            "response": "Disculpa, en este momento tengo problemas para procesar la información. Intenta nuevamente en unos segundos."
        })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)