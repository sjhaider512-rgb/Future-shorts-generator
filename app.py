import traceback
import fal_client
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

MODEL = "fal-ai/kandinsky5/text-to-video/distill"

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Future Shorts AI</title>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #0b0b14;
            color: white;
        }

        .container {
            max-width: 720px;
            margin: auto;
            padding: 28px 18px 60px;
        }

        .logo {
            font-size: 34px;
            font-weight: 800;
            margin-bottom: 5px;
        }

        .subtitle {
            color: #aaa;
            margin-bottom: 30px;
        }

        .card {
            background: #171724;
            border: 1px solid #29293a;
            border-radius: 20px;
            padding: 22px;
            margin-bottom: 20px;
        }

        textarea {
            width: 100%;
            min-height: 140px;
            resize: vertical;
            padding: 16px;
            border-radius: 14px;
            border: 1px solid #3a3a4c;
            background: #0f0f19;
            color: white;
            font-size: 16px;
            outline: none;
        }

        label {
            display: block;
            font-weight: bold;
            margin-top: 18px;
            margin-bottom: 8px;
        }

        select {
            width: 100%;
            padding: 13px;
            border-radius: 12px;
            background: #0f0f19;
            color: white;
            border: 1px solid #3a3a4c;
            font-size: 15px;
        }

        .price {
            margin-top: 20px;
            background: #101c17;
            border: 1px solid #234c38;
            padding: 14px;
            border-radius: 12px;
        }

        .price strong {
            font-size: 22px;
        }

        button {
            width: 100%;
            margin-top: 20px;
            padding: 16px;
            border: 0;
            border-radius: 14px;
            font-size: 17px;
            font-weight: bold;
            cursor: pointer;
            background: linear-gradient(90deg, #7c5cff, #b34cff);
            color: white;
        }

        button:hover {
            opacity: 0.92;
        }

        video {
            width: 100%;
            border-radius: 16px;
            margin-top: 12px;
            background: black;
        }

        .download {
            display: block;
            text-align: center;
            margin-top: 14px;
            padding: 13px;
            border-radius: 12px;
            text-decoration: none;
            color: white;
            background: #29293a;
        }

        .error {
            color: #ff7777;
            background: #2a1418;
            padding: 14px;
            border-radius: 12px;
            margin-top: 18px;
        }

        .badge {
            display: inline-block;
            padding: 6px 10px;
            background: #25253a;
            border-radius: 20px;
            font-size: 12px;
            margin-bottom: 14px;
            color: #c9c9dc;
        }

        .small {
            color: #8f8f9f;
            font-size: 13px;
            margin-top: 10px;
        }
    </style>
</head>

<body>

<div class="container">

    <div class="logo">🎬 Future Shorts AI</div>

    <div class="subtitle">
        Turn your idea into an AI video.
    </div>

    <div class="card">

        <span class="badge">⚡ Economy Model</span>

        <form method="POST">

            <label>Your video idea</label>

            <textarea
                name="prompt"
                required
                placeholder="Example: Futuristic London at night with flying cars above Tower Bridge, cinematic lighting, realistic movement..."
            >{{ prompt }}</textarea>

            <label>Video length</label>

            <select name="duration" id="duration" onchange="updatePrice()">

                <option value="5s"
                    {% if duration == "5s" %}selected{% endif %}>
                    5 seconds
                </option>

                <option value="10s"
                    {% if duration == "10s" %}selected{% endif %}>
                    10 seconds
                </option>

            </select>

            <label>Video format</label>

            <select name="aspect_ratio">

                <option value="2:3"
                    {% if aspect_ratio == "2:3" %}selected{% endif %}>
                    Portrait 2:3
                </option>

                <option value="3:2"
                    {% if aspect_ratio == "3:2" %}selected{% endif %}>
                    Landscape 3:2
                </option>

                <option value="1:1"
                    {% if aspect_ratio == "1:1" %}selected{% endif %}>
                    Square 1:1
                </option>

            </select>

            <div class="price">
                Estimated generation cost:
                <br>
                <strong id="price">$0.05</strong>
            </div>

            <div class="small">
                Economy model: Kandinsky 5 Distill
            </div>

            <button type="submit">
                ✨ Generate Video
            </button>

        </form>

        {% if error %}
            <div class="error">
                {{ error }}
            </div>
        {% endif %}

    </div>

    {% if video_url %}

    <div class="card">

        <h2>🎥 Your Video</h2>

        <video controls autoplay loop>
            <source src="{{ video_url }}" type="video/mp4">
        </video>

        <a
            class="download"
            href="{{ video_url }}"
            target="_blank"
        >
            ⬇ Open / Download Video
        </a>

    </div>

    {% endif %}

</div>

<script>

function updatePrice() {

    const duration =
        document.getElementById("duration").value;

    const price =
        duration === "10s" ? "$0.10" : "$0.05";

    document.getElementById("price").innerText = price;
}

updatePrice();

</script>

</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def home():

    video_url = None
    error = None

    prompt = ""
    duration = "5s"
    aspect_ratio = "2:3"

    if request.method == "POST":

        prompt = request.form.get(
            "prompt", ""
        ).strip()

        duration = request.form.get(
            "duration", "5s"
        )

        aspect_ratio = request.form.get(
            "aspect_ratio", "2:3"
        )

        # Only allow supported values
        if duration not in ["5s", "10s"]:
            duration = "5s"

        if aspect_ratio not in [
            "2:3",
            "3:2",
            "1:1"
        ]:
            aspect_ratio = "2:3"

        if not prompt:

            error = "Please enter a video idea."

        else:

            try:

                print(
                    "Starting Kandinsky generation...",
                    flush=True
                )

                result = fal_client.subscribe(
                    MODEL,
                    arguments={
                        "prompt": prompt,
                        "aspect_ratio": aspect_ratio,
                        "duration": duration
                    },
                    with_logs=True,
                    client_timeout=580
                )

                print(
                    "FAL RESULT:",
                    result,
                    flush=True
                )

                video = result.get(
                    "video", {}
                )

                video_url = video.get(
                    "url"
                )

                if not video_url:

                    error = (
                        "Generation finished, but "
                        "no video URL was returned."
                    )

            except Exception as e:

                print(
                    "VIDEO GENERATION ERROR:",
                    flush=True
                )

                traceback.print_exc()

                error = str(e)

    return render_template_string(
        HTML,
        video_url=video_url,
        error=error,
        prompt=prompt,
        duration=duration,
        aspect_ratio=aspect_ratio
    )


@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "model": MODEL
    })


if __name__ == "__main__":

    import os

    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
