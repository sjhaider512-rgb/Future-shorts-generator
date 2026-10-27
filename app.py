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

# Config
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

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Future Shorts AI</title>
<style>
body { font-family: sans-serif; background: #08142e; color: white; padding: 20px; }
.card { max-width: 600px; margin: auto; background: #101d3b; padding: 20px; border-radius: 12px; }
textarea, select, input { width: 100%; margin-bottom: 15px; padding: 10px; background: #050b19; color: white; border: 1px solid #444; border-radius: 6px; }
button { width: 100%; padding: 12px; background: #21d4fd; border: none; font-weight: bold; cursor: pointer; border-radius: 6px; }
video { width: 100%; margin-top: 15px; border-radius: 8px; }
</style>
</head>
<body>
<div class="card">
<h2>🎬 Future Shorts AI - Cinema Studio</h2>
<form method="POST" enctype="multipart/form-data">
<label>Visual Prompt</label>
<textarea name="prompt" required>{{ prompt }}</textarea>

<label>Dialogue / Script</label>
<textarea name="voiceover_script">{{ voiceover_script }}</textarea>

<label>Character Reference Image (Optional Initial Anchor)</label>
<input type="file" name="reference_image" accept="image/*">

<label>Duration Target</label>
<select name="duration">
<option value="5" {% if duration == 5 %}selected{% endif %}>5 Seconds</option>
<option value="10" {% if duration == 10 %}selected{% endif %}>10 Seconds</option>
<option value="20" {% if duration == 20 %}selected{% endif %}>20 Seconds</option>
</select>

<label>Aspect Ratio</label>
<select name="aspect_ratio">
<option value="16:9">16:9 YouTube Long Form</option>
<option value="9:16">9:16 Shorts / Reels</option>
</select>

<button type="submit">✨ Generate Consistent Story Video</button>
</form>

{% if error %}<p style="color: red;"><strong>Error:</strong> {{ error }}</p>{% endif %}
{% if video_url %}
<h3>Generated Video:</h3>
<video controls src="{{ video_url }}"></video>
{% endif %}
</div>
</body>
</html>
"""

def extract_video_url(result):
    if not result: return None
    video = result.get("video")
    if isinstance(video, dict): return video.get("url")
    videos = result.get("videos")
    if isinstance(videos, list) and videos: return videos[0].get("url")
    return None

def extract_last_frame(video_path, output_image_path):
    """Extracts the final frame of a video to maintain character consistency in the next clip."""
    subprocess.run([
        "ffmpeg", "-y", "-sseof", "-1", "-i", str(video_path),
        "-update", "1", "-q:v", "1", str(output_image_path)
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def generate_clip(prompt, aspect_ratio, image_url=None):
    res = "768x512" if aspect_ratio == "16:9" else "512x768"
    ar = "3:2" if aspect_ratio == "16:9" else "2:3"
    args = {"prompt": prompt, "resolution": res, "aspect_ratio": ar, "duration": "5s", "audio": False}
    if image_url: args["image_url"] = image_url
    result = fal_client.subscribe(MODEL_ID, arguments=args, with_logs=True)
    return extract_video_url(result)

def build_multi_speaker_audio(script_text, job_id):
    if not script_text.strip(): return None
    lines = [l.strip() for l in script_text.strip().split("\n") if l.strip()]
    audio_clips = []

    for idx, line in enumerate(lines):
        speaker, text = "narrator", line
        if ":" in line:
            parts = line.split(":", 1)
            tag = parts[0].strip().lower()
            if tag in VOICE_PROFILES: speaker, text = tag, parts[1].strip()

        profile = VOICE_PROFILES.get(speaker, VOICE_PROFILES["default"])
        out_path = OUTPUT_DIR / f"{job_id}_voice_{idx}.mp3"
        tts = gTTS(text=text, lang=profile["lang"], tld=profile["tld"], slow=False)
        tts.save(str(out_path))
        if out_path.exists(): audio_clips.append(out_path)

    if not audio_clips: return None
    master = OUTPUT_DIR / f"{job_id}_master.mp3"
    concat_txt = OUTPUT_DIR / f"{job_id}_concat.txt"
    with open(concat_txt, "w") as f:
        for clip in audio_clips: f.write(f"file '{str(clip)}'\n")
    
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(master)])
    return master

@app.route("/", methods=["GET", "POST"])
def home():
    error, video_url = None, None
    prompt, voiceover_script = "", ""
    duration = 10

    if request.method == "POST":
        prompt = request.form.get("prompt", "").strip()
        voiceover_script = request.form.get("voiceover_script", "").strip()
        duration = int(request.form.get("duration", "10"))
        aspect_ratio = request.form.get("aspect_ratio", "16:9")

        ref_file = request.files.get("reference_image")
        current_image_url = None
        if ref_file and ref_file.filename:
            temp_img = OUTPUT_DIR / f"{uuid.uuid4()}_{ref_file.filename}"
            ref_file.save(temp_img)
            current_image_url = fal_client.upload(str(temp_img))
            temp_img.unlink(missing_ok=True)

        if not prompt or not FAL_KEY:
            error = "Missing prompt or API key configuration."
        else:
            try:
                clips_count = max(1, duration // CLIP_LENGTH)
                job_id = str(uuid.uuid4())
                downloaded_clips = []

                for i in range(clips_count):
                    clip_prompt = f"{prompt}. Continuous shot, matching character appearance perfectly."
                    remote_url = generate_clip(clip_prompt, aspect_ratio, image_url=current_image_url)
                    
                    local_clip = OUTPUT_DIR / f"{job_id}_{i}.mp4"
                    res = requests.get(remote_url)
                    with open(local_clip, "wb") as f: f.write(res.content)
                    downloaded_clips.append(local_clip)

                    # Extract final frame to chain into the next clip
                    last_frame_path = OUTPUT_DIR / f"{job_id}_frame_{i}.jpg"
                    extract_last_frame(local_clip, last_frame_path)
                    current_image_url = fal_client.upload(str(last_frame_path))

                master_audio = build_multi_speaker_audio(voiceover_script, job_id)
                final_file = OUTPUT_DIR / f"{job_id}_final.mp4"

                # Combine video and audio
                concat_file = OUTPUT_DIR / f"{job_id}_vid_concat.txt"
                with open(concat_file, "w") as f:
                    for c in downloaded_clips: f.write(f"file '{str(c)}'\n")
                
                raw_combined = OUTPUT_DIR / f"{job_id}_raw.mp4"
                subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(raw_combined)])

                if master_audio and master_audio.exists():
                    subprocess.run([
                        "ffmpeg", "-y", "-i", str(raw_combined), "-i", str(master_audio),
                        "-map", "0:v:0", "-map", "1:a", "-c:v", "libx264", "-c:a", "aac",
                        "-shortest", "-movflags", "+faststart", str(final_file)
                    ])
                else:
                    os.replace(raw_combined, final_file)

                video_url = f"/video/{final_file.name}"
            except Exception as e:
                error = str(e)

    return render_template_string(HTML, prompt=prompt, voiceover_script=voiceover_script, duration=duration, video_url=video_url, error=error)

@app.route("/video/<filename>")
def video(filename):
    file_path = OUTPUT_DIR / os.path.basename(filename)
    return send_file(file_path, mimetype="video/mp4")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

