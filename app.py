import io
import os
import re
from flask import Flask, jsonify, render_template_string, request, send_file
from google import genai
from google.genai import types
from gtts import gTTS

app = Flask(__name__)

# Initialize the official Google GenAI client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Future Shorts AI – Cinema Studio</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0b0f19; color: #f8fafc; margin: 0; padding: 30px; display: flex; flex-direction: column; align-items: center; }
        .container { width: 100%; max-width: 650px; background: #111827; padding: 25px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.4); border: 1px solid #1f2937; }
        h1 { color: #38bdf8; text-align: center; margin-bottom: 20px; font-size: 1.6rem; }
        label { display: block; margin-top: 15px; margin-bottom: 6px; font-weight: 600; color: #94a3b8; font-size: 0.9rem; }
        textarea, select { width: 100%; padding: 12px; border: 1px solid #374151; border-radius: 6px; background: #0b0f19; color: #fff; font-size: 0.95rem; box-sizing: border-box; }
        textarea { height: 90px; resize: vertical; }
        .cost-box { margin-top: 15px; background: #0b0f19; padding: 12px; border-radius: 6px; border: 1px solid #374151; font-size: 0.9rem; color: #cbd5e1; }
        .cost-box span { font-weight: bold; color: #38bdf8; font-size: 1.1rem; }
        button { background-color: #0284c7; color: white; border: none; padding: 14px 20px; width: 100%; font-size: 1rem; font-weight: bold; border-radius: 6px; cursor: pointer; transition: background 0.2s; margin-top: 15px; }
        button:hover { background-color: #0369a1; }
        #loading { display: none; text-align: center; margin-top: 15px; color: #38bdf8; font-style: italic; }
        .result-box { margin-top: 20px; background: #0b0f19; padding: 20px; border-radius: 6px; border: 1px solid #374151; white-space: pre-wrap; line-height: 1.6; color: #e2e8f0; max-height: 400px; overflow-y: auto; }
        .audio-box { margin-top: 20px; background: #0b0f19; padding: 15px; border-radius: 8px; border: 1px solid #0284c7; text-align: center; }
        audio { width: 100%; margin-top: 10px; }
        .error-box { margin-top: 15px; background: #7f1d1d; color: #fca5a5; padding: 12px; border-radius: 6px; border: 1px solid #991b1b; font-size: 0.85rem; word-break: break-all; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 Future Shorts AI – Cinema Studio</h1>
        
        <label for="script">Custom Narration Script (Optional)</label>
        <textarea id="script" placeholder="Narrator script here..."></textarea>

        <label for="duration">Video Length Target</label>
        <select id="duration">
            <option value="5 seconds">5 seconds (1 scene test)</option>
            <option value="10 seconds" selected>10 seconds (2 scenes test)</option>
            <option value="15 seconds">15 seconds</option>
            <option value="20 seconds">20 seconds</option>
            <option value="30 seconds">30 seconds</option>
            <option value="60 seconds">60 seconds (Short)</option>
            <option value="8-10 minutes">8-10 minutes (Long-form)</option>
        </select>

        <label for="aspectRatio">Video Format</label>
        <select id="aspectRatio">
            <option value="Portrait 9:16">Portrait 9:16 – TikTok / Shorts / Reels</option>
            <option value="Landscape 16:9">Landscape 16:9 – YouTube</option>
        </select>

        <div class="cost-box">
            Estimated generation cost<br>
            <span>$0.10</span> <span style="font-size:0.8rem; color:#64748b; font-weight:normal;">(free FAL API estimate / $0.05 per clip)</span>
        </div>

        <button onclick="generateVideoContent()">✨ Direct & Generate Documentary Video</button>
        <div id="loading">Synthesizing script & voiceover with Gemini Flash...</div>
        
        <div id="errorBox" class="error-box" style="display:none;"></div>

        <div id="audioPlayerContainer" class="audio-box" style="display:none;">
            <h3 style="color:#38bdf8; margin:0 0 10px 0; font-size: 1rem;">🎙️ Voiceover Audio Preview</h3>
            <audio id="audioPlayer" controls></audio>
        </div>

        <div id="result" class="result-box" style="display:none;"></div>
    </div>

    <script>
        async function generateVideoContent() {
            const customScript = document.getElementById('script').value;
            const duration = document.getElementById('duration').value;
            const aspectRatio = document.getElementById('aspectRatio').value;
            const loading = document.getElementById('loading');
            const resultBox = document.getElementById('result');
            const errorBox = document.getElementById('errorBox');
            const audioContainer = document.getElementById('audioPlayerContainer');
            const audioPlayer = document.getElementById('audioPlayer');
            
            loading.style.display = 'block';
            resultBox.style.display = 'none';
            errorBox.style.display = 'none';
            audioContainer.style.display = 'none';

            try {
                const response = await fetch('/generate-video', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ customScript, duration, aspectRatio })
                });
                const data = await response.json();
                loading.style.display = 'none';

                if (data.success) {
                    resultBox.style.display = 'block';
                    resultBox.innerText = data.script;

                    if (data.narration_text) {
                        const audioUrl = '/generate-audio?text=' + encodeURIComponent(data.narration_text);
                        audioPlayer.src = audioUrl;
                        audioContainer.style.display = 'block';
                    }
                } else {
                    errorBox.style.display = 'block';
                    errorBox.innerText = "Error: " + data.error;
                }
            } catch (err) {
                loading.style.display = 'none';
                errorBox.style.display = 'block';
                errorBox.innerText = 'Network Error: ' + err.message;
            }
        }
    </script>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def home():
  return render_template_string(HTML_TEMPLATE)


@app.route("/generate-video", methods=["POST"])
def generate_video():
  try:
    data = request.get_json() or {}
    custom_script = data.get("customScript", "").strip()
    duration = data.get("duration", "10 seconds")
    aspect_ratio = data.get("aspectRatio", "Portrait 9:16")

    if custom_script:
      prompt = f"""
            Enhance and format this custom narrator script for a cinematic documentary ({duration}, {aspect_ratio}):
            "{custom_script}"
            Provide structured scene breakdowns and clean voiceover text.
            """
    else:
      prompt = f"""
            You are an elite Hollywood documentary writer. Create a compelling documentary script and visual scene breakdown.
            Target Duration: {duration}
            Format: {aspect_ratio}
            """

    # Using the fully supported current model to eliminate 404 errors
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt,
    )

    script_text = response.text

    # Extract clean narration text for the voiceover generator
    clean_narration = re.sub(r"\*\*.*?\*\*", "", script_text)
    clean_narration = re.sub(r"\[.*?\]", "", clean_narration)

    return jsonify({
        "success": True,
        "script": script_text,
        "narration_text": clean_narration[:1000],
    })

  except Exception as e:
    return jsonify({"success": False, "error": str(e)}), 500


@app.route("/generate-audio", methods=["GET"])
def generate_audio():
  text = request.args.get("text", "Welcome to Future Shorts AI.")
  try:
    tts = gTTS(text=text, lang="en")
    audio_fp = io.BytesIO()
    tts.write_to_fp(audio_fp)
    audio_fp.seek(0)
    return send_file(
        audio_fp,
        mimetype="audio/mpeg",
        as_attachment=False,
        download_name="voiceover.mp3",
    )
  except Exception as e:
    return str(e), 500


if __name__ == "__main__":
  app.run(debug=True)

