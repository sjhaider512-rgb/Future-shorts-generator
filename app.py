import os
import uuid
import tempfile
import subprocess
from pathlib import Path

import requests
import fal_client
from flask import Flask, request, render_template_string, send_file


app = Flask(__name__)


# =========================================================
# CONFIGURATION
# =========================================================

FAL_KEY = os.environ.get("FAL_KEY")

if FAL_KEY:
    os.environ["FAL_KEY"] = FAL_KEY


# Correct current FAL endpoint
MODEL_ID = "fal-ai/kandinsky5/text-to-video/distill"

# We generate 5-second clips and combine them for longer videos
CLIP_LENGTH = 5

# Current Kandinsky Distill price for 5 seconds
COST_PER_CLIP = 0.05


OUTPUT_DIR = Path(tempfile.gettempdir()) / "future_shorts"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# HTML
# =========================================================

HTML = """
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>Future Shorts AI</title>


<style>

* {
    box-sizing: border-box;
}


body {

    margin: 0;

    min-height: 100vh;

    font-family:
        Inter,
        Arial,
        Helvetica,
        sans-serif;

    color: white;

    background:
        radial-gradient(
            circle at top left,
            #17346d 0%,
            #08142e 42%,
            #050b19 100%
        );

    padding: 45px 20px;
}


.wrapper {

    width: 100%;

    max-width: 720px;

    margin: auto;
}


.brand {

    margin-bottom: 25px;
}


.brand-title {

    font-size: 34px;

    font-weight: 800;

    margin: 0;
}


.brand-subtitle {

    color: #b8c6e8;

    margin-top: 7px;

    font-size: 15px;
}


.card {

    background:
        linear-gradient(
            145deg,
            rgba(31, 67, 132, 0.88),
            rgba(15, 30, 68, 0.95)
        );

    border:
        1px solid
        rgba(121, 172, 255, 0.25);

    border-radius: 24px;

    padding: 28px;

    box-shadow:
        0 30px 80px
        rgba(0, 0, 0, 0.35);
}


.badge {

    display: inline-block;

    background:
        rgba(74, 147, 255, 0.18);

    border:
        1px solid
        rgba(93, 168, 255, 0.35);

    color: #dceaff;

    border-radius: 20px;

    padding: 7px 12px;

    font-size: 13px;

    margin-bottom: 22px;
}


label {

    display: block;

    font-size: 15px;

    font-weight: 700;

    margin-top: 17px;

    margin-bottom: 8px;
}


textarea,
select {

    width: 100%;

    border:
        1px solid
        #5270a5;

    border-radius: 13px;

    background:
        rgba(7, 18, 42, 0.72);

    color: white;

    font-size: 15px;

    padding: 14px;

    outline: none;
}


textarea {

    min-height: 145px;

    resize: vertical;
}


textarea:focus,
select:focus {

    border-color: #48d7ff;

    box-shadow:
        0 0 0 3px
        rgba(72, 215, 255, 0.12);
}


select option {

    background: #101d3b;

    color: white;
}


.cost-box {

    margin-top: 22px;

    border:
        1px solid
        rgba(45, 236, 189, 0.55);

    background:
        rgba(15, 100, 82, 0.16);

    border-radius: 14px;

    padding: 15px;
}


.cost-label {

    font-size: 13px;

    color: #b9f6e5;
}


.cost {

    font-size: 27px;

    font-weight: 800;

    margin-top: 3px;
}


.cost-note {

    font-size: 12px;

    color: #9eb1d8;

    margin-top: 6px;
}


button {

    width: 100%;

    margin-top: 23px;

    padding: 16px;

    border: none;

    border-radius: 14px;

    cursor: pointer;

    color: white;

    font-size: 16px;

    font-weight: 800;

    background:
        linear-gradient(
            90deg,
            #21d4fd,
            #7868ff,
            #e56cff
        );

    transition:
        transform 0.15s ease,
        opacity 0.15s ease;
}


button:hover {

    transform: translateY(-1px);
}


button:disabled {

    opacity: 0.6;

    cursor: wait;
}


.message {

    margin-top: 22px;

    padding: 15px;

    border-radius: 12px;

    background:
        rgba(255,255,255,0.08);
}


.error {

    border: 1px solid #ff6d7a;

    color: #ffd7da;
}


.success {

    border: 1px solid #43e0b3;
}


video {

    width: 100%;

    margin-top: 18px;

    border-radius: 15px;

    background: black;
}


.download {

    display: block;

    text-align: center;

    text-decoration: none;

    color: white;

    font-weight: 700;

    margin-top: 14px;

    padding: 13px;

    border-radius: 12px;

    background:
        rgba(255,255,255,0.12);
}


.progress {

    display: none;

    margin-top: 20px;

    padding: 15px;

    border-radius: 12px;

    background:
        rgba(255,255,255,0.08);

    color: #dce8ff;
}


@media(max-width: 600px) {

    body {

        padding: 25px 14px;
    }


    .card {

        padding: 20px;
    }


    .brand-title {

        font-size: 29px;
    }
}

</style>

</head>


<body>


<div class="wrapper">


<div class="brand">

<h1 class="brand-title">

🎬 Future Shorts AI

</h1>


<div class="brand-subtitle">

Turn your idea into an AI video.

</div>

</div>


<div class="card">


<div class="badge">

⚡ Economy Model

</div>


<form
    method="POST"
    id="videoForm"
>


<label>

Your video idea

</label>


<textarea
    name="prompt"
    required
    placeholder="Example: Futuristic London at night with flying cars above Tower Bridge, cinematic lighting, realistic movement..."
>{{ prompt }}</textarea>


<label>

Video length

</label>


<select
    name="duration"
    id="duration"
    onchange="updateCost()"
>


<option
    value="5"
    {% if duration == 5 %}selected{% endif %}
>
5 seconds
</option>


<option
    value="10"
    {% if duration == 10 %}selected{% endif %}
>
10 seconds
</option>


<option
    value="20"
    {% if duration == 20 %}selected{% endif %}
>
20 seconds
</option>


<option
    value="40"
    {% if duration == 40 %}selected{% endif %}
>
40 seconds
</option>


<option
    value="60"
    {% if duration == 60 %}selected{% endif %}
>
60 seconds
</option>


</select>


<label>

Video format

</label>


<select name="aspect_ratio">


<option
    value="9:16"
    {% if aspect_ratio == "9:16" %}selected{% endif %}
>
Portrait 9:16 — TikTok / Shorts / Reels
</option>


<option
    value="16:9"
    {% if aspect_ratio == "16:9" %}selected{% endif %}
>
Landscape 16:9 — YouTube
</option>


<option
    value="1:1"
    {% if aspect_ratio == "1:1" %}selected{% endif %}
>
Square 1:1
</option>


</select>


<div class="cost-box">


<div class="cost-label">

Estimated generation cost

</div>


<div
    class="cost"
    id="cost"
>

$0.05

</div>


<div class="cost-note">

Approximate estimate. Actual FAL charges may vary.

</div>


</div>


<div class="cost-note">

Economy model: Kandinsky 5 Distill

</div>


<button
    type="submit"
    id="generateButton"
>

✨ Generate Video

</button>


<div
    class="progress"
    id="progress"
>

⏳ Generating your AI video.

Longer videos require multiple AI clips.

Please keep this page open...

</div>


</form>


{% if error %}


<div class="message error">

<strong>Error:</strong>

{{ error }}

</div>


{% endif %}


{% if video_url %}


<div class="message success">


<strong>

✅ Your video is ready

</strong>


<video
    controls
    playsinline
>


<source
    src="{{ video_url }}"
    type="video/mp4"
>


</video>


<a
    class="download"
    href="{{ video_url }}"
    download
>

⬇ Download Video

</a>


</div>


{% endif %}


</div>


</div>


<script>


function updateCost() {


    const duration =
        parseInt(
            document.getElementById(
                "duration"
            ).value
        );


    const clips =
        Math.ceil(
            duration / 5
        );


    const estimated =
        clips * 0.05;


    document.getElementById(
        "cost"
    ).innerText =
        "$" + estimated.toFixed(2);

}


document
    .getElementById(
        "videoForm"
    )
    .addEventListener(
        "submit",
        function() {


            const button =
                document.getElementById(
                    "generateButton"
                );


            button.disabled = true;


            button.innerText =
                "⏳ Generating...";


            document.getElementById(
                "progress"
            ).style.display =
                "block";

        }
    );


updateCost();


</script>


</body>

</html>
"""


