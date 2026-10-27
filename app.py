import os
import re
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

# Voice configuration using clean Google Translate TLD accents (no distorted pitch filters)
VOICE_PROFILES = {
    "narrator": {"lang": "en", "tld": "com"}, # US Narrator
    "zainab": {"lang": "en", "tld": "co.uk"}, # British accent
    "masooma": {"lang": "en", "tld": "ca"}, # Canadian accent
    "default": {"lang": "en", "tld": "com"}
}

# =========================================================
# HTML TEMPLATE
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

