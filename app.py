from flask import Flask, render_template, request, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from groq import Groq
from openai import OpenAI
import replicate
import os
import re
import time
import uuid
import requests
from datetime import datetime
from dotenv import load_dotenv

# =========================
# LOAD ENV
# =========================
load_dotenv()

# =========================
# APP INIT
# =========================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///haste.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# =========================
# EXTENSIONS
# =========================
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = None

# =========================
# API CLIENTS
# =========================
groq_client = Groq(api_key=os.getenv("YOUR_GROQ_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("YOUR_OpenAI_API_KEY"))
replicate_client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))

# =========================
# HUGGING FACE (NEW)
# =========================
HF_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
HF_MODEL_URL = "https://api-inference.huggingface.co/models/HiDream-ai/HiDream-l1"

HF_HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}"
}

# =========================
# OWNER SECRET
# =========================
OWNER_SECRET_PHRASE = os.getenv("OWNER_SECRET_PHRASE")

# =========================
# MODELS
# =========================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(150))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# =========================
# MEMORY
# =========================
IMPORTANT_PATTERNS = [
    r"my name is",
    r"remember",
    r"i like",
    r"i am",
    r"call me",
    r"my age is",
    r"i live in"
]

def is_important(text):
    return any(re.search(p, text.lower()) for p in IMPORTANT_PATTERNS)

def get_memory():
    if "memory" not in session:
        session["memory"] = []
    return session["memory"]

def memory_context():
    memory = get_memory()
    if not memory:
        return ""
    return "Important user info:\n" + "\n".join(f"- {m}" for m in memory)

# =========================
# ROUTES
# =========================
@app.route("/")
def index():
    return render_template("index.html")

# -------------------------
# LOGIN
# -------------------------
@app.route("/login", methods=["POST"])
def login():
    email = request.json.get("email")
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, username="User")
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return jsonify(success=True)

@app.route("/logout", methods=["POST"])
def logout():
    logout_user()
    session.clear()
    return jsonify(success=True)

# -------------------------
# CHAT + VIDEO + IMAGE
# -------------------------
@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json.get("message", "").strip()
    if not msg:
        return jsonify(reply="Say something.")

    # -------------------------
    # OWNER MODE
    # -------------------------
    if OWNER_SECRET_PHRASE and msg.lower() == OWNER_SECRET_PHRASE.lower():
        session["owner"] = True
        return jsonify(reply="🛡 Owner mode enabled.")

    # -------------------------
    # IMAGE GENERATION (NEW)
    # -------------------------
    if msg.lower().startswith("generate image"):
        prompt = msg.replace("generate image", "").strip()

        try:
            payload = {
                "inputs": prompt,
                "options": {"wait_for_model": True}
            }

            r = requests.post(
                HF_MODEL_URL,
                headers=HF_HEADERS,
                json=payload,
                timeout=180
            )

            if r.status_code != 200:
                return jsonify(reply="⚠️ Image generation failed.")

            filename = f"image_{uuid.uuid4().hex}.png"
            path = os.path.join("static", filename)

            with open(path, "wb") as f:
                f.write(r.content)

            return jsonify(
                reply="🖼️ Image generated!",
                image_url=f"/static/{filename}"
            )

        except Exception as e:
            print("Image generation error:", e)
            return jsonify(reply="⚠️ Image generation error.")

    # -------------------------
    # VIDEO GENERATION (UNCHANGED)
    # -------------------------
    if msg.lower().startswith("generate video"):
        prompt = msg.replace("generate video", "").strip()
        try:
            model = replicate.models.get("luma/reframe-video")
            version = model.versions.list()[0]
            output = replicate.run(
                version=version.id,
                input={"prompt": prompt}
            )
            video_url = output if isinstance(output, str) else output[-1]
            return jsonify(
                reply="🎥 Video generated!",
                video_url=video_url
            )
        except Exception as e:
            print("Video generation error:", e)
            return jsonify(reply="⚠️ Video generation failed.")

    # -------------------------
    # MEMORY
    # -------------------------
    if is_important(msg):
        mem = get_memory()
        mem.append(msg)
        session["memory"] = mem

    system_prompt = (
        "You are Haste, a fast, precise AI assistant.\n"
        f"{memory_context()}"
    )

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": msg}],
            temperature=0.5,
            max_tokens=400
        )
        reply = completion.choices[0].message.content
    except Exception:
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": msg}],
            temperature=0.5,
            max_tokens=400
        )
        reply = completion.choices[0].message.content

    return jsonify(reply=reply)

# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
