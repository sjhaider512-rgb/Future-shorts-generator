import os
import uuid
import json
import tempfile
import subprocess
from pathlib import Path

import requests
import fal_client
from gtts import gTTS
from flask import Flask, request, render_template_string, send_file
import google.genai as genai

app = Flask(__name__)

# =========================================================
# CONFIGURATION
# =========================================================

FAL_KEY = os.environ.get("FAL_KEY")
if FAL_KEY:
    os.environ["FAL_KEY"] = FAL_KEY

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

MODEL_ID = "fal-ai/kandinsky5/text-to-video/distill"
CLIP_LENGTH = 5
OUTPUT_DIR = Path(tempfile.gettempdir()) / "future_shorts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================================================
# HTML TEMPLATE
# =========================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Future Shorts AI — Cinema Studio</title>
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
textarea, select, input[type="text"] {
    width: 100%; border: 1px solid #5270a5; border-radius: 13px;
    background: rgba(7, 18, 42, 0.72); color: white; font-size: 15px; padding: 14px; outline: none;
}
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
.progress { display: none; margin-top: 20px; padding: 18px; border-radius: 12px; background: rgba(255,255,255,0.08); color: #dce8ff; line-height: 1.6; }
.progress-bar-container { width: 100%; background: rgba(255,255,255,0.15); border-radius: 10px; height: 12px; margin-top: 12px; overflow: hidden; }
.progress-bar { width: 0%; height: 100%; background: linear-gradient(90deg, #21d4fd, #7868ff); border-radius: 10px; transition: width 0.3s ease; }
.tip { font-size: 12px; color: #9bb1dd; margin-top: 4px; }
</style>
</head>
<body>
<div class="wrapper">
<div class="brand">
<h1 class="brand-title">🎬 Future Shorts AI</h1>
<div class="brand-subtitle">AI-Directed Historical Documentaries & Story Studio</div>
</div>
<div class="card">
<div class="badge">✨ Gemini AI Director & Continuous Frame-Chaining Engine</div>
<form method="POST" id="videoForm">

<label>Enter Documentary Topic or Title</label>
<input type="text" name="topic" placeholder="e.g., The Mystery of Ancient Alexandria Library" value="{{ topic }}">
<div class="tip">Leave blank if you want to use your own custom prompt and script below.</div>

<label>Custom Visual Prompt (Optional)</label>
<textarea name="prompt" placeholder="Static medium shot, fixed camera...">{{ prompt }}</textarea>

<label>Custom Narration Script (Optional)</label>
<textarea name="voiceover_script" placeholder="Narrator script here...">{{ voiceover_script }}</textarea>

<label>Video Length Target</label>
<select name="duration" id="duration" onchange="updateCost()">
<option value="10" {% if duration == 10 %}selected{% endif %}>10 seconds (2 scenes test)</option>
<option value="20" {% if duration == 20 %}selected{% endif %}>20 seconds (4 scenes)</option>
<option value="60" {% if duration == 60 %}selected{% endif %}>1 Minute (12 scenes)</option>
<option value="300" {% if duration == 300 %}selected{% endif %}>5 Minutes (Full Documentary)</option>
</select>

<label>Video Format</label>
<select name="aspect_ratio">
<option value="16:9" {% if aspect_ratio == "16:9" %}selected{% endif %}>Landscape 16:9 — YouTube Long Form</option>
<option value="9:16" {% if aspect_ratio == "9:16" %}selected{% endif %}>Portrait 9:16 — TikTok / Shorts / Reels</option>
</select>

<div class="cost-box">
<div class="cost-label">Estimated generation cost</div>
<div class="cost" id="cost">$0.10</div>
<div class="cost-note">Raw FAL API estimate ($0.05 per 5s clip).</div>
</div>

<button type="submit" id="generateButton">✨ Direct & Generate Documentary Video</button>

<div class="progress" id="progress">
⏳ <strong id="progressStatus">Initializing AI Director...</strong> (<span id="progressPercent">0%</span> completed)<br>
<span id="progressSubtext">Analyzing topic and writing script breakdown...</span>
<div class="progress-bar-container">
<div class="progress-bar" id="progressBar"></div>
</div>
</div>

</form>

{% if error %}
<div class="message error"><strong>Error:</strong> {{ error }}</div>
{% endif %}

{% if video_url %}
<div class="message success">
<strong>✅ Your documentary video is ready!</strong>
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
    document.getElementById("generateButton").innerText = "⏳ AI Director at Work...";
    document.getElementById("progress").style.display = "block";
    
    let percent = 5;
    const progressBar = document.getElementById("progressBar");
    const progressPercent = document.getElementById("progressPercent");
    const progressStatus = document.getElementById("progressStatus");
    const progressSubtext = document.getElementById("progressSubtext");
    
    const steps = [
        { at: 20, main: "Gemini AI Director Planning", sub: "Writing script and scene breakdowns..." },
        { at: 45, main: "Rendering Scene 1", sub: "Generating initial cinematic frame via FAL AI..." },
        { at: 70, main: "Rendering Scene 2", sub: "Applying frame-chaining continuity..." },
        { at: 88, main: "Synthesizing Narration", sub: "Recording professional voiceover with gTTS..." },
        { at: 96, main: "Stitching Final Production", sub: "Combining clips and audio with FFmpeg..." }
    ];
    
    const interval = setInterval(() => {
        if (percent < 98) {
            percent += 1;
            progressBar.style.width = percent + "%";
            progressPercent.innerText = percent + "%";
            
            steps.forEach(step => {
                if (percent === step.at) {
                    progressStatus.innerText = step.main;
                    progressSubtext.innerText = step.sub;
                }
            });
        }
    }, 350);
});

updateCost();
</script>
</body>
</html>
"""

# =========================================================
# AI DIRECTOR (GEMINI)
# =========================================================

def generate_ai_direction(topic, num_scenes):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set in environment variables.")
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = (
        "You are an expert documentary film director and scriptwriter.\n"
        f"Create a documentary script and scene breakdown for the topic: \"{topic}\".\n"
        f"You must output exactly {num_scenes} scenes (each scene represents 5 seconds of video).\n\n"
        "Return ONLY valid JSON matching this exact structure, with no markdown code blocks around it:\n"
        "{\n"
        ' "master_visual_theme": "Consistent visual description of main characters, clothing, and environment style",\n'
        ' "scenes": [\n'
        " {\n"
        ' "visual_prompt": "Detailed cinematic visual prompt for scene 1 with static camera and consistent characters.",\n'
        ' "narration": "Narration text spoken by the narrator for this 5 second scene."\n'
        " }\n"
        " ]\n"
        "}"
    )
    
    response = client.models.generate_content(
        model='gemini-3.8-flash',
        contents=prompt
    )
    
    raw_text = response.text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]
    
    data = json.loads(raw_text.strip())
    return data

# =========================================================
# HELPERS
# =========================================================

def fal_aspect_ratio(user_ratio):
    return "3:2"

def fal_resolution(user_ratio):
    return "768x512"

def extract_video_url(result):
    if not result: return None
    video = result.get("video")
    if isinstance(video, dict): return video.get("url")
    videos = result.get("videos")
    if isinstance(videos, list) and videos: return videos[0].get("url")
    return None

def extract_last_frame(video_path, output_image_path):
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

def build_single_narrator_audio(narration_texts, job_id):
    audio_clips = []
    for index, text in enumerate(narration_texts):
        if not text.strip(): continue
        speech_file = OUTPUT_DIR / f"{job_id}_speech_{index}.mp3"
        tts = gTTS(text=text, lang="en", tld="com", slow=False)
        tts.save(str(speech_file))
        if speech_file.exists():
            audio_clips.append(speech_file)

    if not audio_clips: return None
    if len(audio_clips) == 1: return audio_clips[0]

    concat_list = OUTPUT_DIR / f"{job_id}_audio_concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for audio in audio_clips:
            safe_path = str(audio).replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")

    master_audio = OUTPUT_DIR / f"{job_id}_master_narration.mp3"
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
        raise RuntimeError("FFmpeg combination error: " + process.stderr[-1200:])

# =========================================================
# MAIN ROUTE
# =========================================================

@app.route("/", methods=["GET", "POST"])
def home():
    error, video_url = None, None
    topic, prompt, voiceover_script = "", "", ""
    duration, aspect_ratio = 10, "16:9"

    if request.method == "POST":
        try:
            topic = request.form.get("topic", "").strip()
            prompt = request.form.get("prompt", "").strip()
            voiceover_script = request.form.get("voiceover_script", "").strip()
            
            try: duration = int(request.form.get("duration", "10"))
            except ValueError: duration = 10
            
            aspect_ratio = request.form.get("aspect_ratio", "16:9")

            if not FAL_KEY:
                error = "FAL_KEY is not configured on the server."
            else:
                number_of_clips = max(1, duration // CLIP_LENGTH)
                job_id = str(uuid.uuid4())
                downloaded_files = []
                narration_texts = []

                if topic:
                    ai_plan = generate_ai_direction(topic, number_of_clips)
                    master_theme = ai_plan.get("master_visual_theme", "")
                    scenes = ai_plan.get("scenes", [])
                    
                    current_image_url = None
                    for index, scene in enumerate(scenes[:number_of_clips]):
                        scene_visual = f"Static medium shot, fixed camera. {master_theme}. {scene.get('visual_prompt', '')}"
                        narration_texts.append(scene.get("narration", ""))
                        
                        remote_url = generate_clip(scene_visual, aspect_ratio, image_url=current_image_url)
                        local_file = OUTPUT_DIR / f"{job_id}_{index}.mp4"
                        download_video(remote_url, local_file)
                        downloaded_files.append(local_file)

                        last_frame = OUTPUT_DIR / f"{job_id}_frame_{index}.jpg"
                        extract_last_frame(local_file, last_frame)
                        if last_frame.exists():
                            try:
                                current_image_url = fal_client.upload(str(last_frame))
                                last_frame.unlink(missing_ok=True)
                            except Exception: pass
                else:
                    if not prompt:
                        raise ValueError("Please provide either a documentary topic or a custom visual prompt.")
                    
                    narration_texts = [voiceover_script] if voiceover_script else [""]
                    current_image_url = None
                    for index in range(number_of_clips):
                        scene_prompt = f"Static medium shot, fixed camera. {prompt}\n\nScene {index+1} of {number_of_clips}, maintaining strict character and scene continuity."
                        remote_url = generate_clip(scene_prompt, aspect_ratio, image_url=current_image_url)
                        local_file = OUTPUT_DIR / f"{job_id}_{index}.mp4"
                        download_video(remote_url, local_file)
                        downloaded_files.append(local_file)

                        last_frame = OUTPUT_DIR / f"{job_id}_frame_{index}.jpg"
                        extract_last_frame(local_file, last_frame)
                        if last_frame.exists():
                            try:
                                current_image_url = fal_client.upload(str(last_frame))
                                last_frame.unlink(missing_ok=True)
                            except Exception: pass

                tts_audio_file = build_single_narrator_audio(narration_texts, job_id)

                final_file = OUTPUT_DIR / f"{job_id}_final.mp4"
                combine_videos_with_audio(downloaded_files, final_file, tts_audio_path=tts_audio_file)

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
        HTML_TEMPLATE, topic=topic, prompt=prompt, voiceover_script=voiceover_script,
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

