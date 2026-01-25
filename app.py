from flask import Flask, render_template, request, jsonify, session
from groq import Groq
from openai import OpenAI
import replicate
import time
import re
import os
from datetime import date

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

# =========================
# 🔑 API CLIENTS
# =========================
groq_client = Groq(api_key=os.getenv("YOUR_GROQ_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("YOUR_OpenAI_API_KEY"))
replicate_client = replicate.Client(
    api_token=os.getenv("REPLICATE_API_TOKEN")
)

# =========================
# 👤 TEMP USERS (V1)
# =========================
USERS = {
    "test@student.com": {
        "password": "1234",
        "name": "Student"
    }
}

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

    # Reset if new day
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
    return render_template("index.html")

# -------------------------
# 🔐 LOGIN
# -------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if email in USERS and USERS[email]["password"] == password:
        session.clear()
        session["user_id"] = email
        session["user_name"] = USERS[email]["name"]
        session["memory"] = []
        session["video_usage"] = {
            "date": str(date.today()),
            "count": 0
        }
        return jsonify({"success": True})

    return jsonify({"success": False}), 401

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

# -------------------------
# 🎥 VIDEO GENERATION (LUMA)
# -------------------------
@app.route("/generate-video", methods=["POST"])
def generate_video():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    if not can_generate_video():
        return jsonify({
            "error": "Daily video limit reached (1/day)."
        }), 403

    prompt = request.json.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "Prompt required"}), 400

    try:
        output = replicate_client.run(
            "luma/reframe-video",
            input={
                "prompt": prompt
            }
        )

        return jsonify({
            "type": "video",
            "url": output
        })

    except Exception as e:
        print("Luma video error:", e)
        return jsonify({"error": "Video generation failed"}), 500

# -------------------------
# 💬 CHAT
# -------------------------
@app.route("/chat", methods=["POST"])
def chat():
    if "user_id" not in session:
        return jsonify({"reply": "Please log in to continue."}), 401

    user_input = request.json.get("message", "").strip()
    if not user_input:
        return jsonify({"reply": "Say something."})

    # Detect video intent
    if user_input.lower().startswith("generate video"):
        prompt = user_input.replace("generate video", "").strip()
        return jsonify({
            "reply": "🎥 Generating video… (limit: 1 per day)",
            "video_prompt": prompt
        })

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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
