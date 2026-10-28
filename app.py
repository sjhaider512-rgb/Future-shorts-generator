import os
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types

app = Flask(__name__)

# Initialize the official Google GenAI client using the environment variable
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


@app.route("/", methods=["GET"])
def home():
  # Serves the main web interface template
  try:
    return render_template("index.html")
  except Exception:
    return (
        "<h1>Future Shorts Documentary Generator</h1><p>Server is live and"
        " ready!</p>"
    )


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

    # Generate content using the stable Gemini Flash model
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt,
    )

    return jsonify({"success": True, "script": response.text})

  except Exception as e:
    return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
  app.run(debug=True)

