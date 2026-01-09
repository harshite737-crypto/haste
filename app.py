from flask import Flask, render_template, request, jsonify, make_response
from groq import Groq
from openai import OpenAI
import re
import uuid
import os

app = Flask(__name__)

# =========================
# 🔑 API KEYS (ENV VARS)
# =========================
groq_client = Groq(api_key=os.getenv("YOUR_GROQ_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("YOUR_OpenAI_API_KEY"))

# =========================
# 🧠 PER-USER MEMORY (SAFE)
# =========================
user_memory = {}

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

def memory_context(user_id):
    if user_id not in user_memory or not user_memory[user_id]:
        return ""
    return (
        "Important user info:\n"
        + "\n".join(f"- {m}" for m in user_memory[user_id])
    )

# =========================
# 👤 USER IDENTIFICATION
# =========================
def get_user_id():
    user_id = request.cookies.get("haste_uid")
    if not user_id:
        user_id = str(uuid.uuid4())
    return user_id

# =========================
# 🌐 ROUTES
# =========================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_id = get_user_id()
    user_input = request.json.get("message", "").strip()

    if not user_input:
        return jsonify({"reply": "Say something."})

    # Store important memory PER USER
    if is_important(user_input):
        if user_id not in user_memory:
            user_memory[user_id] = []
        user_memory[user_id].append(user_input)

    # =========================
    # 🎓 STUDENT MODE PROMPT
    # =========================
    system_prompt = (
        "You are Haste, an AI tutor made especially for students.\n"
        "Explain concepts in simple language.\n"
        "Give step-by-step answers.\n"
        "Focus on exam-ready explanations.\n"
        "Use examples when helpful.\n"
        "If the question is academic, answer like a teacher.\n"
        "You may use simple Hinglish if it helps understanding.\n"
        f"{memory_context(user_id)}"
    )

    # -------------------------
    # 🚀 TRY GROQ FIRST
    # -------------------------
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

        reply = completion.choices[0].message.content

        response = make_response(jsonify({"reply": reply}))
        response.set_cookie("haste_uid", user_id, max_age=60 * 60 * 24 * 365)
        return response

    except Exception as groq_error:
        print("Groq failed:", groq_error)

    # -------------------------
    # 🔁 FALLBACK TO OPENAI
    # -------------------------
    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.5,
            max_tokens=400
        )

        reply = completion.choices[0].message.content

        response = make_response(jsonify({"reply": reply}))
        response.set_cookie("haste_uid", user_id, max_age=60 * 60 * 24 * 365)
        return response

    except Exception as openai_error:
        print("OpenAI failed:", openai_error)
        return jsonify({
            "reply": "Neural link failed. Both engines are unavailable."
        })

# =========================
# ▶️ RUN SERVER
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
