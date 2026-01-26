from flask import Flask, request, jsonify, render_template
import replicate
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

replicate_client = replicate.Client(
    api_token=os.getenv("REPLICATE_API_TOKEN")
)

@app.route("/")
def index():
    return render_template("index.html")

# -------------------------
# CHAT (NO LOGIN, NO LIMIT)
# -------------------------
@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json.get("message", "").strip()

    if not msg:
        return jsonify({"reply": "Say something 🙂"})

    if msg.lower().startswith("generate video"):
        prompt = msg.replace("generate video", "").strip()
        return jsonify({
            "reply": "🎥 Generating video…",
            "video_prompt": prompt
        })

    return jsonify({
        "reply": f"Haste: You said → {msg}"
    })

# -------------------------
# VIDEO GENERATION (VEO-3-FAST)
# -------------------------
@app.route("/generate-video", methods=["POST"])
def generate_video():
    prompt = request.json.get("prompt", "").strip()

    if not prompt:
        return jsonify({"error": "Prompt required"}), 400

    try:
        output = replicate.run(
            "google/veo-3-fast",
            input={
                "prompt": prompt,
                "duration": 4,
                "aspect_ratio": "16:9"
            }
        )

        video_url = output[0]

        return jsonify({
            "success": True,
            "video_url": video_url
        })

    except Exception as e:
        print("Video generation error:", e)
        return jsonify({"error": "Video generation failed"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
