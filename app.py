import os
import json
import time
import html as html_mod
import pandas as pd
from datetime import datetime, date
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from twelvelabs import TwelveLabs

from config import RULESETS, JURISDICTIONS, PLATFORMS, AUDIO_FLAGS, DEMO_VIDEO_ID, DEMO_INDEX_ID, DEMO_VIDEO_LABEL
from helpers import (
    parse_findings, severity_score, parse_timestamp_seconds, build_prompt,
    log_feedback, load_feedback_log, load_rights_log, save_rights_log,
    get_expiring_rights, load_ground_truth, save_ground_truth, compute_metrics,
)
from styles import get_app_css, LOADING_OVERLAY, THEME_TOGGLE_JS

load_dotenv()
client = TwelveLabs(api_key=os.environ.get("TWELVELABS_API_KEY", ""))

# ── API HELPERS (need client + st.cache) ─────────────────────
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

# ── VIDEO PLAYER COMPONENT ───────────────────────────────────
def video_player(video_url: str, seek_to: float = 0, findings: list = None):
    markers_js = ""
    if findings:
        for i, f in enumerate(findings):
            ts = parse_timestamp_seconds(f)
            severity = "CRITICAL" if "CRITICAL" in f else "MAJOR" if "MAJOR" in f else "MINOR"
            color = "#dc2626" if severity == "CRITICAL" else "#ea580c" if severity == "MAJOR" else "#2563eb"
            safe_label = html_mod.escape(f[:60]).replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
            markers_js += f'addMarker({ts}, "{color}", "{safe_label}");'

    findings_data = json.dumps([
        (parse_timestamp_seconds(f), html_mod.escape(f[:50]),
         "critical" if "CRITICAL" in f else "major" if "MAJOR" in f else "minor")
        for f in (findings or [])
    ])

    components.html(f"""
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        html, body {{
            background: #111;
            font-family: 'Inter', -apple-system, sans-serif;
            overflow: hidden;
            height: 100%;
        }}

        .outer-wrap {{
            display: flex;
            height: 100%;
            background: #111;
            border-radius: 10px;
            overflow: hidden;
        }}

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
            background: #333;
            cursor: pointer;
            flex-shrink: 0;
        }}

        .timeline-progress {{
            position: absolute;
            top: 0; left: 0;
            height: 100%;
            background: #fff;
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
            background: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 0.3rem 0.6rem;
            font-size: 0.62rem;
            color: #333;
            white-space: normal;
            width: 180px;
            z-index: 10;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }}

        .timeline-marker:hover .marker-tooltip {{ display: block; }}

        .controls-row {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.4rem 0.75rem;
            background: #111;
            border-top: 1px solid #222;
            flex-shrink: 0;
        }}

        .timecode {{
            font-size: 0.65rem;
            color: #888;
            letter-spacing: 0.05em;
            white-space: nowrap;
            font-weight: 500;
        }}

        .seekbar-panel {{
            width: 220px;
            flex-shrink: 0;
            display: flex;
            flex-direction: column;
            background: #0a0a0a;
            border-left: 1px solid #222;
            overflow: hidden;
        }}

        .panel-label {{
            font-size: 0.6rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: #666;
            padding: 0.6rem 0.75rem 0.5rem;
            border-bottom: 1px solid #222;
            flex-shrink: 0;
            font-weight: 600;
        }}

        .seekbar-wrap {{
            flex: 1;
            overflow-y: auto;
            padding: 0.4rem 0.5rem;
            display: flex;
            flex-direction: column;
            gap: 0.3rem;
        }}

        .seekbar-wrap::-webkit-scrollbar {{ width: 3px; }}
        .seekbar-wrap::-webkit-scrollbar-track {{ background: #0a0a0a; }}
        .seekbar-wrap::-webkit-scrollbar-thumb {{ background: #333; border-radius: 2px; }}

        .seek-badge {{
            background: transparent;
            border-radius: 6px;
            padding: 0.35rem 0.6rem;
            font-size: 0.6rem;
            cursor: pointer;
            letter-spacing: 0.02em;
            font-family: 'Inter', sans-serif;
            font-weight: 500;
            transition: all 0.12s;
            white-space: normal;
            text-align: left;
            line-height: 1.4;
            width: 100%;
        }}

        .seek-badge.critical {{
            border: 1px solid #dc2626; color: #fca5a5;
        }}
        .seek-badge.critical:hover {{ background: rgba(220,38,38,0.15); }}

        .seek-badge.major {{
            border: 1px solid #ea580c; color: #fdba74;
        }}
        .seek-badge.major:hover {{ background: rgba(234,88,12,0.15); }}

        .seek-badge.minor {{
            border: 1px solid #2563eb; color: #93c5fd;
        }}
        .seek-badge.minor:hover {{ background: rgba(37,99,235,0.15); }}

        .no-findings {{
            font-size: 0.62rem;
            color: #555;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            padding: 0.75rem 0.5rem;
            font-weight: 500;
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
                {"<span class='timecode' style='color:#fff;margin-left:auto;background:#333;padding:2px 8px;border-radius:4px;'>⏱ " + str(int(seek_to)) + "s</span>" if seek_to > 0 else ""}
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
st.set_page_config(page_title="Cleared", layout="wide", page_icon="C")

st.markdown(get_app_css(), unsafe_allow_html=True)
st.markdown(THEME_TOGGLE_JS, unsafe_allow_html=True)

# ── SIDEBAR ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="padding:0.5rem 0 0.6rem 0;border-bottom:1px solid var(--border-light);margin-bottom:0.75rem;'
        'display:flex;align-items:center;justify-content:space-between;">'
        '<div>'
        '<span style="font-family:\'JetBrains Mono\',monospace;font-weight:700;color:var(--text-primary);font-size:1.1rem;'
        'letter-spacing:-0.02em;line-height:1;">Cleared</span>'
        '<span style="font-family:\'JetBrains Mono\',monospace;color:var(--text-muted);font-size:0.5rem;letter-spacing:0.1em;'
        'text-transform:uppercase;margin-left:0.4rem;vertical-align:middle;font-weight:500;">compliance</span>'
        '</div>'
        '<div class="theme-toggle" onclick="toggleTheme()">light / dark</div>'
        '</div>',
        unsafe_allow_html=True
    )
    run = st.button("Run Compliance Check", width='stretch')

    st.markdown('<p style="margin-top:1rem;margin-bottom:0.25rem;font-size:0.62rem;font-weight:600;color:var(--text-muted);letter-spacing:0.1em;text-transform:uppercase;font-family:\'JetBrains Mono\',monospace;">Video</p>', unsafe_allow_html=True)
    st.caption(DEMO_VIDEO_LABEL)

    selected_video_id = DEMO_VIDEO_ID
    selected_video_label = DEMO_VIDEO_LABEL

    st.markdown('<p style="margin-top:1rem;margin-bottom:0.25rem;font-size:0.62rem;font-weight:600;color:var(--text-muted);letter-spacing:0.1em;text-transform:uppercase;font-family:JetBrains Mono,monospace;">Ruleset</p>', unsafe_allow_html=True)
    ruleset_name = st.selectbox("ruleset", list(RULESETS.keys()), label_visibility="collapsed")
    custom_rules = ""
    if ruleset_name == "Custom":
        custom_rules = st.text_area("custom rules (one per line)", height=100, label_visibility="collapsed", placeholder="e.g.\nNo visible tattoos\nNo competitor products")

    st.markdown('<p style="margin-top:1rem;margin-bottom:0.25rem;font-size:0.62rem;font-weight:600;color:var(--text-muted);letter-spacing:0.1em;text-transform:uppercase;font-family:JetBrains Mono,monospace;">Platforms</p>', unsafe_allow_html=True)
    selected_platforms = st.multiselect("platforms", PLATFORMS, default=[], label_visibility="collapsed")

    st.markdown('<p style="margin-top:1rem;margin-bottom:0.25rem;font-size:0.62rem;font-weight:600;color:var(--text-muted);letter-spacing:0.1em;text-transform:uppercase;font-family:JetBrains Mono,monospace;">Jurisdictions</p>', unsafe_allow_html=True)
    selected_jurisdictions = st.multiselect("jurisdictions", list(JURISDICTIONS.keys()), default=[], label_visibility="collapsed")

    st.markdown('<p style="margin-top:1rem;margin-bottom:0.25rem;font-size:0.62rem;font-weight:600;color:var(--text-muted);letter-spacing:0.1em;text-transform:uppercase;font-family:JetBrains Mono,monospace;">Audio Flags</p>', unsafe_allow_html=True)
    selected_audio = st.multiselect("audio flags", AUDIO_FLAGS, default=AUDIO_FLAGS, label_visibility="collapsed")

    st.markdown('<div style="margin-top:0.75rem"></div>', unsafe_allow_html=True)
    include_rights = st.checkbox("Include rights & clearances scan", value=True)

# ── THEATER PLAYER ────────────────────────────────────────────
_tv_url = fetch_video_url(DEMO_VIDEO_ID, DEMO_INDEX_ID)
if _tv_url:
    video_player(
        _tv_url,
        seek_to=st.session_state.get("seek_to", 0),
        findings=st.session_state.get("findings", []),
    )
else:
    st.markdown(
        '<div style="background:#111;border-radius:8px;height:420px;display:flex;align-items:center;'
        'justify-content:center;color:#555;font-family:\'JetBrains Mono\',monospace;font-size:0.78rem;'
        'letter-spacing:0.05em;">Video player loading...</div>',
        unsafe_allow_html=True
    )


# ── RUN ───────────────────────────────────────────────────────
_overlay_ph = st.empty()

if run:
    if not selected_platforms:
        st.error("Select at least one platform to run analysis.")
    else:
        _overlay_ph.markdown(LOADING_OVERLAY, unsafe_allow_html=True)
        prompt = build_prompt(ruleset_name, custom_rules, selected_platforms, selected_jurisdictions, selected_audio, include_rights)
        try:
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
        except Exception as e:
            st.error(f"Analysis failed: {e}")
        finally:
            _overlay_ph.empty()

# ── RESULTS ───────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Report", "Review Findings", "Accuracy", "Export", "Rights Tracker", "Learning"
])

# ── TAB 1: REPORT ─────────────────────────────────────────
with tab1:
    if "report" not in st.session_state:
        st.markdown('<div style="text-align:center;padding:4rem 2rem;color:var(--text-muted);font-size:0.82rem;'
                    'font-family:\'JetBrains Mono\',monospace;letter-spacing:0.02em;">'
                    'Select platforms and click <b style="color:var(--text-secondary)">Run Compliance Check</b> to analyze.</div>',
                    unsafe_allow_html=True)
    else:
        score = st.session_state.risk_score
        if score >= 20:
            st.markdown(f'<div class="risk-critical">CRITICAL RISK &mdash; Score {score} &mdash; Immediate action required</div>', unsafe_allow_html=True)
        elif score >= 15:
            st.markdown(f'<div class="risk-high">HIGH RISK &mdash; Score {score}</div>', unsafe_allow_html=True)
        elif score >= 7:
            st.markdown(f'<div class="risk-medium">MEDIUM RISK &mdash; Score {score}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="risk-low">LOW RISK &mdash; Score {score}</div>', unsafe_allow_html=True)
        st.markdown(f"*{st.session_state.get('run_time','—')} · {st.session_state.get('ruleset','—')} · {st.session_state.get('video_label','')}*")
        st.markdown("---")
        st.markdown(st.session_state.report)

# ── TAB 2: REVIEW FINDINGS ────────────────────────────────
with tab2:
    if "report" not in st.session_state:
        st.caption("Run a compliance check to review findings.")
    else:
        findings = st.session_state.findings

        st.caption("Review each finding. Click timestamps to seek. Decisions are logged for learning.")

        if not findings:
            st.info("No timestamped findings detected. See full report.")
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

                    if col_seek.button(f"Seek {ts_sec}s", key=f"seek_{i}"):
                        st.session_state.seek_to = ts_sec
                        st.rerun()

                    if col_a.button("Approve", key=f"a_{i}"):
                        log_feedback(finding, "approved", st.session_state.video_id, st.session_state.ruleset, st.session_state.platforms, st.session_state.jurisdictions)
                        st.success("Logged: approved")

                    if col_r.button("Reject", key=f"r_{i}"):
                        log_feedback(finding, "rejected", st.session_state.video_id, st.session_state.ruleset, st.session_state.platforms, st.session_state.jurisdictions)
                        st.error("Logged: rejected")

                    if col_e.button("Escalate", key=f"e_{i}"):
                        log_feedback(finding, "escalated", st.session_state.video_id, st.session_state.ruleset, st.session_state.platforms, st.session_state.jurisdictions)
                        st.warning("Logged: escalated")

                    # LTX PANEL (always shown)
                    st.markdown('<div class="ltx-panel">', unsafe_allow_html=True)
                    st.markdown(f"<p style='color:#7c3aed;font-size:0.68rem;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.75rem;font-weight:600;font-family:\"JetBrains Mono\",monospace;'>LTX Remediation</p>", unsafe_allow_html=True)
                    st.markdown(f"<p style='color:var(--text-tertiary);font-size:0.78rem;margin-bottom:0.75rem'>{finding[:80]}...</p>", unsafe_allow_html=True)

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

                    st.markdown("<p style='font-size:0.7rem;color:#888;letter-spacing:0.05em;text-transform:uppercase;margin-bottom:0.6rem;font-weight:500'>Select replacement clip to generate:</p>", unsafe_allow_html=True)

                    _thumb_schemes = [
                        ("135deg, #f5f3ff 0%, #ede9fe 60%, #ddd6fe 100%", "#7c3aed", "OPTION 1"),
                        ("135deg, #eff6ff 0%, #dbeafe 60%, #bfdbfe 100%", "#2563eb", "OPTION 2"),
                        ("135deg, #fef2f2 0%, #fecaca 60%, #fca5a5 100%", "#dc2626", "OPTION 3"),
                        ("135deg, #f0fdf4 0%, #dcfce7 60%, #bbf7d0 100%", "#16a34a", "OPTION 4"),
                    ]
                    _tcols = st.columns(2)
                    for j, opt in enumerate(options):
                        _grad, _accent, _label = _thumb_schemes[j % len(_thumb_schemes)]
                        with _tcols[j % 2]:
                            st.markdown(f"""
<div style="position:relative;width:100%;padding-bottom:56.25%;background:linear-gradient({_grad});border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;margin-bottom:0.35rem;">
  <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;">
    <div style="width:32px;height:32px;border-radius:50%;border:2px solid {_accent};display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,0.7);">
      <div style="width:0;height:0;border-top:7px solid transparent;border-bottom:7px solid transparent;border-left:12px solid {_accent};margin-left:2px;"></div>
    </div>
  </div>
  <div style="position:absolute;top:6px;left:8px;font-size:0.55rem;color:{_accent};letter-spacing:0.08em;font-family:Inter,sans-serif;font-weight:600;">{_label}</div>
  <div style="position:absolute;bottom:0;left:0;right:0;background:linear-gradient(transparent,rgba(255,255,255,0.85));padding:0.35rem 0.55rem;">
    <div style="font-size:0.62rem;color:#555;line-height:1.3;">{opt[:55]}{"…" if len(opt)>55 else ""}</div>
  </div>
</div>""", unsafe_allow_html=True)
                            if st.button("generate", key=f"ltx_use_{i}_{j}", width='stretch'):
                                st.session_state[f"ltx_selected_{i}"] = opt
                                st.success(f"Queued: {opt[:60]}...")

                    if st.session_state.get(f"ltx_selected_{i}"):
                        st.markdown(f"<p style='color:#166534;font-size:0.75rem;margin-top:0.5rem;font-weight:500'>Queued: {st.session_state[f'ltx_selected_{i}'][:80]}...</p>", unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

# ── TAB 3: ACCURACY METRICS ───────────────────────────────
with tab3:
    st.markdown("### Accuracy Metrics")
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

        metric_card(m1, metrics["tp"], "true positives", "#059669")
        metric_card(m2, metrics["fp"], "false positives", "#dc2626")
        metric_card(m3, metrics["fn"], "false negatives", "#d97706")
        metric_card(m4, f"{metrics['precision']:.0%}", "precision", "#7c3aed")
        metric_card(m5, f"{metrics['recall']:.0%}", "recall", "#2563eb")
        metric_card(m6, f"{metrics['f1']:.0%}", "f1 score", "#be185d")

        st.markdown("---")

        # explanation
        st.markdown(f"""
<p style='font-size:0.85rem;color:#444;line-height:1.8'>
<span style='color:#059669;font-weight:600'>Precision {metrics['precision']:.0%}</span> —
of {metrics['tp'] + metrics['fp']} findings flagged, {metrics['tp']} matched ground truth ({metrics['fp']} false positives)<br>
<span style='color:#2563eb;font-weight:600'>Recall {metrics['recall']:.0%}</span> —
of {metrics['tp'] + metrics['fn']} real violations, {metrics['tp']} were detected ({metrics['fn']} missed)<br>
<span style='color:#be185d;font-weight:600'>F1 {metrics['f1']:.0%}</span> —
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
                "Download Metrics CSV",
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
<div style='background:#fff;border:1px solid #e8e8e8;border-radius:10px;padding:1.25rem;margin-top:0.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.04)'>
<p style='color:#7c3aed;font-size:0.7rem;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.5rem;font-weight:600'>Baseline Comparison</p>
<p style='color:#333;font-size:0.9rem'>Manual review: <span style='color:#ea580c;font-weight:600'>{manual_time} minutes</span> &nbsp;|&nbsp;
System: <span style='color:#059669;font-weight:600'>{auto_time} seconds</span> &nbsp;|&nbsp;
Speedup: <span style='color:#be185d;font-weight:600'>{speedup}x</span></p>
<p style='color:#888;font-size:0.78rem;margin-top:0.5rem'>At $150/hr manual review cost: <span style='color:#059669;font-weight:600'>${round(manual_time/60*150, 2)} saved per video</span></p>
</div>
""", unsafe_allow_html=True)

# ── TAB 4: EXPORT & AUDIT ─────────────────────────────────
with tab4:
    if "report" not in st.session_state:
        st.caption("Run a compliance check to enable export.")
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
            st.download_button("Download CSV", df.to_csv(index=False), "cleared_report.csv", "text/csv", width='stretch')

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
            st.download_button("Download Audit JSON", json.dumps(audit_json, indent=2), "cleared_audit.json", "application/json", width='stretch')

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
            st.download_button("Download OTIO Markers", json.dumps(otio_export, indent=2), "cleared_markers.otio", "application/json", width='stretch')

        st.caption("OTIO markers import into Premiere Pro, Avid, and DaVinci Resolve via OpenTimelineIO plugin")
        st.markdown("---")
        st.markdown("### Audit Trail")
        logs = load_feedback_log()
        if logs:
            st.dataframe(pd.DataFrame(logs), width='stretch')
            st.download_button("Download Audit Trail", pd.DataFrame(logs).to_csv(index=False), "cleared_audit_trail.csv", "text/csv")
        else:
            st.caption("no reviewer decisions logged yet")

# ── TAB 5: RIGHTS TRACKER ─────────────────────────────────
with tab5:
    rights_entries = load_rights_log()
    expiring = get_expiring_rights(rights_entries, days_ahead=30)
    if expiring:
        for e in expiring:
            days = e.get("days_remaining", "?")
            color = "#dc2626" if isinstance(days, int) and days <= 7 else "#ea580c"
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
                    css, indicator = "rights-expiring", f"EXPIRED {abs(days)} days ago"
                    color = "#dc2626"
                elif days <= 7:
                    css, indicator = "rights-expiring", f"Expires in {days} days"
                    color = "#ea580c"
                elif days <= 30:
                    css, indicator = "rights-expiring", f"{days} days remaining"
                    color = "#d97706"
                else:
                    css, indicator = "rights-ok", f"{days} days remaining"
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
        st.download_button("Download Learning Data", df_log.to_csv(index=False), "cleared_learning.csv", "text/csv")