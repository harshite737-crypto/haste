from flask import Flask, render_template, request, jsonify, make_response
from groq import Groq
from openai import OpenAI
import re
import uuid
import os

app = Flask(__name__)

groq_client = Groq(api_key=os.getenv("YOUR_GROQ_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("YOUR_OpenAI_API_KEY"))

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
    return any(re.search(p, text.lower()) for p in IMPORTANT_PATTERNS)

def memory_context(user_id):
    if user_id not in user_memory:
        return ""
    return "Important user info:\n" + "\n".join(f"- {m}" for m in user_memory[user_id])

def get_user_id():
    uid = request.cookies.get("haste_uid")
    if not uid:
        uid = str(uuid.uuid4())
    return uid

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_id = get_user_id()
    data = request.json
    user_input = data.get("message", "").strip()
    student_mode = data.get("student_mode", True)

    if not user_input:
        return jsonify({"reply": "Say something."})

    if is_important(user_input):
        user_memory.setdefault(user_id, []).append(user_input)

    if student_mode:
        system_prompt = (
            "You are Haste, a friendly AI tutor for students.\n"
            "Explain step-by-step.\n"
            "Use Hinglish only if helpful.\n"
            f"{memory_context(user_id)}"
        )
    else:
        system_prompt = (
            "You are Haste, a professional AI assistant.\n"
            "Reply in fluent English.\n"
            f"{memory_context(user_id)}"
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

        reply = completion.choices[0].message.content
        response = make_response(jsonify({"reply": reply}))
        response.set_cookie("haste_uid", user_id, max_age=31536000)
        return response

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

        reply = completion.choices[0].message.content
        response = make_response(jsonify({"reply": reply}))
        response.set_cookie("haste_uid", user_id, max_age=31536000)
        return response

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