# =========================================================
# HELPERS
# =========================================================


def fal_aspect_ratio(user_ratio):

    # Kandinsky Distill currently supports:
    # 2:3 portrait
    # 3:2 landscape
    # 1:1 square

    if user_ratio == "16:9":
        return "3:2"

    if user_ratio == "1:1":
        return "1:1"

    return "2:3"


def fal_resolution(user_ratio):

    if user_ratio == "16:9":
        return "768x512"

    if user_ratio == "1:1":
        return "512x512"

    return "512x768"


def extract_video_url(result):

    if not result:
        return None


    video = result.get("video")


    if isinstance(video, dict):

        url = video.get("url")

        if url:
            return url


    videos = result.get("videos")


    if isinstance(videos, list) and videos:

        first = videos[0]

        if isinstance(first, dict):

            return first.get("url")


    return None


def generate_clip(
    prompt,
    user_aspect_ratio
):


    api_ratio = fal_aspect_ratio(
        user_aspect_ratio
    )


    resolution = fal_resolution(
        user_aspect_ratio
    )


    result = fal_client.subscribe(

        MODEL_ID,

        arguments={

            "prompt": prompt,

            "resolution": resolution,

            "aspect_ratio": api_ratio,

            "duration": "5s",
        },

        with_logs=True,
    )


    video_url = extract_video_url(
        result
    )


    if not video_url:

        raise RuntimeError(
            "FAL completed the request but "
            "did not return a video URL."
        )


    return video_url


