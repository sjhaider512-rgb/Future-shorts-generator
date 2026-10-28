import os
from flask import Flask, jsonify, render_template_string, request
from google import genai
from google.genai import types

app = Flask(__name__)

# Initialize the official Google GenAI client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Future Shorts Documentary Generator</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 30px; display: flex; flex-direction: column; align-items: center; }
        .container { width: 100%; max-width: 750px; background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
        h1 { color: #38bdf8; text-align: center; margin-bottom: 20px; font-size: 1.8rem; }
        label { display: block; margin-top: 15px; margin-bottom: 6px; font-weight: 600; color: #cbd5e1; }
        input[type="text"], select { width: 100%; padding: 12px; margin-bottom: 10px; border: 1px solid #475569; border-radius: 6px; background: #0f172a; color: #fff; font-size: 1rem; box-sizing: border-box; }
        button { background-color: #0284c7; color: white; border: none; padding: 14px 20px; width: 100%; font-size: 1rem; font-weight: bold; border-radius: 6px; cursor: pointer; transition: background 0.2s; margin-top: 20px; }
        button:hover { background-color: #0369a1; }
        #loading { display: none; text-align: center; margin-top: 15px; color: #38bdf8; font-style: italic; }
        .result-box { margin-top: 25px; background: #0f172a; padding: 20px; border-radius: 6px; border: 1px solid #334155; white-space: pre-wrap; line-height: 1.6; color: #e2e8f0; max-height: 450px; overflow-y: auto; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 Future Shorts Documentary Generator</h1>
        
        <label for="topic">Documentary Topic:</label>
        <input type="text" id="topic" placeholder="e.g., Rise of Quantum Computing">

        <label for="duration">Target Duration:</label>
        <select id="duration">
            <option value="15 seconds">Short (15 Seconds)</option>
            <option value="30 seconds">Short (30 Seconds)</option>
            <option value="60 seconds">Short (60 Seconds)</option>
            <option value="8-10 minutes">Long-form Documentary (8-10 Minutes)</option>
        </select>

        <label for="aspectRatio">Aspect Ratio Layout:</label>
        <select id="aspectRatio">
            <option value="9:16 (Vertical / Shorts / Reels)">9:16 (Vertical)</option>
            <option value="16:9 (Horizontal / YouTube)">16:9 (Horizontal)</option>
        </select>

        <button onclick="generateScript()">Generate Cinematic Script & Plan</button>
        <div id="loading">Crafting your custom script with Gemini Flash...</div>
        <div id="result" class="result-box" style="display:none;"></div>
    </div>

    <script>
        async function generateScript() {
            const topic = document.getElementById('topic').value;
            const duration = document.getElementById('duration').value;
            const aspectRatio = document.getElementById('aspectRatio').value;
            const loading = document.getElementById('loading');
            const resultBox = document.getElementById('result');
            
            if (!topic) {
                alert('Please enter a topic!');
                return;
            }

            loading.style.display = 'block';
            resultBox.style.display = 'none';

            try {
                const response = await fetch('/generate-script', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ topic, duration, aspectRatio })
                });
                const data = await response.json();
                loading.style.display = 'none';
                resultBox.style.display = 'block';

                if (data.success) {
                    resultBox.innerText = data.script;
                } else {
                    resultBox.innerText = 'Error: ' + data.error;
                }
            } catch (err) {
                loading.style.display = 'none';
                resultBox.style.display = 'block';
                resultBox.innerText = 'Network Error: ' + err.message;
            }
        }
    </script>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def home():
  return render_template_string(HTML_TEMPLATE)


@app.route("/generate-script", methods=["POST"])
def generate_script():
  try:
    data = request.get_json() or {}
    topic = data.get("topic", "The Future of Space Travel")
    duration = data.get("duration", "60 seconds")
    aspect_ratio = data.get("aspectRatio", "9:16")

    prompt = f"""
        You are an elite Hollywood documentary writer and video director.
        Create a precise production script and visual blueprint for a documentary about: "{topic}".
        
        Parameters:
        - Target Duration: {duration}
        - Aspect Ratio Format: {aspect_ratio}
        
        Please structure your output with:
        1. **Title & Concept Overview**
        2. **Pacing & Timing Breakdown** (timed sections matching the {duration} length)
        3. **Scene-by-Scene Script & Visual Cues** (tailored for {aspect_ratio} framing)
        4. **Voiceover & Audio Guidance**
        """

    # Generate content using Gemini Flash
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt,
    )

    return jsonify({"success": True, "script": response.text})

  except Exception as e:
    return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
  app.run(debug=True)

