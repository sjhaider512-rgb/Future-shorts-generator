import os
import fal_client
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Future Shorts Generator</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="font-family:Arial; max-width:700px; margin:40px auto; padding:20px;">
    <h1>🎬 Future Shorts Generator</h1>
    <p>Create an AI video from one prompt.</p>

    <form method="POST">
        <textarea name="prompt" rows="5"
        style="width:100%; padding:10px;"
        placeholder="Example: Futuristic London at night, flying cars above Tower Bridge, cinematic, vertical video"></textarea>
        <br><br>
        <button type="submit" style="padding:12px 25px;">
            Generate Video
        </button>
    </form>

    {% if video_url %}
        <h2>Your video</h2>
        <video width="100%" controls>
            <source src="{{ video_url }}" type="video/mp4">
        </video>
        <p><a href="{{ video_url }}" target="_blank">Open video</a></p>
    {% endif %}

    {% if error %}
        <p style="color:red;">{{ error }}</p>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    video_url = None
    error = None

    if request.method == "POST":
        prompt = request.form.get("prompt", "").strip()

        if not prompt:
            error = "Please enter a prompt."
        else:
            try:
                result = fal_client.subscribe(
                    "fal-ai/wan/v2.2-a14b/text-to-video",
                    arguments={
                        "prompt": prompt,
                    },
                    with_logs=True,
                )

                video = result.get("video", {})
                video_url = video.get("url")

                if not video_url:
                    error = "Video generated but no video URL was returned."

            except Exception as e:
                error = str(e)

    return render_template_string(
        HTML,
        video_url=video_url,
        error=error
    )

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