def download_video(
    url,
    destination
):


    response = requests.get(

        url,

        stream=True,

        timeout=300
    )


    response.raise_for_status()


    with open(
        destination,
        "wb"
    ) as file:


        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):


            if chunk:

                file.write(chunk)


def combine_videos(
    video_files,
    output_file
):


    if len(video_files) == 1:


        os.replace(
            video_files[0],
            output_file
        )


        return


    concat_file = (
        OUTPUT_DIR /
        f"{uuid.uuid4()}_concat.txt"
    )


    with open(
        concat_file,
        "w",
        encoding="utf-8"
    ) as file:


        for video in video_files:


            safe_path = (
                str(video)
                .replace(
                    "'",
                    "'\\''"
                )
            )


            file.write(
                f"file '{safe_path}'\\n"
            )


    command = [

        "ffmpeg",

        "-y",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        str(concat_file),

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-c:a",
        "aac",

        "-movflags",
        "+faststart",

        str(output_file),
    ]


    process = subprocess.run(

        command,

        stdout=subprocess.PIPE,

        stderr=subprocess.PIPE,

        text=True
    )


    try:

        concat_file.unlink()

    except Exception:

        pass


    if process.returncode != 0:


        raise RuntimeError(

            "Could not combine generated clips. "
            "FFmpeg error: "
            + process.stderr[-1200:]

        )


# =========================================================
# MAIN ROUTE
# =========================================================


@app.route(
    "/",
    methods=[
        "GET",
        "POST"
    ]
)

def home():


    error = None

    video_url = None

    prompt = ""

    duration = 5

    aspect_ratio = "9:16"


    if request.method == "POST":


        prompt = (
            request.form
            .get(
                "prompt",
                ""
            )
            .strip()
        )


        try:


            duration = int(

                request.form.get(
                    "duration",
                    "5"
                )

            )


        except ValueError:


            duration = 5


        aspect_ratio = (

            request.form.get(
                "aspect_ratio",
                "9:16"
            )

        )


        allowed_durations = [

            5,
            10,
            20,
            40,
            60

        ]


        allowed_ratios = [

            "9:16",
            "16:9",
            "1:1"

        ]


        if duration not in allowed_durations:


            error = (
                "Invalid video duration."
            )


        elif aspect_ratio not in allowed_ratios:


            error = (
                "Invalid video format."
            )


        elif not prompt:


            error = (
                "Please enter a video idea."
            )


        elif not FAL_KEY:


            error = (

                "FAL_KEY is not configured "
                "on the server."

            )


        else:


            try:


                number_of_clips = (
                    duration //
                    CLIP_LENGTH
                )


                job_id = str(
                    uuid.uuid4()
                )


                downloaded_files = []


                for index in range(
                    number_of_clips
                ):


                    scene_number = (
                        index + 1
                    )


                    scene_prompt = f"""
{prompt}

This is scene {scene_number} of {number_of_clips}
of one continuous cinematic video.

Maintain consistent subject appearance,
characters,
clothing,
vehicle design,
environment,
lighting,
camera style,
colour palette,
and visual style.

The action should naturally progress
through the overall story.

Do not add any text.

Do not add captions.

Do not add subtitles.

Do not add logos.

Do not add watermarks.

Do not add UI elements.

Smooth realistic movement.

Cinematic composition.

High visual quality.
"""


                    remote_url = generate_clip(

                        scene_prompt,

                        aspect_ratio

                    )


                    local_file = (

                        OUTPUT_DIR /

                        f"{job_id}_{index}.mp4"

                    )


                    download_video(

                        remote_url,

                        local_file

                    )


                    downloaded_files.append(
                        local_file
                    )


                final_file = (

                    OUTPUT_DIR /

                    f"{job_id}_final.mp4"

                )


                combine_videos(

                    downloaded_files,

                    final_file

                )


                for temp_file in downloaded_files:


                    if temp_file == final_file:

                        continue


                    try:

                        temp_file.unlink()

                    except Exception:

                        pass


                video_url = (

                    "/video/" +

                    final_file.name

                )


            except Exception as exc:


                print(

                    "VIDEO GENERATION ERROR:",

                    repr(exc),

                    flush=True

                )


                error = str(exc)


    return render_template_string(

        HTML,

        prompt=prompt,

        duration=duration,

        aspect_ratio=aspect_ratio,

        video_url=video_url,

        error=error,

    )


# =========================================================
# VIDEO ROUTE
# =========================================================


@app.route(
    "/video/<filename>"
)

def video(filename):


    safe_name = os.path.basename(
        filename
    )


    file_path = (
        OUTPUT_DIR /
        safe_name
    )


    if not file_path.exists():


        return (

            "Video not found.",

            404

        )


    return send_file(

        file_path,

        mimetype="video/mp4",

        as_attachment=False

    )


# =========================================================
# LOCAL START
# =========================================================


if __name__ == "__main__":


    port = int(

        os.environ.get(
            "PORT",
            10000
        )

    )


    app.run(

        host="0.0.0.0",

        port=port

    )
