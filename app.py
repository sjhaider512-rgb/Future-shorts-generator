import os
import uuid
import tempfile
import subprocess
from pathlib import Path

import requests
import fal_client
from gtts import gTTS
from flask import Flask, request, render_template_string, send_file


app = Flask(__name__)

FAL_KEY = os.environ.get("FAL_KEY")
if FAL_KEY:
    os.environ["FAL_KEY"] = FAL_KEY

MODEL_ID = "fal-ai/kandinsky5/text-to-video/distill"
CLIP_LENGTH = 5
OUTPUT_DIR = Path(tempfile.gettempdir()) / "future_shorts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Future Shorts AI</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0; min-height: 100vh;
    font-family: Inter, Arial, sans-serif;
    color: white;
    background: radial-gradient(circle at top left, #17346d 0%, #08142e 42%, #050b19 100%);
    padding: 45px 20px;
}
.wrapper { width: 100%; max-width: 720px; margin: auto; }
.brand { margin-bottom: 25px; }
.brand-title { font-size: 34px; font-weight: 800; margin: 0; }
.brand-subtitle { color: #b8c6e8; margin-top: 7px; font-size: 15px; }
.card {
    background: linear-gradient(145deg, rgba(31, 67, 132, 0.88), rgba(15, 30, 68, 0.95));
    border: 1px solid rgba(121, 172, 255, 0.25);
    border-radius: 24px; padding: 28px;
    box-shadow: 0 30px 80px rgba(0, 0, 0, 0.35);
}
.badge {
    display: inline-block; background: rgba(74, 147, 255, 0.18);
    border: 1px solid rgba(93, 168, 255, 0.35); color: #dceaff;
    border-radius: 20px; padding: 7px 12px; font-size: 13px; margin-bottom: 22px;
}
label { display: block; font-size: 15px; font-weight: 700; margin-top: 17px; margin-bottom: 8px; }
textarea, select, input[type="file"] {
    width: 100%; border: 1px solid #5270a5; border-radius: 13px;
    background: rgba(7, 18, 42, 0.72); color: white; font-size: 15px; padding: 14px; outline: none;
}
input[type="file"] { padding: 10px; cursor: pointer; }
textarea { min-height: 110px; resize: vertical; }
select option { background: #101d3b; color: white; }
button {
    width: 100%; margin-top: 23px; padding: 16px; border: none; border-radius: 14px;
    cursor: pointer; color: white; font-size: 16px; font-weight: 800;
    background: linear-gradient(90deg, #21d4fd, #7868ff, #e56cff);
}
.message { margin-top: 22px; padding: 15px; border-radius: 12px; background: rgba(255,255,255,0.08); }
.error { border: 1px solid #ff6d7a; color: #ffd7da; }
.success { border: 1px solid #43e0b3; }
video { width: 100%; margin-top: 18px; border-radius: 15px; background: black; }
.download { display: block; text-align: center; text-decoration: none; color: white; font-weight: 700; margin-top: 14px; padding: 13px; border-radius: 12px; background: rgba(255,255,255,0.12); }
.progress { display: none; margin-top: 20px; padding: 15px; border-radius: 12px; background: rgba(255,255,255,0.08); color: #dce8ff; }
</style>
</head>
<body>
<div class="wrapper">
<div class="brand">
<h1 class="brand-title">🎬 Future Shorts AI</h1>
<div class="brand-subtitle">Turn your story into an AI video with dual characters & free voiceover.</div>
</div>
<div class="card">
<div class="badge">⚡ Story Mode: Dual Images & Free Voiceover</div>
<form method="POST" id="videoForm" enctype="multipart/form-data">
<label>Your video visual prompt</label>
<textarea name="prompt" required>{{ prompt }}</textarea>
<label>Voiceover Script / Dialogue (Optional - Free TTS)</label>
<textarea name="voiceover_script">{{ voiceover_script }}</textarea>
<label>Reference Image: Zainab (Optional)</label>
<input type="file" name="image_zainab" accept="image/*">
<label>Reference Image: Masooma (Optional)</label>
<input type="file" name="image_masooma" accept="image/*">
<label>Video length</label>
<select name="duration" id="duration">
<option value="5" {% if duration == 5 %}selected{% endif %}>5 seconds</option>
<option value="10" {% if duration == 10 %}selected{% endif %}>10 seconds</option>
<option value="20" {% if duration == 20 %}selected{% endif %}>20 seconds</option>
<option value="40" {% if duration == 40 %}selected{% endif %}>40 seconds</option>
<option value="60" {% if duration == 60 %}selected{% endif %}>60 seconds</option>
</select>
<label>Video format</label>
<select name="aspect_ratio">
<option value="9:16" {% if aspect_ratio == "9:16" %}selected{% endif %}>Portrait 9:16</option>
<option value="16:9" {% if aspect_ratio == "16:9" %}selected{% endif %}>Landscape 16:9</option>
<option value="1:1" {% if aspect_ratio == "1:1" %}selected{% endif %}>Square 1:1</option>
</select>
<button type="submit" id="generateButton">✨ Generate Story with Voiceover</button>
<div class="progress" id="progress">⏳ Generating video clips and synthesizing voiceover... Please keep this page open...</div>
</form>
{% if error %}
<div class="message error"><strong>Error:</strong> {{ error }}</div>
{% endif %}
{% if video_url %}
<div class="message success">
<strong>✅ Your story video is ready</strong>
<video controls playsinline><source src="{{ video_url }}" type="video/mp4"></video>
<a class="download" href="{{ video_url }}" download>⬇ Download Video</a>
</div>
{% endif %}
</div>
</div>
<script>
document.getElementById("videoForm").addEventListener("submit", function() {
    document.getElementById("generateButton").disabled = true;
    document.getElementById("generateButton").innerText = "⏳ Generating...";
    document.getElementById("progress").style.display = "block";
});
</script>
</body>
</html>
"""

def fal_aspect_ratio(user_ratio):
    if user_ratio == "16:9": return "3:2"
    if user_ratio == "1:1": return "1:1"
    return "2:3"

def fal_resolution(user_ratio):
    if user_ratio == "16:9": return "768x512"
    if user_ratio == "1:1": return "512x512"
    return "768x512"

def extract_video_url(result):
    if not result: return None
    video = result.get("video")
    if isinstance(video, dict):
        url = video.get("url")
        if url: return url
    videos = result.get("videos")
    if isinstance(videos, list) and videos:
        first = videos[0]
        if isinstance(first, dict): return first.get("url")
    return None

def generate_clip(prompt, user_aspect_ratio, image_url=None):
    arguments = {
        "prompt": prompt,
        "resolution": fal_resolution(user_aspect_ratio),
        "aspect_ratio": fal_aspect_ratio(user_aspect_ratio),
        "duration": "5s",
        "audio": True,
    }
    if image_url: arguments["image_url"] = image_url
    result = fal_client.subscribe(MODEL_ID, arguments=arguments, with_logs=True)
    video_url = extract_video_url(result)
    if not video_url:
        raise RuntimeError("FAL completed the request but did not return a video URL.")
    return video_url

def download_video(url, destination):
    response = requests.get(url, stream=True, timeout=300)
    response.raise_for_status()
    with open(destination, "wb") as file:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk: file.write(chunk)

def combine_videos_with_audio(video_files, output_file, tts_audio_path=None):
    temp_combined = OUTPUT_DIR / f"{uuid.uuid4()}_raw.mp4"
    if len(video_files) == 1:
        os.replace(video_files[0], temp_combined)
    else:
        concat_file = OUTPUT_DIR / f"{uuid.uuid4()}_concat.txt"
        with open(concat_file, "w", encoding="utf-8") as file:
            for video in video_files:
                safe_path = str(video).replace("'", "'\\''")
                file.write(f"file '{safe_path}'\n")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(temp_combined)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try: concat_file.unlink()
        except Exception: pass

    if tts_audio_path and Path(tts_audio_path).exists():
        command = [
            "ffmpeg", "-y", "-i", str(temp_combined), "-i", str(tts_audio_path),
            "-map", "0:v:0", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "23", "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(output_file)
        ]
    else:
        command = [
            "ffmpeg", "-y", "-i", str(temp_combined), "-c:v", "libx264",
            "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-movflags", "+faststart", str(output_file)
        ]

    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try: temp_combined.unlink(missing_ok=True)
    except Exception: pass

    if process.returncode != 0:
        raise RuntimeError("Could not combine video and voiceover. FFmpeg error: " + process.stderr[-1200:])

@app.route("/", methods=["GET", "POST"])
def home():
    error, video_url = None, None
    prompt, voiceover_script = "", ""
    duration, aspect_ratio = 5, "9:16"
    zainab_url, masooma_url = None, None

    if request.method == "POST":
        prompt = request.form.get("prompt", "").strip()
        voiceover_script = request.form.get("voiceover_script", "").strip()
        try: duration = int(request.form.get("duration", "5"))
        except ValueError: duration = 5
        aspect_ratio = request.form.get("aspect_ratio", "9:16")

        file_zainab = request.files.get("image_zainab")
        if file_zainab and file_zainab.filename != "":
            try:
                p1 = Path(tempfile.gettempdir()) / f"{uuid.uuid4()}_{file_zainab.filename}"
                file_zainab.save(p1)
                zainab_url = fal_client.upload(str(p1))
                p1.unlink(missing_ok=True)
            except Exception as e1: print("ZAINAB IMAGE ERROR:", repr(e1), flush=True)

        file_masooma = request.files.get("image_masooma")
        if file_masooma and file_masooma.filename != "":
            try:
                p2 = Path(tempfile.gettempdir()) / f"{uuid.uuid4()}_{file_masooma.filename}"
                file_masooma.save(p2)
                masooma_url = fal_client.upload(str(p2))
                p2.unlink(missing_ok=True)
            except Exception as e2: print("MASOOMA IMAGE ERROR:", repr(e2), flush=True)

        if not prompt:
            error = "Please enter a video idea."
        elif not FAL_KEY:
            error = "FAL_KEY is not configured on the server."
        else:
            try:
                number_of_clips = duration // CLIP_LENGTH
                job_id = str(uuid.uuid4())
                downloaded_files = []

                for index in range(number_of_clips):
                    scene_prompt = f"{prompt}\n\nScene {index+1} of {number_of_clips} featuring Zainab and Masooma. Consistent subject appearance, high quality."
                    current_image_url = zainab_url if (index % 2 == 0 and zainab_url) else (masooma_url if masooma_url else zainab_url)
                    remote_url = generate_clip(scene_prompt, aspect_ratio, image_url=current_image_url)
                    local_file = OUTPUT_DIR / f"{job_id}_{index}.mp4"
                    download_video(remote_url, local_file)
                    downloaded_files.append(local_file)

                tts_audio_file = None
                if voiceover_script:
                    try:
                        tts = gTTS(text=voiceover_script, lang='en', slow=False)
                        tts_audio_file = OUTPUT_DIR / f"{job_id}_voice.mp3"
                        tts.save(str(tts_audio_file))
                    except Exception as tts_err: print("TTS ERROR:", repr(tts_err), flush=True)

                final_file = OUTPUT_DIR / f"{job_id}_final.mp4"
                combine_videos_with_audio(downloaded_files, final_file, tts_audio_path=tts_audio_file)

                for temp_file in downloaded_files:
                    try: temp_file.unlink()
                    except Exception: pass
                if tts_audio_file and tts_audio_file.exists():
                    try: tts_audio_file.unlink()
                    except Exception: pass

                video_url = "/video/" + final_file.name
            except Exception as exc:
                print("ERROR:", repr(exc), flush=True)
                error = str(exc)

    return render_template_string(HTML, prompt=prompt, voiceover_script=voiceover_script, duration=duration, aspect_ratio=aspect_ratio, video_url=video_url, error=error)

@app.route("/video/<filename>")
def video(filename):
    file_path = OUTPUT_DIR / os.path.basename(filename)
    if not file_path.exists(): return "Video not found.", 404
    return send_file(file_path, mimetype="video/mp4", as_attachment=False)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

