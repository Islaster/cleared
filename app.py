import os
import json
import time
import math
import base64
import tempfile
import pandas as pd
from datetime import datetime, date
import streamlit as st
import streamlit.components.v1 as components
from twelvelabs import TwelveLabs

client = TwelveLabs(api_key=os.environ["TWELVELABS_API_KEY"])

# ── PREDEFINED COMPLIANCE RULESETS ───────────────────────────
RULESETS = {
    "Broadcast Standards": {
        "description": "Standard broadcast compliance rules",
        "rules": [
            "No visible alcohol branding in content targeted to audiences under 21",
            "Flag graphic violence or blood in content without proper rating disclosure",
            "No nudity or sexual content without appropriate rating",
            "No profanity or hate speech before watershed (9pm)",
            "No tobacco or drug use without health warning",
            "No dangerous stunts without safety disclaimer",
        ]
    },
    "Brand Guidelines": {
        "description": "Advertising creative brand safety",
        "rules": [
            "Detect unauthorized use of competitor brands or trademarks",
            "No negative portrayal of the brand or its products",
            "Brand logo must appear in final 5 seconds",
            "No association with violence, controversy, or adult content",
            "Talent must be cleared and releases on file",
            "No artwork or music without clearance documentation",
        ]
    },
    "Platform Policies": {
        "description": "YouTube, TikTok, streaming platform requirements",
        "rules": [
            "Identify language that violates platform hate speech policies",
            "No alcohol shown being consumed for TikTok audiences",
            "No graphic violence without age restriction flag",
            "No misinformation or misleading health claims",
            "No copyright music without license verification",
            "Sponsored content must include disclosure",
        ]
    },
    "Custom": {
        "description": "Define your own rules",
        "rules": []
    }
}

JURISDICTIONS = {
    "None": "",
    "OFCOM (UK)": "OFCOM standards: Flag watershed violations (pre-9pm unsuitable content), product placement without disclosure, harmful content, sponsorship identification rules, due impartiality requirements for news content.",
    "FCC (US)": "FCC standards: Flag indecency and profanity (18 USC 1464), unauthorized sponsorship identification, children's TV advertising limits (COPPA), equal time provisions, EAS abuse.",
    "GDPR (EU)": "GDPR: Flag biometric data processing without consent disclosure, facial recognition of identifiable individuals, personal data visible on screen, children's data (under 16) without parental consent.",
    "ARPP (France)": "ARPP: Flag alcohol advertising rules (Loi Evin), food advertising to children, environmental claims without substantiation, tobacco advertising prohibition.",
    "CRTC (Canada)": "CRTC: Flag Canadian content requirements, bilingual obligations, alcohol advertising restrictions, children's programming standards.",
    "Multi-region": "Check against ALL of: OFCOM (UK), FCC (US), GDPR (EU), ARPP (France), CRTC (Canada). Flag anything that would fail in ANY jurisdiction.",
}

PLATFORMS = ["YouTube", "TikTok", "Instagram", "Broadcast pre-watershed",
             "Streaming (Netflix/HBO)", "Roblox", "The Sphere", "Custom"]

AUDIO_FLAGS = [
    "Profanity / cursing",
    "Unlicensed music",
    "Sound effects requiring clearance",
    "Singing / vocal performance",
    "Brand jingles or slogans",
    "Wilhelm scream or stock SFX",
    "Hate speech or slurs",
    "Drug or alcohol references in lyrics",
    "Unauthorized celebrity voice",
]

# ── HELPERS ──────────────────────────────────────────────────
def parse_findings(report):
    import re
    findings = []
    lines = report.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Section 1 style — "Timestamp: [MM:SS-MM:SS]" with description/severity on following lines
        if line.lower().startswith("timestamp:") and "[" in line:
            ts_match = re.search(r'\[[\d:]+(?:-[\d:]+)?\]', line)
            ts_str = ts_match.group(0) if ts_match else ""

            # look back for the category header (last non-empty line before this one)
            category = ""
            for back in range(i - 1, max(i - 5, -1), -1):
                prev = lines[back].strip()
                if prev and not prev.lower().startswith("timestamp"):
                    category = prev
                    break

            description = ""
            severity = ""
            for fwd in range(i + 1, min(i + 8, len(lines))):
                fwd_line = lines[fwd].strip()
                if fwd_line.lower().startswith("description:"):
                    description = fwd_line[len("description:"):].strip()
                elif fwd_line.lower().startswith("severity:"):
                    severity = fwd_line[len("severity:"):].strip()

            parts = [p for p in [ts_str, category, description, severity] if p]
            findings.append(" — ".join(parts))
            i += 1
            continue

        # Section 3 style — "[MM:SS-MM:SS] description — Clearance needed: X"
        if re.match(r'^\[[\d:]+', line):
            findings.append(line)
            i += 1
            continue

        i += 1
    return findings

def severity_score(report):
    score = 0
    score += report.count("CRITICAL") * 10
    score += report.count("MAJOR") * 7
    score += report.count("MINOR") * 3
    return score

def parse_timestamp_seconds(finding):
    import re
    try:
        match = re.search(r'\[(\d+):(\d+)', finding)
        if match:
            return int(match.group(1)) * 60 + int(match.group(2))
    except Exception:
        pass
    return 0

def log_feedback(finding, decision, video_id, ruleset, platforms, jurisdictions):
    log = {
        "timestamp": datetime.now().isoformat(),
        "video_id": video_id,
        "finding": finding,
        "decision": decision,
        "ruleset": ruleset,
        "platforms": platforms,
        "jurisdictions": jurisdictions,
    }
    with open("feedback_log.json", "a") as f:
        f.write(json.dumps(log) + "\n")

def load_feedback_log():
    try:
        with open("feedback_log.json", "r") as f:
            return [json.loads(l) for l in f.readlines()]
    except FileNotFoundError:
        return []

