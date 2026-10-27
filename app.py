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

# =========================================================
# CONFIGURATION
# =========================================================

FAL_KEY = os.environ.get("FAL_KEY")
if FAL_KEY:
    os.environ["FAL_KEY"] = FAL_KEY

MODEL_ID = "fal-ai/kandinsky5/text-to-video/distill"
CLIP_LENGTH = 5
OUTPUT_DIR = Path(tempfile.gettempdir()) / "future_shorts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VOICE_PROFILES = {
    "narrator": {"lang": "en", "tld": "com"},
    "zainab": {"lang": "en", "tld": "co.uk"},
    "masooma": {"lang": "en", "tld": "ca"},
    "default": {"lang": "en", "tld": "com"}
}

# =========================================================
# HTML TEMPLATE (Full Featured UI Restored)
# =========================================================

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Future Shorts AI — Story Studio</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0; min-height: 100vh;
    font-family: Inter, Arial, sans-serif;
    color: white;
    background: radial-gradient(circle at top left, #17346d 0%, #08142e 42%, #050b19 100%);
    padding: 45px 20px;
}
.wrapper { width: 100%; max-width: 760px; margin: auto; }
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
.cost-box {
    margin-top: 22px; border: 1px solid rgba(45, 236, 189, 0.55);
    background: rgba(15, 100, 82, 0.16); border-radius: 14px; padding: 15px;
}
.cost-label { font-size: 13px; color: #b9f6e5; }
.cost { font-size: 27px; font-weight: 800; margin-top: 3px; }
.cost-note { font-size: 12px; color: #9eb1d8; margin-top: 6px; }
button {
    width: 100%; margin-top: 23px; padding: 16px; border: none; border-radius: 14px;
    cursor: pointer; color: white; font-size: 16px; font-weight: 800;
    background: linear-gradient(90deg, #21d4fd, #7868ff, #e56cff);
    transition: transform 0.15s ease;
}
button:hover { transform: translateY(-1px); }
button:disabled { opacity: 0.6; cursor: wait; }
.message { margin-top: 22px; padding: 15px; border-radius: 12px; background: rgba(255,255,255,0.08); }
.error { border: 1px solid #ff6d7a; color: #ffd7da; }
.success { border: 1px solid #43e0b3; }
video { width: 100%; margin-top: 18px; border-radius: 15px; background: black; }
.download { display: block; text-align: center; text-decoration: none; color: white; font-weight: 700; margin-top: 14px; padding: 13px; border-radius: 12px; background: rgba(255,255,255,0.12); }
.progress { display: none; margin-top: 20px; padding: 15px; border-radius: 12px; background: rgba(255,255,255,0.08); color: #dce8ff; }
.tip { font-size: 12px; color: #9bb1dd; margin-top: 4px; }
</style>
</head>
<body>
<div class="wrapper">
<div class="brand">
<h1 class="brand-title">🎬 Future Shorts AI</h1>
<div class="brand-subtitle">Cinema-Grade Animated Story & History Video Studio</div>
</div>
<div class="card">
<div class="badge">⚡ Multi-Speaker Dialogue & Continuous Consistency Engine</div>
<form method="POST" id="videoForm" enctype="multipart/form-data">

<label>Your video visual prompt</label>
<textarea name="prompt" required placeholder="Describe the scene visuals, cinematic camera movement, environment, atmosphere...">{{ prompt }}</textarea>

<label>Voiceover Script / Multi-Character Dialogue</label>
<div class="tip">Format speaker lines with 'Zainab:', 'Masooma:', or 'Narrator:' for character-specific voice synthesis.</div>
<textarea name="voiceover_script" placeholder="Narrator: Long ago in ancient Mesopotamia...&#10;Zainab: Look at these majestic ancient towers!&#10;Masooma: They were built thousands of years ago.">{{ voiceover_script }}</textarea>

<label>Reference Image: Zainab (Optional)</label>
<input type="file" name="image_zainab" accept="image/*">

<label>Reference Image: Masooma (Optional)</label>
<input type="file" name="image_masooma" accept="image/*">

<label>Video length Target</label>
<select name="duration" id="duration" onchange="updateCost()">
<option value="5" {% if duration == 5 %}selected{% endif %}>5 seconds (Test clip)</option>
<option value="10" {% if duration == 10 %}selected{% endif %}>10 seconds (Short scene)</option>
<option value="20" {% if duration == 20 %}selected{% endif %}>20 seconds</option>
<option value="60" {% if duration == 60 %}selected{% endif %}>1 Minute</option>
<option value="300" {% if duration == 300 %}selected{% endif %}>5 Minutes (Full Scene)</option>
<option value="600" {% if duration == 600 %}selected{% endif %}>10 Minutes (Full Documentary Chapter)</option>
<option value="900" {% if duration == 900 %}selected{% endif %}>15 Minutes</option>
<option value="3600" {% if duration == 3600 %}selected{% endif %}>60 Minutes (Full Feature)</option>
</select>

<label>Video format</label>
<select name="aspect_ratio">
<option value="9:16" {% if aspect_ratio == "9:16" %}selected{% endif %}>Portrait 9:16 — TikTok / Shorts / Reels</option>
<option value="16:9" {% if aspect_ratio == "16:9" %}selected{% endif %}>Landscape 16:9 — YouTube Long Form</option>
<option value="1:1" {% if aspect_ratio == "1:1" %}selected{% endif %}>Square 1:1</option>
</select>

<div class="cost-box">
<div class="cost-label">Estimated generation cost</div>
<div class="cost" id="cost">$0.05</div>
<div class="cost-note">Raw FAL API estimate ($0.05 per 5s clip).</div>
</div>

<button type="submit" id="generateButton">✨ Generate Story Video with Voiceover</button>

<div class="progress" id="progress">
⏳ Generating continuous video clips & synthesizing character audio...<br>
Please keep this browser window active during long-form renders.
</div>

</form>

{% if error %}
<div class="message error"><strong>Error:</strong> {{ error }}</div>
{% endif %}

{% if video_url %}
<div class="message success">
<strong>✅ Your story video is ready!</strong>
<video controls playsinline><source src="{{ video_url }}" type="video/mp4"></video>
<a class="download" href="{{ video_url }}" download>⬇ Download Video</a>
</div>
{% endif %}

</div>
</div>

<script>
function updateCost() {
    const duration = parseInt(document.getElementById("duration").value);
    const clips = Math.ceil(duration / 5);
    const estimated = clips * 0.05;
    document.getElementById("cost").innerText = "$" + estimated.toFixed(2);
}

document.getElementById("videoForm").addEventListener("submit", function() {
    document.getElementById("generateButton").disabled = true;
    document.getElementById("generateButton").innerText = "⏳ Rendering Consistent Clips...";
    document.getElementById("progress").style.display = "block";
});

updateCost();
</script>
</body>
</html>
"""

# =========================================================
# HELPERS
# =========================================================

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

def extract_last_frame(video_path, output_image_path):
    """Extracts the final frame of a video clip to carry character consistency into the next chunk."""
    subprocess.run([
        "ffmpeg", "-y", "-sseof", "-1", "-i", str(video_path),
        "-update", "1", "-q:v", "1", str(output_image_path)
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

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

def build_multi_speaker_audio(script_text, job_id):
    if not script_text.strip():
        return None

    lines = script_text.strip().split("\n")
    audio_clips = []

    for index, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        speaker = "narrator"
        text = line

        if ":" in line:
            parts = line.split(":", 1)
            speaker_tag = parts[0].strip().lower()
            if speaker_tag in VOICE_PROFILES:
                speaker = speaker_tag
                text = parts[1].strip()

        if not text:
            continue

        profile = VOICE_PROFILES.get(speaker, VOICE_PROFILES["default"])
        processed_speech = OUTPUT_DIR / f"{job_id}_part_{index}.mp3"

        tts = gTTS(text=text, lang=profile["lang"], tld=profile["tld"], slow=False)
        tts.save(str(processed_speech))

        if processed_speech.exists():
            audio_clips.append(processed_speech)

    if not audio_clips:
        return None

    if len(audio_clips) == 1:
        return audio_clips[0]

    concat_list = OUTPUT_DIR / f"{job_id}_audio_concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for audio in audio_clips:
            safe_path = str(audio).replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")

    master_audio = OUTPUT_DIR / f"{job_id}_master_voiceover.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list), "-c", "copy", str(master_audio)
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    for clip in audio_clips:
        try: clip.unlink(missing_ok=True)
        except Exception: pass
    try: concat_list.unlink(missing_ok=True)
    except Exception: pass

    return master_audio

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
        
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_file), "-c", "copy", str(temp_combined)
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        try: concat_file.unlink(missing_ok=True)
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

# =========================================================
# MAIN ROUTE
# =========================================================

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

        # Handle Zainab Image Upload
        file_zainab = request.files.get("image_zainab")
        if file_zainab and file_zainab.filename != "":
            try:
                p1 = Path(tempfile.gettempdir()) / f"{uuid.uuid4()}_{file_zainab.filename}"
                file_zainab.save(p1)
                zainab_url = fal_client.upload(str(p1))
                p1.unlink(missing_ok=True)
            except Exception as e1: print("ZAINAB IMAGE ERROR:", repr(e1), flush=True)

        # Handle Masooma Image Upload
        file_masooma = request.files.get("image_masooma")
        if file_masooma and file_masooma.filename != "":
            try:
                p2 = Path(tempfile.gettempdir()) / f"{uuid.uuid4()}_{file_masooma.filename}"
                file_masooma.save(p2)
                masooma_url = fal_client.upload(str(p2))
                p2.unlink(missing_ok=True)
            except Exception as e2: print("MASOOMA IMAGE ERROR:", repr(e2), flush=True)

        if not prompt:
            error = "Please enter a video prompt idea."
        elif not FAL_KEY:
            error = "FAL_KEY is not configured on the server."
        else:
            try:
                number_of_clips = max(1, duration // CLIP_LENGTH)
                job_id = str(uuid.uuid4())
                downloaded_files = []

                # Set initial anchor image from uploads
                current_image_url = zainab_url if zainab_url else masooma_url

                # Render video clips sequentially with frame-chaining consistency
                for index in range(number_of_clips):
                    scene_prompt = f"{prompt}\n\nScene {index+1} of {number_of_clips} maintaining strict character and scene continuity, high-definition historical aesthetic."
                    
                    remote_url = generate_clip(scene_prompt, aspect_ratio, image_url=current_image_url)
                    local_file = OUTPUT_DIR / f"{job_id}_{index}.mp4"
                    download_video(remote_url, local_file)
                    downloaded_files.append(local_file)

                    # Extract final frame of this clip to pass into the next clip as reference!
                    last_frame_path = OUTPUT_DIR / f"{job_id}_frame_{index}.jpg"
                    extract_last_frame(local_file, last_frame_path)
                    if last_frame_path.exists():
                        try:
                            current_image_url = fal_client.upload(str(last_frame_path))
                            last_frame_path.unlink(missing_ok=True)
                        except Exception:
                            pass

                # Generate multi-character voiceover soundtrack
                tts_audio_file = build_multi_speaker_audio(voiceover_script, job_id)

                # Merge video clips with master soundtrack
                final_file = OUTPUT_DIR / f"{job_id}_final.mp4"
                combine_videos_with_audio(downloaded_files, final_file, tts_audio_path=tts_audio_file)

                # Cleanup temporary files
                for temp_file in downloaded_files:
                    try: temp_file.unlink(missing_ok=True)
                    except Exception: pass
                if tts_audio_file and tts_audio_file.exists():
                    try: tts_audio_file.unlink(missing_ok=True)
                    except Exception: pass

                video_url = "/video/" + final_file.name
            except Exception as exc:
                print("ERROR:", repr(exc), flush=True)
                error = str(exc)

    return render_template_string(
        HTML, prompt=prompt, voiceover_script=voiceover_script,
        duration=duration, aspect_ratio=aspect_ratio, video_url=video_url, error=error
    )

@app.route("/video/<filename>")
def video(filename):
    file_path = OUTPUT_DIR / os.path.basename(filename)
    if not file_path.exists(): return "Video not found.", 404
    return send_file(file_path, mimetype="video/mp4", as_attachment=False)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

