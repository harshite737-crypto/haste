from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from groq import Groq
from openai import OpenAI
import replicate
import os
import re
from datetime import date
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///haste.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# =========================
# 🔧 EXTENSIONS
# =========================
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login_page"  # redirect if not logged in

# =========================
# 👤 USER MODEL
# =========================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(150), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# =========================
# 🔑 API CLIENTS
# =========================
groq_client = Groq(api_key=os.getenv("YOUR_GROQ_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("YOUR_OpenAI_API_KEY"))
replicate_client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))

# =========================
# 🧠 MEMORY (PER USER)
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
    text = text.lower()
    return any(re.search(p, text) for p in IMPORTANT_PATTERNS)

def get_user_memory():
    if "memory" not in session:
        session["memory"] = []
    return session["memory"]

def memory_context():
    memory = get_user_memory()
    if not memory:
        return ""
    return "Important user info:\n" + "\n".join(f"- {m}" for m in memory)

# =========================
# 🎥 VIDEO LIMIT (1 / DAY)
# =========================
def can_generate_video():
    today = str(date.today())
    if "video_usage" not in session:
        session["video_usage"] = {"date": today, "count": 0}
    usage = session["video_usage"]
    if usage["date"] != today:
        usage["date"] = today
        usage["count"] = 0
    if usage["count"] >= 1:
        return False
    usage["count"] += 1
    session["video_usage"] = usage
    return True

# =========================
# 🌐 ROUTES
# =========================
@app.route("/")
def index():
    if current_user.is_authenticated:
        return render_template("index.html", username=current_user.username)
    return redirect(url_for("login_page"))

# -------------------------
# 🔐 LOGIN & REGISTER PAGES
# -------------------------
@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        data = request.json
        email = data.get("email")
        password = data.get("password")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            # initialize session memory & usage
            session["memory"] = []
            session["video_usage"] = {"date": str(date.today()), "count": 0}
            return jsonify({"success": True})
        return jsonify({"success": False}), 401
    return render_template("login.html")

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email")
    username = data.get("username")
    password = data.get("password")
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 400
    user = User(email=email, username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"success": True})

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    session.clear()
    return jsonify({"success": True})

# -------------------------
# 🎥 VIDEO GENERATION (LUMA)
# -------------------------
@app.route("/generate-video", methods=["POST"])
@login_required
def generate_video():
    if not can_generate_video():
        return jsonify({"error": "Daily video limit reached (1/day)."}), 403

    prompt = request.json.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "Prompt required"}), 400

    try:
        output = replicate_client.run(
            "luma/reframe-video",
            input={"prompt": prompt}
        )
        return jsonify({"type": "video", "url": output})
    except Exception as e:
        print("Luma video error:", e)
        return jsonify({"error": "Video generation failed"}), 500

# -------------------------
# 💬 CHAT
# -------------------------
@app.route("/chat", methods=["POST"])
@login_required
def chat():
    user_input = request.json.get("message", "").strip()
    if not user_input:
        return jsonify({"reply": "Say something."})

    # Detect video intent
    if user_input.lower().startswith("generate video"):
        prompt = user_input.replace("generate video", "").strip()
        return jsonify({"reply": "🎥 Generating video… (limit: 1 per day)", "video_prompt": prompt})

    # Save important memory
    if is_important(user_input):
        memory = get_user_memory()
        memory.append(user_input)
        session["memory"] = memory

    system_prompt = (
        "You are Haste, a fast, precise AI assistant.\n"
        "Respond clearly and concisely.\n"
        f"{memory_context()}"
    )

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.5,
            max_tokens=400
        )
        return jsonify({"reply": completion.choices[0].message.content})
    except Exception:
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.5,
            max_tokens=400
        )
        return jsonify({"reply": completion.choices[0].message.content})

# =========================
# ▶️ RUN SERVER
# =========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # create DB if not exists
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
