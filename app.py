import os
from flask import Flask, jsonify, render_template_string, request
from google import genai
from google.genai import types

app = Flask(__name__)

# Initialize the official Google GenAI client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Your complete user interface built right in (no separate HTML file needed!)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Future Shorts Documentary Generator</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 40px; display: flex; flex-direction: column; align-items: center; }
        .container { width: 100%; max-width: 700px; background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
        h1 { color: #38bdf8; text-align: center; margin-bottom: 20px; font-size: 1.8rem; }
        label { display: block; margin-bottom: 8px; font-weight: 600; color: #cbd5e1; }
        input[type="text"] { width: 100%; padding: 12px; margin-bottom: 20px; border: 1px solid #475569; border-radius: 6px; background: #0f172a; color: #fff; font-size: 1rem; box-sizing: border-box; }
        button { background-color: #0284c7; color: white; border: none; padding: 12px 20px; width: 100%; font-size: 1rem; font-weight: bold; border-radius: 6px; cursor: pointer; transition: background 0.2s; }
        button:hover { background-color: #0369a1; }
        #loading { display: none; text-align: center; margin-top: 15px; color: #38bdf8; font-style: italic; }
        .result-box { margin-top: 25px; background: #0f172a; padding: 20px; border-radius: 6px; border: 1px solid #334155; white-space: pre-wrap; line-height: 1.6; color: #e2e8f0; max-height: 400px; overflow-y: auto; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 Future Shorts Documentary Generator</h1>
        <label for="topic">Enter Documentary Topic:</label>
        <input type="text" id="topic" placeholder="e.g., The Mystery of Deep Sea Ecosystems">
        <button onclick="generateScript()">Generate Script</button>
        <div id="loading">Generating your cinematic script with Gemini Flash...</div>
        <div id="result" class="result-box" style="display:none;"></div>
    </div>

    <script>
        async function generateScript() {
            const topic = document.getElementById('topic').value;
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
                    body: JSON.stringify({ topic: topic })
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
    topic = data.get("topic", "The Evolution of Cinematic Technology")

    prompt = f"""
        You are an expert AI documentary director and scriptwriter.
        Write a cinematic, highly engaging short-form documentary script about: "{topic}".
        
        Structure your response clearly with:
        1. **Title**: Catchy documentary title
        2. **Hook**: Introduction that grabs the viewer's attention instantly
        3. **Scene-by-Scene Breakdown**: Narration paired with vivid visual/cinematic cues
        4. **Outro**: A memorable closing statement
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

