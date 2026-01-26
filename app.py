from flask import Flask, render_template, request, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from groq import Groq
from openai import OpenAI
import replicate
import os
import time
import random
import uuid
from datetime import date, datetime
from dotenv import load_dotenv

# =========================
# 🔧 LOAD ENV FIRST
# =========================
load_dotenv()

# =========================
# 🚀 APP INIT
# =========================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# ✅ CONFIG MUST COME BEFORE db = SQLAlchemy
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "sqlite:///haste.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# =========================
# 🔌 EXTENSIONS
# =========================
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = None  # no redirects for APIs

# =========================
# 🔐 CONFIG
# =========================
OWNER_SECRET_PHRASE = os.getenv("OWNER_SECRET_PHRASE")
UPI_ID = os.getenv("UPI_ID", "haste@upi")

# =========================
# 🧠 API CLIENTS
# =========================
groq_client = Groq(api_key=os.getenv("YOUR_GROQ_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("YOUR_OpenAI_API_KEY"))
replicate_client = replicate.Client(
    api_token=os.getenv("REPLICATE_API_TOKEN")
)

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

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.String(100), unique=True)
    user_id = db.Column(db.Integer)
    plan = db.Column(db.String(20))
    amount = db.Column(db.Integer)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# =========================
# 🧮 USAGE
# =========================
def get_usage():
    today = str(date.today())
    session.setdefault("usage", {"date": today, "messages": 0, "videos": 0})

    if session["usage"]["date"] != today:
        session["usage"] = {"date": today, "messages": 0, "videos": 0}

    return session["usage"]

# =========================
# 🌐 ROUTES
# =========================
@app.route("/")
def index():
    return render_template("index.html")

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
# 💳 CREATE FAKE UPI PAYMENT
# -------------------------
@app.route("/create-upi-payment", methods=["POST"])
def create_upi_payment():
    plan = request.json.get("plan")
    if plan not in PLANS or plan == "free":
        return jsonify(error="Invalid plan"), 400

    payment_id = str(uuid.uuid4())

    db.session.add(Payment(
        payment_id=payment_id,
        user_id=current_user.id,
        plan=plan,
        amount=PLANS[plan]["price"]
    ))
    db.session.commit()

    return jsonify(
        payment_id=payment_id,
        upi_id=UPI_ID,
        amount=PLANS[plan]["price"],
        note=f"HASTE-{plan.upper()}-{payment_id[:6]}"
    )

@app.route("/confirm-upi-payment", methods=["POST"])
def confirm_upi_payment():
    payment = Payment.query.filter_by(
        payment_id=request.json.get("payment_id")
    ).first()

    if not payment:
        return jsonify(error="Invalid payment"), 400

    payment.status = "success"
    user = User.query.get(payment.user_id)
    user.plan = payment.plan
    db.session.commit()

    return jsonify(success=True)

# -------------------------
# 💬 CHAT
# -------------------------
@app.route("/chat", methods=["POST"])
def chat():
    if not current_user.is_authenticated:
        return jsonify(reply="❌ Please login"), 401

    msg = request.json.get("message", "").strip()
    if not msg:
        return jsonify(reply="Say something.")

    # OWNER MODE
    if msg == OWNER_SECRET_PHRASE:
        session["owner"] = True
        current_user.plan = "mind"
        db.session.commit()
        return jsonify(reply="🛡 Owner mode enabled.")

    db.session.add(VisitLog(ip=request.remote_addr, message=msg))
    db.session.commit()

    plan = "mind" if session.get("owner") else current_user.plan
    rules = PLANS[plan]
    usage = get_usage()

    if usage["messages"] >= rules["messages"]:
        return jsonify(reply="🚫 Daily limit reached"), 403

    usage["messages"] += 1
    session["usage"] = usage

    min_d, max_d = rules["delay"]
    if max_d > 0:
        time.sleep(random.randint(min_d, max_d))

    upgrade_note = "" if plan == "mind" else "\n\n⚡ Upgrade to get faster answers"

    completion = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": msg}],
        max_tokens=400
    )

    return jsonify(reply=completion.choices[0].message.content + upgrade_note)

# -------------------------
# 👑 OWNER DASHBOARD
# -------------------------
@app.route("/owner")
def owner():
    if not session.get("owner"):
        return "Forbidden", 403

    logs = VisitLog.query.order_by(VisitLog.timestamp.desc()).all()
    return jsonify([
        {"ip": l.ip, "message": l.message, "time": l.timestamp.isoformat()}
        for l in logs
    ])

# =========================
# ▶️ RUN (LOCAL ONLY)
# =========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
