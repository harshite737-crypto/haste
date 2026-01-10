from flask import Flask, render_template, request, jsonify, session
from groq import Groq
from openai import OpenAI
import os, re

app = Flask(__name__)
app.secret_key = "haste-secret-key"

groq_client = Groq(api_key=os.getenv("YOUR_GROQ_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("YOUR_OPENAI_API_KEY"))

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

def memory_context():
    memory = session.get("memory", [])
    if not memory:
        return ""
    return "Important user info:\n" + "\n".join(f"- {m}" for m in memory)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_input = data.get("message", "")
    student_mode = data.get("studentMode", False)  # OFF by default

    if "memory" not in session:
        session["memory"] = []

    if is_important(user_input):
        session["memory"].append(user_input)
        session.modified = True

    tone = (
        "Use simple Hinglish, student-friendly language."
        if student_mode else
        "Use clear, professional English."
    )

    system_prompt = (
        "You are Haste, a helpful AI assistant.\n"
        f"{tone}\n"
        f"{memory_context()}"
    )

    try:
        res = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            max_tokens=700,
            temperature=0.5
        )
        return jsonify({"reply": res.choices[0].message.content})
    except:
        res = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            max_tokens=700,
            temperature=0.5
        )
        return jsonify({"reply": res.choices[0].message.content})

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

if __name__ == "__main__":
    app.run(debug=True)
