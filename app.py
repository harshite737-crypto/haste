from flask import Flask, render_template, request, jsonify
from groq import Groq
from openai import OpenAI
import time
import re

app = Flask(__name__)

# =========================
# 🔑 API KEYS (ADD YOURS)
# =========================
import os

groq_client = Groq(api_key=os.getenv("YOUR_GROQ_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("YOUR_OpenAI_API_KEY"))


# =========================
# 🧠 MEMORY (IMPORTANT ONLY)
# =========================
memory = []

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

def memory_context():
    if not memory:
        return ""
    return "Important user info:\n" + "\n".join(f"- {m}" for m in memory)

# =========================
# 🌐 ROUTES
# =========================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "").strip()
    if not user_input:
        return jsonify({"reply": "Say something."})

    # Store important memory
    if is_important(user_input):
        memory.append(user_input)

    system_prompt = (
        "You are Haste, a fast, precise AI assistant.\n"
        "Respond clearly and concisely.\n"
        f"{memory_context()}"
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
        return jsonify({"reply": reply})

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
        return jsonify({"reply": reply})

    except Exception as openai_error:
        print("OpenAI failed:", openai_error)
        return jsonify({
            "reply": "Neural link failed. Both engines are unavailable."
        })

# =========================
# ▶️ RUN SERVER
# =========================
if __name__ == "__main__":
   import os

port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)

