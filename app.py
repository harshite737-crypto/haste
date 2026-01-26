from flask import Flask, render_template, request, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from groq import Groq
from openai import OpenAI
import replicate
import os
import re
import random
import time
from datetime import date, datetime
from dotenv import load_dotenv

# =========================
# 🔧 LOAD ENV
# =========================
load_dotenv()

# =========================
# 🚀 APP INIT
# =========================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///haste.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# =========================
# 🔌 EXTENSIONS
# =========================
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = None

# =========================
# 🔑 API CLIENTS
# =========================
groq_client = Groq(api_key=os.getenv("YOUR_GROQ_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("YOUR_OpenAI_API_KEY"))
replicate_client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))

# =========================
# 👤 OWNER SECRET
# =========================
OWNER_SECRET_PHRASE = os.getenv("OWNER_SECRET_PHRASE")  # enables owner mode

# =========================
# 📊 PLANS
# =========================
PLANS = {
    "free":  {"price": 0,   "messages": 50,  "videos": 1,  "delay": (10, 20)},
    "sound": {"price": 10,  "messages": 100, "videos": 2,  "delay": (5, 10)},
    "light": {"price": 50,  "messages": 150, "videos": 10, "delay": (2, 3)},
    "mind":  {"price": 100, "messages": float("inf"), "videos": float("inf"), "delay": (0, 0)}
}

# =========================
# 👤 MODELS
# =========================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(150))
    plan = db.Column(db.String(20), default="free")

class VisitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(100))
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# =========================
# 🧠 MEMORY
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
# 🧮 USAGE (MESSAGES/VIDEOS)
# =========================
def get_usage():
    today = str(date.today())
    if "usage" not in session:
        session["usage"] = {"date": today, "messages": 0, "videos": 0}
    usage = session["usage"]
    if usage["date"] != today:
        usage["date"] = today
        usage["messages"] = 0
        usage["videos"] = 0
    return usage

def can_generate_video(plan):
    if session.get("owner"):
        return True
    usage = get_usage()
    if usage["videos"] >= PLANS[plan]["videos"]:
        return False
    usage["videos"] += 1
    session["usage"] = usage
    return True

def increment_message(plan):
    if session.get("owner"):
        return True
    usage = get_usage()
    usage["messages"] += 1
    session["usage"] = usage
    return usage["messages"] <= PLANS[plan]["messages"]

# =========================
# 🌐 ROUTES
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
# CHAT
# -------------------------
@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json.get("message", "").strip()
    if not msg:
        return jsonify(reply="Say something.")

    # -------------------------
    # OWNER MODE (WORKS EVEN WITHOUT LOGIN)
    # -------------------------
    if msg == OWNER_SECRET_PHRASE:
        session["owner"] = True
        return jsonify(reply="🛡 Owner mode enabled. Everything is free now.")

    # -------------------------
    # Determine plan
    # -------------------------
    if session.get("owner"):
        plan = "mind"
    elif current_user.is_authenticated:
        plan = current_user.plan
    else:
        plan = "free"

    # -------------------------
    # Detect video intent
    # -------------------------
    if msg.lower().startswith("generate video"):
        prompt = msg.replace("generate video", "").strip()
        if not can_generate_video(plan):
            return jsonify({"reply": f"🚫 Daily video limit reached ({PLANS[plan]['videos']}/day)"})
        try:
            output = replicate_client.run(
                "luma/reframe-video",
                input={"prompt": prompt}
            )
            # Some outputs return list
            if isinstance(output, list):
                output = output[-1]
            return jsonify({
                "reply": "🎥 Video generated!",
                "video_url": output
            })
        except Exception as e:
            print("Video generation error:", e)
            return jsonify({"reply": "⚠️ Video generation failed"})

    # -------------------------
    # Increment message usage
    # -------------------------
    if not increment_message(plan):
        return jsonify(reply=f"🚫 Daily message limit reached ({PLANS[plan]['messages']}/day)")

    # -------------------------
    # Save memory
    # -------------------------
    if is_important(msg):
        mem = get_memory()
        mem.append(msg)
        session["memory"] = mem

    # -------------------------
    # System prompt
    # -------------------------
    system_prompt = (
        "You are Haste, a fast, precise AI assistant.\n"
        f"{memory_context()}"
    )

    # -------------------------
    # Delay based on plan
    # -------------------------
    min_d, max_d = PLANS[plan]["delay"]
    if max_d > 0:
        time.sleep(random.randint(min_d, max_d))

    # -------------------------
    # Generate AI reply
    # -------------------------
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

    upgrade_note = "" if plan == "mind" else "\n\n⚡ Upgrade to get faster answers"
    return jsonify(reply=reply + upgrade_note)

# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