def load_rights_log():
    try:
        with open("rights_log.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_rights_log(entries):
    with open("rights_log.json", "w") as f:
        json.dump(entries, f, indent=2, default=str)

def get_expiring_rights(entries, days_ahead=30):
    today = date.today()
    expiring = []
    for e in entries:
        try:
            exp = date.fromisoformat(e["expiry_date"])
            delta = (exp - today).days
            if delta <= days_ahead:
                e["days_remaining"] = delta
                expiring.append(e)
        except Exception:
            pass
    return expiring

def load_ground_truth():
    try:
        with open("ground_truth.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_ground_truth(data):
    with open("ground_truth.json", "w") as f:
        json.dump(data, f, indent=2)

def compute_metrics(ground_truth_violations, system_findings):
    """Compare ground truth list against system findings list."""
    tp = 0
    fp = 0
    fn = 0
    matched = set()

    for gt in ground_truth_violations:
        gt_lower = gt.lower()
        found = False
        for i, sf in enumerate(system_findings):
            if i not in matched:
                # simple keyword overlap match
                gt_words = set(gt_lower.split())
                sf_words = set(sf.lower().split())
                overlap = gt_words & sf_words
                if len(overlap) >= 2:
                    tp += 1
                    matched.add(i)
                    found = True
                    break
        if not found:
            fn += 1

    fp = len(system_findings) - len(matched)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0

    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
    }

@st.cache_data(ttl=60)
def fetch_indexes():
    try:
        indexes = list(client.indexes.list())
        return [(idx.index_name or idx.id, idx.id) for idx in indexes]
    except Exception:
        return []

@st.cache_data(ttl=60)
def fetch_videos(index_id):
    try:
        videos = list(client.assets.list(index_id=index_id))
        return [
            (v.metadata.filename if hasattr(v, 'metadata') and v.metadata and v.metadata.filename else v.id, v.id)
            for v in videos
        ]
    except Exception:
        try:
            tasks = list(client.tasks.list(index_id=index_id))
            return [(t.video_id, t.video_id) for t in tasks if t.status == "ready"]
        except Exception:
            return []

@st.cache_data(ttl=3600)
def fetch_video_url(video_id, index_id):
    try:
        video = client.indexes.videos.retrieve(index_id, video_id)
        return video.hls.video_url
    except Exception:
        return None

def build_prompt(ruleset_name, custom_rules, platforms, jurisdictions, audio_flags, include_rights):
    rules_list = list(RULESETS[ruleset_name]["rules"]) if ruleset_name != "Custom" else []
    if custom_rules:
        for r in custom_rules.split("\n"):
            if r.strip():
                rules_list.append(r.strip())

    rules_text = "\n".join(f"- {r}" for r in rules_list)
    platforms_text = ", ".join(platforms)

    jurisdiction_blocks = []
    for j in jurisdictions:
        if j != "None" and JURISDICTIONS.get(j):
            jurisdiction_blocks.append(f"{j}: {JURISDICTIONS[j]}")
    jurisdiction_text = "\n".join(jurisdiction_blocks) if jurisdiction_blocks else "No specific jurisdiction selected."

    audio_text = "\n".join(f"- {a}" for a in audio_flags) if audio_flags else "- General audio compliance check"

    rights_section = """
SECTION 3 - RIGHTS & CLEARANCES
Identify ALL of the following requiring clearance:
- On-screen artworks, paintings, sculptures, installations
- Brand logos, trademarks, product packaging
- Identifiable talent (faces visible, recognizable)
- Background music, sound effects, jingles
- Architectural works, set designs
- News footage, archival material
Format: [timestamp] [asset type] [description] [clearance needed: YES/MAYBE/NO]
""" if include_rights else ""

    return f"""
You are a senior compliance reviewer conducting a full regulatory clearance review.

TARGET PLATFORMS: {platforms_text}

COMPLIANCE RULESET ({ruleset_name}):
{rules_text}

AUDIO FLAGS TO CHECK:
{audio_text}

Produce a structured compliance report:

SECTION 1 - CONTENT FLAGS
Check for: alcohol, drugs, violence, minors, abuse, hate speech, vaping, tobacco, dangerous activities.
For each finding:
- Exact timestamp [MM:SS-MM:SS]
- Precise description of what was detected
- Which rule it violates
- Severity: CRITICAL / MAJOR / MINOR
- Recommended action
If nothing found in a category, state: NOT DETECTED.

SECTION 2 - AUDIO FLAGS
Check for: {', '.join(audio_flags) if audio_flags else 'general audio compliance'}
For each finding:
- Timestamp [MM:SS-MM:SS]
- Description of audio content
- Whether clearance or censorship is required
- Severity: CRITICAL / MAJOR / MINOR

{rights_section}

SECTION 4 - PLATFORM SUITABILITY
For each platform in [{platforms_text}]:
Format: [platform]: [APPROVED / FLAGGED / REJECTED] — [one sentence reason] [timestamps if relevant]

SECTION 5 - REGULATORY REVIEW
{jurisdiction_text}
For each jurisdiction: [COMPLIANT / FLAG] — [specific rule] — [evidence]

SECTION 6 - OVERALL RECOMMENDATION
APPROVED FOR DISTRIBUTION / NEEDS REVIEW / REJECTED
Risk level: CRITICAL / HIGH / MEDIUM / LOW
One paragraph summary written for a client.
"""

# ── VIDEO PLAYER COMPONENT ───────────────────────────────────
def video_player(video_url: str, seek_to: float = 0, findings: list = None):
    markers_js = ""
    if findings:
        for i, f in enumerate(findings):
            ts = parse_timestamp_seconds(f)
            severity = "CRITICAL" if "CRITICAL" in f else "MAJOR" if "MAJOR" in f else "MINOR"
            color = "#ff3232" if severity == "CRITICAL" else "#ff69b4" if severity == "MAJOR" else "#ffdfba"
            markers_js += f'addMarker({ts}, "{color}", "{f[:60].replace(chr(34), "")}");'

    findings_data = json.dumps([
        (parse_timestamp_seconds(f), f[:50],
         "critical" if "CRITICAL" in f else "major" if "MAJOR" in f else "minor")
        for f in (findings or [])
    ])

    components.html(f"""
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap');
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        html, body {{
            background: #0a0a0a;
            font-family: 'Space Mono', monospace;
            overflow: hidden;
            height: 100%;
        }}

        .outer-wrap {{
            display: flex;
            height: 100%;
            background: #0a0a0a;
        }}

        /* ── left: video + scrubber + timecode ── */
        .video-side {{
            flex: 1;
            min-width: 0;
            display: flex;
            flex-direction: column;
            background: #000;
        }}

        video {{
            width: 100%;
            flex: 1;
            min-height: 0;
            background: #000;
            display: block;
        }}

        .timeline-wrap {{
            position: relative;
            height: 4px;
            background: #1a1a1a;
            cursor: pointer;
            flex-shrink: 0;
        }}

        .timeline-progress {{
            position: absolute;
            top: 0; left: 0;
            height: 100%;
            background: #ff69b4;
            pointer-events: none;
            transition: width 0.1s linear;
        }}

        .timeline-marker {{
            position: absolute;
            top: -4px;
            width: 3px;
            height: 12px;
            border-radius: 1px;
            cursor: pointer;
        }}

        .timeline-marker:hover {{ opacity: 0.7; }}

        .marker-tooltip {{
            display: none;
            position: absolute;
            bottom: 18px;
            left: 50%;
            transform: translateX(-50%);
            background: #111;
            border: 1px solid #333;
            border-radius: 2px;
            padding: 0.25rem 0.5rem;
            font-size: 0.58rem;
            color: #ccc;
            white-space: normal;
            width: 160px;
            z-index: 10;
        }}

        .timeline-marker:hover .marker-tooltip {{ display: block; }}

        .controls-row {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.4rem 0.75rem;
            background: #0a0a0a;
            border-top: 1px solid #1a1a1a;
            flex-shrink: 0;
        }}

        .timecode {{
            font-size: 0.6rem;
            color: #555;
            letter-spacing: 0.1em;
            white-space: nowrap;
        }}

        /* ── right: violation badges panel ── */
        .seekbar-panel {{
            width: 210px;
            flex-shrink: 0;
            display: flex;
            flex-direction: column;
            background: #080808;
            border-left: 1px solid #141414;
            overflow: hidden;
        }}

        .panel-label {{
            font-size: 0.52rem;
            letter-spacing: 0.28em;
            text-transform: uppercase;
            color: #333;
            padding: 0.55rem 0.75rem 0.4rem;
            border-bottom: 1px solid #111;
            flex-shrink: 0;
        }}

        .seekbar-wrap {{
            flex: 1;
            overflow-y: auto;
            padding: 0.4rem 0.5rem;
            display: flex;
            flex-direction: column;
            gap: 0.28rem;
        }}

        .seekbar-wrap::-webkit-scrollbar {{ width: 3px; }}
        .seekbar-wrap::-webkit-scrollbar-track {{ background: #0a0a0a; }}
        .seekbar-wrap::-webkit-scrollbar-thumb {{ background: #222; border-radius: 2px; }}

        .seek-badge {{
            background: transparent;
            border-radius: 2px;
            padding: 0.28rem 0.55rem;
            font-size: 0.55rem;
            cursor: pointer;
            letter-spacing: 0.06em;
            font-family: 'Space Mono', monospace;
            transition: all 0.12s;
            white-space: normal;
            text-align: left;
            line-height: 1.4;
            width: 100%;
        }}

        .seek-badge.critical {{
            border: 1px solid #ff3232; color: #ff3232;
        }}
        .seek-badge.critical:hover {{ background: rgba(255,50,50,0.12); }}

        .seek-badge.major {{
            border: 1px solid #ff69b4; color: #ff69b4;
        }}
        .seek-badge.major:hover {{ background: rgba(255,105,180,0.12); }}

        .seek-badge.minor {{
            border: 1px solid #64b5f6; color: #64b5f6;
        }}
        .seek-badge.minor:hover {{ background: rgba(100,181,246,0.12); }}

        .no-findings {{
            font-size: 0.55rem;
            color: #2a2a2a;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            padding: 0.75rem 0.5rem;
        }}
    </style>

    <div class="outer-wrap">

        <!-- left: video -->
        <div class="video-side">
            <video id="clearedplayer" controls preload="metadata"></video>

            <div class="timeline-wrap" id="timeline" onclick="timelineClick(event)">
                <div class="timeline-progress" id="progress"></div>
            </div>

            <div class="controls-row">
                <span class="timecode" id="current-time">0:00</span>
                <span class="timecode">/</span>
                <span class="timecode" id="dur">--:--</span>
                {"<span class='timecode' style='color:#ff69b4;margin-left:auto'>⏱ " + str(int(seek_to)) + "s</span>" if seek_to > 0 else ""}
            </div>
        </div>

        <!-- right: violations -->
        <div class="seekbar-panel">
            <div class="panel-label">violations</div>
            <div class="seekbar-wrap" id="seekbar">
                <span class="no-findings" id="no-findings-msg">run check to see findings</span>
            </div>
        </div>

    </div>

    <script>
        const video = document.getElementById('clearedplayer');
        const progress = document.getElementById('progress');
        const timeline = document.getElementById('timeline');
        const seekbar = document.getElementById('seekbar');
        const videoSrc = "{video_url}";
        let duration = 0;

        function fmt(s) {{
            const m = Math.floor(s / 60);
            const sec = Math.floor(s % 60);
            return m + ':' + (sec < 10 ? '0' : '') + sec;
        }}

        function onReady() {{
            duration = video.duration;
            document.getElementById('dur').textContent = fmt(duration);
            {markers_js}
            video.currentTime = {seek_to};
            {"video.play();" if seek_to > 0 else ""}
        }}

        if (typeof Hls !== 'undefined' && Hls.isSupported() && videoSrc.includes('.m3u8')) {{
            const hls = new Hls();
            hls.loadSource(videoSrc);
            hls.attachMedia(video);
            hls.on(Hls.Events.MANIFEST_PARSED, onReady);
        }} else {{
            video.src = videoSrc;
            video.addEventListener('loadedmetadata', onReady);
        }}

        video.addEventListener('timeupdate', function() {{
            if (duration > 0) {{
                progress.style.width = (video.currentTime / duration * 100) + '%';
                document.getElementById('current-time').textContent = fmt(video.currentTime);
            }}
        }});

        function timelineClick(e) {{
            if (duration === 0) return;
            const rect = timeline.getBoundingClientRect();
            video.currentTime = ((e.clientX - rect.left) / rect.width) * duration;
            video.play();
        }}

        function addMarker(seconds, color, label) {{
            if (duration === 0) return;
            const pct = (seconds / duration) * 100;
            const marker = document.createElement('div');
            marker.className = 'timeline-marker';
            marker.style.left = pct + '%';
            marker.style.background = color;
            const tip = document.createElement('div');
            tip.className = 'marker-tooltip';
            tip.textContent = fmt(seconds) + ' — ' + label;
            marker.appendChild(tip);
            marker.onclick = function(e) {{
                e.stopPropagation();
                video.currentTime = seconds;
                video.play();
            }};
            timeline.appendChild(marker);
        }}

        const findings = {findings_data};
        if (findings.length > 0) {{
            const msg = document.getElementById('no-findings-msg');
            if (msg) msg.remove();
            findings.forEach(function(f) {{
                const btn = document.createElement('button');
                btn.className = 'seek-badge ' + f[2];
                btn.textContent = fmt(f[0]) + '  ' + f[1].substring(0, 40) + (f[1].length > 40 ? '…' : '');
                btn.onclick = function() {{
                    video.currentTime = f[0];
                    video.play();
                }};
                seekbar.appendChild(btn);
            }});
        }}
    </script>
    """, height=460)

# ── PAGE CONFIG ──────────────────────────────────────────────
st.set_page_config(page_title="Cleared", layout="wide", page_icon="✦")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Playfair+Display:ital,wght@0,700;1,400&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Mono', monospace;
    background-color: #0a0a0a;
    color: #f0f0f0;
}
.stApp { background-color: #0a0a0a; }

h1 {
    font-family: 'Playfair Display', serif !important;
    font-style: italic !important;
    color: #ff69b4 !important;
    font-size: 3rem !important;
    letter-spacing: 0.05em;
    text-shadow: 0 0 40px rgba(255,105,180,0.5), 0 0 80px rgba(255,105,180,0.2);
    margin-bottom: 0 !important;
}
h2 {
    font-family: 'Space Mono', monospace !important;
    color: #64b5f6 !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    font-weight: 400 !important;
}
h3 {
    font-family: 'Space Mono', monospace !important;
    color: #ce93d8 !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.2em;
    text-transform: uppercase;
}

/* ── SIDEBAR ── */
section[data-testid="stSidebar"] {
    background: #080808 !important;
    border-right: 1px solid #1a1a1a !important;
}
section[data-testid="stSidebar"] .stMarkdown p {
    color: #555 !important;
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
}
section[data-testid="stSidebar"] label {
    color: #555 !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}

/* ── INPUTS ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #111 !important;
    border: 1px solid #222 !important;
    color: #f0f0f0 !important;
    border-radius: 2px !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.8rem !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #ff69b4 !important;
    box-shadow: 0 0 0 1px #ff69b4 !important;
}
.stSelectbox > div > div, .stMultiSelect > div > div {
    background: #0d0d0d !important;
    border: 1px solid #222 !important;
    color: #f0f0f0 !important;
    border-radius: 2px !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.75rem !important;
}

/* ── MULTISELECT TAGS — cycle pink / blue / green ── */
.stMultiSelect span[data-baseweb="tag"] {
    background: rgba(255,105,180,0.12) !important;
    border: 1px solid #ff69b4 !important;
    border-radius: 2px !important;
    color: #ff69b4 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.6rem !important;
}
.stMultiSelect span[data-baseweb="tag"]:nth-child(3n+2) {
    background: rgba(100,181,246,0.12) !important;
    border-color: #64b5f6 !important;
    color: #64b5f6 !important;
}
.stMultiSelect span[data-baseweb="tag"]:nth-child(3n+3) {
    background: rgba(0,255,136,0.10) !important;
    border-color: #00ff88 !important;
    color: #00ff88 !important;
}
.stMultiSelect span[data-baseweb="tag"] span[role="presentation"] { color: inherit !important; }

/* ── BUTTONS ── */
.stButton > button {
    background: transparent !important;
    color: #ff69b4 !important;
    border: 1px solid #ff69b4 !important;
    border-radius: 2px !important;
    font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    transition: all 0.15s ease !important;
}
.stButton > button:hover {
    background: rgba(255,105,180,0.12) !important;
    box-shadow: 0 0 16px rgba(255,105,180,0.4) !important;
    transform: translateY(-1px) !important;
}
/* run button — filled */
.stButton > button[kind="primary"], section[data-testid="stSidebar"] .stButton > button {
    background: #ff69b4 !important;
    color: #0a0a0a !important;
    border-color: #ff69b4 !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: #ff85c2 !important;
    box-shadow: 0 0 20px rgba(255,105,180,0.5) !important;
}

/* ── TABS — sticky below Streamlit's 44px toolbar ── */
.stTabs [data-baseweb="tab-list"] {
    position: sticky !important;
    top: 44px !important;
    z-index: 998 !important;
    background: #0a0a0a !important;
    border-bottom: 1px solid #1a1a1a !important;
    gap: 0 !important;
    padding-top: 2px !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #333 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.6rem !important;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    border-bottom: 2px solid transparent !important;
    padding: 0.5rem 1.25rem !important;
    transition: color 0.15s !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #ce93d8 !important; }
.stTabs [aria-selected="true"] {
    color: #ff69b4 !important;
    border-bottom: 2px solid #ff69b4 !important;
}

/* ── ALERTS ── */
.stSuccess > div { background: rgba(0,255,136,0.05) !important; border: 1px solid #00ff88 !important; border-radius: 2px !important; color: #00ff88 !important; }
.stError > div { background: rgba(255,50,50,0.06) !important; border: 1px solid #ff3232 !important; border-radius: 2px !important; color: #ff6464 !important; }
.stWarning > div { background: rgba(255,223,186,0.06) !important; border: 1px solid #ffdfba !important; border-radius: 2px !important; color: #ffdfba !important; }
.stInfo > div { background: rgba(100,181,246,0.06) !important; border: 1px solid #64b5f6 !important; border-radius: 2px !important; color: #64b5f6 !important; }
/* ── SPINNER — rotating disc (inline st.spinner) ── */
.stSpinner > div {
    border: 3px solid #1a1a1a !important;
    border-top-color: #ff69b4 !important;
    border-right-color: #64b5f6 !important;
    border-bottom-color: #00ff88 !important;
    border-left-color: #ce93d8 !important;
    border-radius: 50% !important;
    width: 28px !important;
    height: 28px !important;
    animation: cleared-spin 0.75s linear infinite !important;
}
.stSpinner > div > * { display: none !important; }

/* ── GLOBAL RUNNING INDICATOR (top-right dude) ── */
[data-testid="stStatusWidget"] { opacity: 1 !important; }
[data-testid="stStatusWidget"] svg { display: none !important; }
[data-testid="stStatusWidget"]::before {
    content: '' !important;
    display: inline-block !important;
    width: 16px !important;
    height: 16px !important;
    border-radius: 50% !important;
    border: 2px solid transparent !important;
    border-top-color: #ff69b4 !important;
    border-right-color: #64b5f6 !important;
    border-bottom-color: #00ff88 !important;
    border-left-color: #ce93d8 !important;
    animation: cleared-spin 0.75s linear infinite !important;
    vertical-align: middle !important;
}
@keyframes cleared-spin { to { transform: rotate(360deg); } }

/* ── REDUCE IFRAME / TAB GAP ── */
[data-testid="stCustomComponentV1"] {
    margin-bottom: -2rem !important;
    padding-bottom: 0 !important;
    line-height: 0 !important;
}
iframe { display: block !important; margin-bottom: 0 !important; }
.stTabs { margin-top: 0 !important; }
/* kill the element-container padding around the iframe */
[data-testid="stCustomComponentV1"] > div { padding-bottom: 0 !important; }

/* ── HIDE MULTISELECT "NO RESULTS" BUBBLE ── */
[data-baseweb="no-results"] { display: none !important; }
ul[data-baseweb="menu"] li:only-child[aria-disabled="true"] { display: none !important; }
.stCaption { color: #444 !important; font-size: 0.65rem !important; letter-spacing: 0.1em; }
.stMarkdown p { color: #ccc; font-size: 0.85rem; line-height: 1.8; }
.stDownloadButton > button { background: transparent !important; border: 1px solid #222 !important; color: #555 !important; font-family: 'Space Mono', monospace !important; font-size: 0.65rem !important; letter-spacing: 0.15em; text-transform: uppercase; border-radius: 2px !important; }
.stDownloadButton > button:hover { border-color: #00ff88 !important; color: #00ff88 !important; }
hr { border-color: #1a1a1a !important; margin: 1rem 0 !important; }
.stCheckbox label { color: #aaa !important; font-size: 0.75rem !important; }

/* ── RISK BANNERS ── */
.risk-critical { background: rgba(255,50,50,0.08); border: 1px solid #ff3232; border-left: 3px solid #ff3232; border-radius: 2px; padding: 0.6rem 1.25rem; color: #ff6464; font-size: 0.65rem; letter-spacing: 0.25em; text-transform: uppercase; margin-bottom: 1rem; }
.risk-high { background: rgba(255,105,180,0.07); border: 1px solid #ff69b4; border-left: 3px solid #ff69b4; border-radius: 2px; padding: 0.6rem 1.25rem; color: #ff69b4; font-size: 0.65rem; letter-spacing: 0.25em; text-transform: uppercase; margin-bottom: 1rem; }
.risk-medium { background: rgba(100,181,246,0.07); border: 1px solid #64b5f6; border-left: 3px solid #64b5f6; border-radius: 2px; padding: 0.6rem 1.25rem; color: #64b5f6; font-size: 0.65rem; letter-spacing: 0.25em; text-transform: uppercase; margin-bottom: 1rem; }
.risk-low { background: rgba(0,255,136,0.06); border: 1px solid #00ff88; border-left: 3px solid #00ff88; border-radius: 2px; padding: 0.6rem 1.25rem; color: #00ff88; font-size: 0.65rem; letter-spacing: 0.25em; text-transform: uppercase; margin-bottom: 1rem; }

/* ── FINDING CARDS ── */
.finding-card { background: #0d0d0d; border: 1px solid #1a1a1a; border-radius: 2px; padding: 0.75rem 1rem; margin-bottom: 0.5rem; font-size: 0.78rem; color: #ccc; line-height: 1.6; }
.finding-critical { border-left: 3px solid #ff3232; }
.finding-major { border-left: 3px solid #ff69b4; }
.finding-minor { border-left: 3px solid #64b5f6; }

/* ── META ── */
.meta-label { font-size: 0.6rem; letter-spacing: 0.25em; text-transform: uppercase; color: #333; margin-bottom: 0.2rem; }
.meta-value-pink { color: #ff69b4; font-size: 0.9rem; }
.meta-value-lavender { color: #ce93d8; font-size: 0.9rem; }
.meta-value-mint { color: #00ff88; font-size: 0.9rem; }
.meta-value-peach { color: #64b5f6; font-size: 0.9rem; }

/* ── LTX / RIGHTS / METRICS ── */
.ltx-panel { background: #0d0d0d; border: 1px solid #2a1a3a; border-radius: 4px; padding: 1rem 1.25rem; margin-top: 0.75rem; }
.ltx-option { background: #111; border: 1px solid #2a2a2a; border-radius: 2px; padding: 0.5rem 0.75rem; margin-bottom: 0.4rem; font-size: 0.72rem; color: #ccc; }
.rights-expiring { background: rgba(255,105,180,0.07); border: 1px solid #ff69b4; border-radius: 2px; padding: 0.5rem 0.75rem; margin-bottom: 0.4rem; font-size: 0.72rem; color: #ff69b4; }
.rights-ok { background: rgba(0,255,136,0.04); border: 1px solid #1a3a2a; border-radius: 2px; padding: 0.5rem 0.75rem; margin-bottom: 0.4rem; font-size: 0.72rem; color: #444; }
.metric-card { background: #0d0d0d; border: 1px solid #1a1a1a; border-radius: 4px; padding: 1rem; text-align: center; }
.metric-number { font-size: 2rem; font-weight: 700; font-family: 'Space Mono', monospace; }
.metric-label { font-size: 0.6rem; letter-spacing: 0.2em; text-transform: uppercase; color: #444; margin-top: 0.25rem; }
.section-divider { border: none; border-top: 1px solid #111; margin: 0.75rem 0; }

/* ── CLEARED LOGO ── */
.cleared-logo {
    font-family: 'Playfair Display', serif;
    font-style: italic;
    color: #ff69b4;
    font-size: 1.5rem;
    letter-spacing: 0.05em;
    text-shadow: 0 0 30px rgba(255,105,180,0.6), 0 0 60px rgba(255,105,180,0.2);
    line-height: 1;
    display: inline-block;
}
.cleared-subhead {
    font-family: 'Space Mono', monospace;
    color: #64b5f6;
    font-size: 0.55rem;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    margin-left: 0.75rem;
    vertical-align: middle;
    opacity: 0.7;
}
</style>
""", unsafe_allow_html=True)


# ── HARDCODED VIDEO ───────────────────────────────────────────
DEMO_VIDEO_ID = "69bf04be251dc4f29f376218"
DEMO_INDEX_ID = "69bf0452a434aab7c15a12b4"
DEMO_VIDEO_LABEL = "compliance-practice-10"
DEMO_VIDEO_FILENAME = "compliance-practice-10.mp4"
DEMO_VIDEO_PORT = "8502"

# ── SIDEBAR ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="padding:0.6rem 0 0.75rem 0;border-bottom:1px solid #1a1a1a;margin-bottom:0.75rem;">'
        '<span style="font-family:\'Playfair Display\',serif;font-style:italic;color:#ff69b4;font-size:1.4rem;'
        'text-shadow:0 0 24px rgba(255,105,180,0.6);letter-spacing:0.05em;line-height:1;">Cleared</span>'
        '</div>',
        unsafe_allow_html=True
    )
    run = st.button("⚡ run compliance check", width='stretch')
    st.markdown("---")
    st.markdown("### ✦ Video")
    video_source = st.radio("source", ["Select from TwelveLabs", "Upload video"], label_visibility="collapsed")

    if video_source == "Upload video":
        st.file_uploader("upload video", type=["mp4", "mov", "avi", "webm"], label_visibility="collapsed")
        st.caption(f"using: {DEMO_VIDEO_LABEL}")
    else:
        st.caption(f"✦ {DEMO_VIDEO_LABEL}")

    selected_video_id = DEMO_VIDEO_ID
    selected_video_label = DEMO_VIDEO_LABEL

    st.markdown("### ✦ Platforms")
    selected_platforms = st.multiselect("platforms", PLATFORMS, default=[], label_visibility="collapsed")

    st.markdown("### ✦ Jurisdictions")
    selected_jurisdictions = st.multiselect("jurisdictions", list(JURISDICTIONS.keys()), default=[], label_visibility="collapsed")


# ── HARDCODED CONFIG ──────────────────────────────────────────
ruleset_name = "Broadcast Standards"
custom_rules = ""
include_rights = True
selected_audio = AUDIO_FLAGS

# ── THEATER PLAYER ────────────────────────────────────────────
_tv_url = fetch_video_url(DEMO_VIDEO_ID, DEMO_INDEX_ID)
if _tv_url:
    video_player(
        _tv_url,
        seek_to=st.session_state.get("seek_to", 0),
        findings=st.session_state.get("findings", []),
    )
else:
    st.warning("could not load video stream")


# ── RUN ───────────────────────────────────────────────────────
_overlay_ph = st.empty()

if run:
    if not selected_platforms:
        st.error("select at least one platform")
    else:
        _overlay_ph.markdown("""
<div style="position:fixed;inset:0;background:rgba(10,10,10,0.88);z-index:9999;
     display:flex;flex-direction:column;align-items:center;justify-content:center;
     backdrop-filter:blur(4px);">
  <div style="width:72px;height:72px;border-radius:50%;
       border:5px solid #111;
       border-top-color:#ff69b4;
       border-right-color:#64b5f6;
       border-bottom-color:#00ff88;
       border-left-color:#ce93d8;
       animation:cleared-spin 0.75s linear infinite;">
  </div>
  <div style="color:#ff69b4;font-family:'Space Mono',monospace;font-size:0.72rem;
       letter-spacing:0.35em;text-transform:uppercase;margin-top:1.75rem;
       text-shadow:0 0 20px rgba(255,105,180,0.6);">
    analyzing with pegasus
  </div>
  <div style="color:#555;font-family:'Space Mono',monospace;font-size:0.6rem;
       letter-spacing:0.2em;margin-top:0.5rem;">
    this may take a minute
  </div>
</div>
<style>@keyframes cleared-spin {{ to {{ transform: rotate(360deg); }} }}</style>
""", unsafe_allow_html=True)
        prompt = build_prompt(ruleset_name, custom_rules, selected_platforms, selected_jurisdictions, selected_audio, include_rights)
        response = client.analyze(video_id=selected_video_id, prompt=prompt)
        st.session_state.report = response.data
        st.session_state.findings = parse_findings(response.data)
        st.session_state.video_id = selected_video_id
        st.session_state.video_label = selected_video_label
        st.session_state.risk_score = severity_score(response.data)
        st.session_state.platforms = selected_platforms
        st.session_state.jurisdictions = selected_jurisdictions
        st.session_state.ruleset = ruleset_name
        st.session_state.run_time = datetime.now().isoformat()
        st.session_state.seek_to = 0
        _overlay_ph.empty()

# ── RESULTS ───────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "report", "review findings", "accuracy metrics", "export & audit", "rights tracker", "learning"
])

# ── TAB 1: REPORT ─────────────────────────────────────────
with tab1:
    if "report" not in st.session_state:
        st.caption("run a compliance check to see the report")
    else:
        score = st.session_state.risk_score
        if score >= 20:
            st.markdown(f'<div class="risk-critical">⛔ critical risk · score {score} / 30 · immediate action required</div>', unsafe_allow_html=True)
        elif score >= 15:
            st.markdown(f'<div class="risk-high">⚠ high risk · score {score} / 30</div>', unsafe_allow_html=True)
        elif score >= 7:
            st.markdown(f'<div class="risk-medium">⚡ medium risk · score {score} / 30</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="risk-low">✓ low risk · score {score} / 30</div>', unsafe_allow_html=True)
        st.markdown(f"*{st.session_state.get('run_time','—')} · {st.session_state.get('ruleset','—')} · {st.session_state.get('video_label','')}*")
        st.markdown("---")
        st.markdown(st.session_state.report)

# ── TAB 2: REVIEW FINDINGS ────────────────────────────────
with tab2:
    if "report" not in st.session_state:
        st.caption("run a compliance check to see findings")
    else:
        findings = st.session_state.findings

        st.caption("review each finding · click timestamp to seek · decisions logged for learning")

        if not findings:
            st.info("no timestamped findings — see full report")
        else:
            for i, finding in enumerate(findings):
                card_class = "finding-card"
                if "CRITICAL" in finding:
                    card_class += " finding-critical"
                elif "MAJOR" in finding:
                    card_class += " finding-major"
                else:
                    card_class += " finding-minor"

                ts_sec = parse_timestamp_seconds(finding)

                with st.container():
                    st.markdown(f'<div class="{card_class}">{finding}</div>', unsafe_allow_html=True)

                    col_seek, col_a, col_r, col_e = st.columns([2, 1, 1, 1])

                    if col_seek.button(f"⏱ seek {ts_sec}s", key=f"seek_{i}"):
                        st.session_state.seek_to = ts_sec
                        st.rerun()

                    if col_a.button("✓ approve", key=f"a_{i}"):
                        log_feedback(finding, "approved", st.session_state.video_id, st.session_state.ruleset, st.session_state.platforms, st.session_state.jurisdictions)
                        st.success("logged: approved")

                    if col_r.button("✗ reject", key=f"r_{i}"):
                        log_feedback(finding, "rejected", st.session_state.video_id, st.session_state.ruleset, st.session_state.platforms, st.session_state.jurisdictions)
                        st.error("logged: rejected")

                    if col_e.button("⚠ escalate", key=f"e_{i}"):
                        log_feedback(finding, "escalated", st.session_state.video_id, st.session_state.ruleset, st.session_state.platforms, st.session_state.jurisdictions)
                        st.warning("logged: escalated")

                    # LTX PANEL (always shown)
                    st.markdown('<div class="ltx-panel">', unsafe_allow_html=True)
                    st.markdown(f"<p style='color:#ce93d8;font-size:0.7rem;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:0.75rem'>✦ LTX Remediation</p>", unsafe_allow_html=True)
                    st.markdown(f"<p style='color:#888;font-size:0.72rem;margin-bottom:0.75rem'>{finding[:80]}...</p>", unsafe_allow_html=True)

                    v_lower = finding.lower()
                    if "alcohol" in v_lower or "drink" in v_lower or "beer" in v_lower or "wine" in v_lower:
                        options = [
                            "Person holding a glass of sparkling water, elegant setting, same lighting and mood as original shot",
                            "Person holding a coffee cup in conversation, warm interior light, matching the scene context",
                            "Close-up of hands on a table, no beverage visible, neutral and clean",
                            "Person gesturing while talking, beverage completely removed from frame",
                        ]
                    elif "vap" in v_lower or "smok" in v_lower or "inhaler" in v_lower:
                        options = [
                            "Person exhaling slowly, misty breath in cool air, no device present",
                            "Person pausing thoughtfully, hands at sides, same background and framing",
                            "Cutaway to product or environment, person not in frame",
                            "Person sipping from a water bottle instead, same pacing and energy",
                        ]
                    elif "logo" in v_lower or "brand" in v_lower or "trademark" in v_lower or "sign" in v_lower:
                        options = [
                            "Same scene composition with brand signage digitally replaced with neutral text",
                            "Slightly reframed angle that naturally avoids the branded element",
                            "Soft-focus background that obscures the logo while keeping subject sharp",
                            "Wide establishing shot that repositions the branded element outside frame",
                        ]
                    elif "minor" in v_lower or "child" in v_lower:
                        options = [
                            "Same scene with adult stand-in, matching clothing and body language",
                            "Shot reframed to exclude individuals under 18",
                            "Cutaway to object or environment that carries same narrative meaning",
                            "Animation or illustration replacing the live-action element entirely",
                        ]
                    else:
                        options = [
                            "Alternative shot of same scene without the flagged element, matching color grade",
                            "Cutaway to a neutral establishing shot maintaining scene continuity",
                            "Close-up on different subject in same environment, same duration",
                            "Wide shot pulling back to naturally exclude the violation from frame",
                        ]

                    st.markdown("<p style='font-size:0.62rem;color:#666;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:0.6rem'>select replacement clip to generate:</p>", unsafe_allow_html=True)

                    _thumb_schemes = [
                        ("135deg, #1a0828 0%, #2d1050 60%, #080510 100%", "#ce93d8", "OPTION 1"),
                        ("135deg, #081828 0%, #0d2a4a 60%, #050a10 100%", "#64b5f6", "OPTION 2"),
                        ("135deg, #1a0808 0%, #3a1010 60%, #0a0505 100%", "#ef9a9a", "OPTION 3"),
                        ("135deg, #081a08 0%, #103a10 60%, #050a05 100%", "#a5d6a7", "OPTION 4"),
                    ]
                    _tcols = st.columns(2)
                    for j, opt in enumerate(options):
                        _grad, _accent, _label = _thumb_schemes[j % len(_thumb_schemes)]
                        with _tcols[j % 2]:
                            st.markdown(f"""
<div style="position:relative;width:100%;padding-bottom:56.25%;background:linear-gradient({_grad});border:1px solid #222;border-radius:2px;overflow:hidden;margin-bottom:0.35rem;">
  <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;">
    <div style="width:32px;height:32px;border-radius:50%;border:2px solid {_accent};display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.4);">
      <div style="width:0;height:0;border-top:7px solid transparent;border-bottom:7px solid transparent;border-left:12px solid {_accent};margin-left:2px;"></div>
    </div>
  </div>
  <div style="position:absolute;top:5px;left:7px;font-size:0.5rem;color:{_accent};letter-spacing:0.18em;font-family:monospace;opacity:0.8;">{_label}</div>
  <div style="position:absolute;bottom:0;left:0;right:0;background:linear-gradient(transparent,rgba(0,0,0,0.7));padding:0.3rem 0.5rem;">
    <div style="font-size:0.55rem;color:#aaa;line-height:1.3;">{opt[:55]}{"…" if len(opt)>55 else ""}</div>
  </div>
</div>""", unsafe_allow_html=True)
                            if st.button("generate", key=f"ltx_use_{i}_{j}", width='stretch'):
                                st.session_state[f"ltx_selected_{i}"] = opt
                                st.success(f"Queued: {opt[:60]}...")

                    if st.session_state.get(f"ltx_selected_{i}"):
                        st.markdown(f"<p style='color:#baffc9;font-size:0.7rem;margin-top:0.5rem'>✓ Queued: {st.session_state[f'ltx_selected_{i}'][:80]}...</p>", unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

# ── TAB 3: ACCURACY METRICS ───────────────────────────────
with tab3:
    st.markdown("### ✦ Accuracy Metrics")
    st.caption("enter ground truth violations to compute precision, recall, and F1 per ruleset")

    gt_data = load_ground_truth()
    video_key = st.session_state.get("video_id", "unknown")
    current_ruleset = st.session_state.get("ruleset", ruleset_name)

    st.markdown("#### Ground Truth Entry")
    st.caption("watch the video manually and list every real violation you see — one per line. this becomes your baseline.")

    gt_key = f"{video_key}__{current_ruleset}"
    existing_gt = "\n".join(gt_data.get(gt_key, {}).get("violations", []))

    gt_input = st.text_area(
        f"Ground truth violations for: {current_ruleset}",
        value=existing_gt,
        height=160,
        placeholder="e.g.\n[00:37] Man drinking from bottle — alcohol consumption\n[00:49] Woman using inhaler-like device — possible drug reference\n[00:25] XINU brand logo visible — requires clearance"
    )

    col_save, col_clear = st.columns([2, 1])
    if col_save.button("save ground truth"):
        if gt_key not in gt_data:
            gt_data[gt_key] = {}
        gt_data[gt_key]["violations"] = [l.strip() for l in gt_input.split("\n") if l.strip()]
        gt_data[gt_key]["video_id"] = video_key
        gt_data[gt_key]["ruleset"] = current_ruleset
        gt_data[gt_key]["saved_at"] = datetime.now().isoformat()
        save_ground_truth(gt_data)
        st.success(f"saved {len(gt_data[gt_key]['violations'])} ground truth violations")

    if col_clear.button("clear"):
        if gt_key in gt_data:
            del gt_data[gt_key]
            save_ground_truth(gt_data)
            st.rerun()

    st.markdown("---")
    st.markdown("#### Computed Metrics")

    system_findings = st.session_state.get("findings", [])
    gt_violations = gt_data.get(gt_key, {}).get("violations", [])

    if not system_findings:
        st.info("run a compliance check first to generate system findings")
    elif not gt_violations:
        st.info("enter ground truth violations above to compute metrics")
    else:
        metrics = compute_metrics(gt_violations, system_findings)

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        def metric_card(col, value, label, color):
            col.markdown(f'<div class="metric-card"><div class="metric-number" style="color:{color}">{value}</div><div class="metric-label">{label}</div></div>', unsafe_allow_html=True)

        metric_card(m1, metrics["tp"], "true positives", "#baffc9")
        metric_card(m2, metrics["fp"], "false positives", "#ff69b4")
        metric_card(m3, metrics["fn"], "false negatives", "#ffdfba")
        metric_card(m4, f"{metrics['precision']:.0%}", "precision", "#ce93d8")
        metric_card(m5, f"{metrics['recall']:.0%}", "recall", "#bae1ff")
        metric_card(m6, f"{metrics['f1']:.0%}", "f1 score", "#ff69b4")

        st.markdown("---")

        # explanation
        st.markdown(f"""
<p style='font-size:0.8rem;color:#ccc;line-height:1.8'>
<span style='color:#baffc9'>Precision {metrics['precision']:.0%}</span> —
of {metrics['tp'] + metrics['fp']} findings flagged, {metrics['tp']} matched ground truth ({metrics['fp']} false positives)<br>
<span style='color:#bae1ff'>Recall {metrics['recall']:.0%}</span> —
of {metrics['tp'] + metrics['fn']} real violations, {metrics['tp']} were detected ({metrics['fn']} missed)<br>
<span style='color:#ff69b4'>F1 {metrics['f1']:.0%}</span> —
combined score balancing precision and recall
</p>
""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### Per-Ruleset Summary Table")
        st.caption("run checks across multiple rulesets to populate this table")

        # build summary from all saved ground truth entries
        summary_rows = []
        for key, entry in gt_data.items():
            if entry.get("video_id") == video_key:
                rs = entry.get("ruleset", "unknown")
                gt_v = entry.get("violations", [])
                # use current system findings as proxy (in production each ruleset would have its own run)
                m = compute_metrics(gt_v, system_findings)
                summary_rows.append({
                    "Ruleset": rs,
                    "GT Violations": len(gt_v),
                    "System Findings": len(system_findings),
                    "TP": m["tp"], "FP": m["fp"], "FN": m["fn"],
                    "Precision": f"{m['precision']:.0%}",
                    "Recall": f"{m['recall']:.0%}",
                    "F1": f"{m['f1']:.0%}",
                })

        if summary_rows:
            st.dataframe(pd.DataFrame(summary_rows), width='stretch')
            st.download_button(
                "↓ download metrics csv",
                pd.DataFrame(summary_rows).to_csv(index=False),
                "cleared_accuracy_metrics.csv",
                "text/csv"
            )
        else:
            st.caption("save ground truth for multiple rulesets to see comparison table")

        st.markdown("---")
        st.markdown("#### Manual Review Baseline Comparison")
        col_manual, col_auto = st.columns(2)
        manual_time = col_manual.number_input("manual review time (minutes)", min_value=1, value=45)
        auto_time = col_auto.number_input("system analysis time (seconds)", min_value=1, value=25)

        speedup = round((manual_time * 60) / auto_time, 1)
        st.markdown(f"""
<div style='background:#0f0f0f;border:1px solid #1a1a1a;border-radius:4px;padding:1rem;margin-top:0.5rem'>
<p style='color:#ce93d8;font-size:0.65rem;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:0.5rem'>baseline comparison</p>
<p style='color:#ccc;font-size:0.85rem'>Manual review: <span style='color:#ffdfba'>{manual_time} minutes</span> &nbsp;|&nbsp;
System: <span style='color:#baffc9'>{auto_time} seconds</span> &nbsp;|&nbsp;
Speedup: <span style='color:#ff69b4'>{speedup}×</span></p>
<p style='color:#666;font-size:0.72rem;margin-top:0.5rem'>At $150/hr manual review cost: <span style='color:#baffc9'>${round(manual_time/60*150, 2)} saved per video</span></p>
</div>
""", unsafe_allow_html=True)

# ── TAB 4: EXPORT & AUDIT ─────────────────────────────────
with tab4:
    if "report" not in st.session_state:
        st.caption("run a compliance check to enable export")
    else:
        score = st.session_state.risk_score
        st.markdown("### Export")
        findings_data = st.session_state.findings or ["no findings"]
        df = pd.DataFrame(findings_data, columns=["finding"])
        df["video_id"] = st.session_state.video_id
        df["ruleset"] = st.session_state.get("ruleset", "")
        df["platforms"] = ", ".join(st.session_state.get("platforms", []))
        df["jurisdictions"] = ", ".join(st.session_state.get("jurisdictions", []))
        df["risk_score"] = score
        df["run_time"] = st.session_state.get("run_time", "")
        df["exported_at"] = datetime.now().isoformat()

        st.dataframe(df, width='stretch')

        col_csv, col_json, col_otio = st.columns(3)

        with col_csv:
            st.download_button("↓ download csv", df.to_csv(index=False), "cleared_report.csv", "text/csv", width='stretch')

        with col_json:
            audit_json = {
                "report_id": f"cleared_{int(time.time())}",
                "generated_at": datetime.now().isoformat(),
                "video_id": st.session_state.video_id,
                "ruleset": st.session_state.get("ruleset"),
                "platforms": st.session_state.get("platforms"),
                "jurisdictions": st.session_state.get("jurisdictions"),
                "risk_score": score,
                "findings": st.session_state.findings,
                "full_report": st.session_state.report,
            }
            st.download_button("↓ audit json", json.dumps(audit_json, indent=2), "cleared_audit.json", "application/json", width='stretch')

        with col_otio:
            otio_markers = []
            for finding in st.session_state.findings:
                ts = parse_timestamp_seconds(finding)
                severity = "CRITICAL" if "CRITICAL" in finding else "MAJOR" if "MAJOR" in finding else "MINOR"
                otio_markers.append({
                    "OTIO_SCHEMA": "Marker.1",
                    "metadata": {"cleared_compliance": {"finding": finding, "severity": severity, "ruleset": st.session_state.get("ruleset"), "platforms": st.session_state.get("platforms")}},
                    "name": f"COMPLIANCE: {severity}",
                    "color": "RED" if severity == "CRITICAL" else "PINK" if severity == "MAJOR" else "YELLOW",
                    "marked_range": {
                        "OTIO_SCHEMA": "TimeRange.1",
                        "start_time": {"OTIO_SCHEMA": "RationalTime.1", "rate": 24, "value": ts * 24},
                        "duration": {"OTIO_SCHEMA": "RationalTime.1", "rate": 24, "value": 48}
                    },
                    "comment": finding
                })
            otio_export = {"OTIO_SCHEMA": "Timeline.1", "metadata": {"cleared_version": "1.0"}, "name": f"Cleared — {st.session_state.video_id[:12]}", "markers": otio_markers}
            st.download_button("↓ otio markers", json.dumps(otio_export, indent=2), "cleared_markers.otio", "application/json", width='stretch')

        st.caption("OTIO markers import into Premiere Pro, Avid, and DaVinci Resolve via OpenTimelineIO plugin")
        st.markdown("---")
        st.markdown("### Audit Trail")
        logs = load_feedback_log()
        if logs:
            st.dataframe(pd.DataFrame(logs), width='stretch')
            st.download_button("↓ full audit trail", pd.DataFrame(logs).to_csv(index=False), "cleared_audit_trail.csv", "text/csv")
        else:
            st.caption("no reviewer decisions logged yet")

# ── TAB 5: RIGHTS TRACKER ─────────────────────────────────
with tab5:
    rights_entries = load_rights_log()
    expiring = get_expiring_rights(rights_entries, days_ahead=30)
    if expiring:
        for e in expiring:
            days = e.get("days_remaining", "?")
            color = "#ff3232" if isinstance(days, int) and days <= 7 else "#ff69b4"
            st.markdown(f'<div class="rights-expiring" style="border-color:{color};color:{color}"><b>{e.get("asset","")}</b> — expires {e.get("expiry_date","?")} ({days} days) — {e.get("type","")}</div>', unsafe_allow_html=True)

    st.markdown("### Rights Duration Tracker")
    st.caption("track expiry dates for music, talent releases, artwork clearances, and licensed assets")

    with st.expander("+ add rights entry", expanded=False):
        r1, r2, r3, r4 = st.columns(4)
        r_asset = r1.text_input("asset name", placeholder="e.g. Track — Blue World")
        r_type = r2.selectbox("type", ["Music license", "Talent release", "Artwork clearance", "Brand license", "Archive footage", "Other"])
        r_expiry = r3.date_input("expiry date")
        r_notes = r4.text_input("notes", placeholder="licensor, territory...")
        if st.button("add to tracker"):
            entries = load_rights_log()
            entries.append({"asset": r_asset, "type": r_type, "expiry_date": r_expiry.isoformat(), "notes": r_notes, "added_at": datetime.now().isoformat(), "video_id": st.session_state.get("video_id", "")})
            save_rights_log(entries)
            st.success(f"added: {r_asset}")

    entries = rights_entries
    if entries:
        for e in sorted(entries, key=lambda x: x.get("expiry_date", "")):
            try:
                days = (date.fromisoformat(e["expiry_date"]) - date.today()).days
                if days <= 0:
                    css, indicator = "rights-expiring", f"⛔ EXPIRED {abs(days)} days ago"
                    color = "#ff3232"
                elif days <= 7:
                    css, indicator = "rights-expiring", f"⚠ expires in {days} days"
                    color = "#ff69b4"
                elif days <= 30:
                    css, indicator = "rights-expiring", f"⚡ {days} days remaining"
                    color = "#ffdfba"
                else:
                    css, indicator = "rights-ok", f"✓ {days} days remaining"
                    color = "#888"
            except Exception:
                css, indicator, color = "rights-ok", "date unknown", "#888"
            st.markdown(f'<div class="{css}" style="border-color:{color};color:{color}"><b>{e.get("asset","")}</b> · {e.get("type","")} · {e.get("expiry_date","")} · {indicator}{("  ·  " + e.get("notes","")) if e.get("notes") else ""}</div>', unsafe_allow_html=True)
    else:
        st.caption("no rights entries yet")

# ── TAB 6: LEARNING ───────────────────────────────────────
with tab6:
    st.markdown("### Continuous Learning")
    st.caption("reviewer decisions tune detection over time")

    logs = load_feedback_log()
    if not logs:
        st.info("no reviewer decisions yet")
    else:
        df_log = pd.DataFrame(logs)
        total = len(df_log)
        approved = len(df_log[df_log.decision == "approved"]) if "decision" in df_log else 0
        rejected = len(df_log[df_log.decision == "rejected"]) if "decision" in df_log else 0
        escalated = len(df_log[df_log.decision == "escalated"]) if "decision" in df_log else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f'<p class="meta-label">total reviewed</p><p class="meta-value-lavender">{total}</p>', unsafe_allow_html=True)
        m2.markdown(f'<p class="meta-label">approved</p><p class="meta-value-mint">{approved}</p>', unsafe_allow_html=True)
        m3.markdown(f'<p class="meta-label">rejected</p><p class="meta-value-pink">{rejected}</p>', unsafe_allow_html=True)
        m4.markdown(f'<p class="meta-label">escalated</p><p class="meta-value-peach">{escalated}</p>', unsafe_allow_html=True)

        fpr = round(approved / total * 100, 1) if total > 0 else 0
        st.markdown("---")
        st.markdown(f"**Estimated false positive rate:** {fpr}% of findings approved by reviewers")
        st.caption("high rate = detection thresholds need loosening for this ruleset")
        st.markdown("---")
        st.dataframe(df_log, width='stretch')
        st.download_button("↓ export learning data", df_log.to_csv(index=False), "cleared_learning.csv", "text/csv")