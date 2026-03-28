"""All CSS styles for the Cleared compliance app — themed with CSS variables."""


def get_app_css():
    """Return the full application CSS with light/dark theme support via CSS variables."""
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* ══════════════════════════════════════════════════════
   THEME VARIABLES
   ══════════════════════════════════════════════════════ */

/* ── LIGHT (default) ── */
:root {
    --bg-primary: #f8f9fa;
    --bg-secondary: #ffffff;
    --bg-tertiary: #f3f4f6;
    --bg-input: #ffffff;
    --bg-hover: #f9fafb;
    --bg-btn-primary: #111827;
    --bg-btn-primary-hover: #1f2937;

    --border: #d1d5db;
    --border-light: #e5e7eb;

    --text-primary: #111827;
    --text-secondary: #374151;
    --text-tertiary: #6b7280;
    --text-muted: #9ca3af;
    --text-on-primary: #ffffff;

    --accent: #111827;

    --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.08);

    --risk-critical-bg: #fef2f2; --risk-critical-border: #fecaca; --risk-critical-accent: #dc2626; --risk-critical-text: #991b1b;
    --risk-high-bg: #fff7ed; --risk-high-border: #fed7aa; --risk-high-accent: #ea580c; --risk-high-text: #9a3412;
    --risk-medium-bg: #fffbeb; --risk-medium-border: #fde68a; --risk-medium-accent: #d97706; --risk-medium-text: #92400e;
    --risk-low-bg: #f0fdf4; --risk-low-border: #bbf7d0; --risk-low-accent: #16a34a; --risk-low-text: #166534;

    --tag-1-bg: #f0fdf4; --tag-1-border: #bbf7d0; --tag-1-text: #166534;
    --tag-2-bg: #eff6ff; --tag-2-border: #bfdbfe; --tag-2-text: #1e40af;
    --tag-3-bg: #faf5ff; --tag-3-border: #e9d5ff; --tag-3-text: #6b21a8;

    --success-bg: #f0fdf4; --success-border: #bbf7d0; --success-text: #166534;
    --error-bg: #fef2f2; --error-border: #fecaca; --error-text: #991b1b;
    --warn-bg: #fffbeb; --warn-border: #fde68a; --warn-text: #92400e;
    --info-bg: #eff6ff; --info-border: #bfdbfe; --info-text: #1e40af;

    --ltx-bg: #faf5ff; --ltx-border: #e9d5ff;
    --overlay-bg: rgba(248,249,250,0.92);
}

/* ── DARK ── */
.dark-mode {
    --bg-primary: #0a0a0a;
    --bg-secondary: #111111;
    --bg-tertiary: #1a1a1a;
    --bg-input: #141414;
    --bg-hover: #1a1a1a;
    --bg-btn-primary: #e5e7eb;
    --bg-btn-primary-hover: #d1d5db;

    --border: #2a2a2a;
    --border-light: #1f1f1f;

    --text-primary: #e5e7eb;
    --text-secondary: #d1d5db;
    --text-tertiary: #9ca3af;
    --text-muted: #6b7280;
    --text-on-primary: #0a0a0a;

    --accent: #e5e7eb;

    --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.4);

    --risk-critical-bg: rgba(220,38,38,0.1); --risk-critical-border: #7f1d1d; --risk-critical-accent: #ef4444; --risk-critical-text: #fca5a5;
    --risk-high-bg: rgba(234,88,12,0.1); --risk-high-border: #7c2d12; --risk-high-accent: #f97316; --risk-high-text: #fdba74;
    --risk-medium-bg: rgba(217,119,6,0.1); --risk-medium-border: #78350f; --risk-medium-accent: #f59e0b; --risk-medium-text: #fde68a;
    --risk-low-bg: rgba(22,163,74,0.08); --risk-low-border: #14532d; --risk-low-accent: #22c55e; --risk-low-text: #86efac;

    --tag-1-bg: rgba(22,163,74,0.1); --tag-1-border: #14532d; --tag-1-text: #86efac;
    --tag-2-bg: rgba(37,99,235,0.1); --tag-2-border: #1e3a5f; --tag-2-text: #93c5fd;
    --tag-3-bg: rgba(124,58,237,0.1); --tag-3-border: #3b0764; --tag-3-text: #c4b5fd;

    --success-bg: rgba(22,163,74,0.1); --success-border: #14532d; --success-text: #86efac;
    --error-bg: rgba(220,38,38,0.1); --error-border: #7f1d1d; --error-text: #fca5a5;
    --warn-bg: rgba(217,119,6,0.1); --warn-border: #78350f; --warn-text: #fde68a;
    --info-bg: rgba(37,99,235,0.1); --info-border: #1e3a5f; --info-text: #93c5fd;

    --ltx-bg: rgba(124,58,237,0.06); --ltx-border: #3b0764;
    --overlay-bg: rgba(10,10,10,0.92);
}

/* ══════════════════════════════════════════════════════
   COMPONENTS
   ══════════════════════════════════════════════════════ */

/* ── BASE ── */
html, body, [class*="css"] {
    font-family: 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace;
}
.stApp {
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    transition: background-color 0.2s, color 0.2s;
}

/* ── TYPOGRAPHY ── */
h1 {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    font-size: 1.6rem !important;
    letter-spacing: -0.02em;
    margin-bottom: 0 !important;
}
h2 {
    font-family: 'JetBrains Mono', monospace !important;
    color: var(--text-primary) !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 600 !important;
}
h3 {
    font-family: 'JetBrains Mono', monospace !important;
    color: var(--text-secondary) !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 600 !important;
}

/* ── TEXT ── */
.stMarkdown p { color: var(--text-secondary) !important; font-size: 0.85rem; line-height: 1.7; }
.stCaption, .stCaption p { color: var(--text-muted) !important; font-size: 0.72rem !important; }
hr { border-color: var(--border-light) !important; margin: 1rem 0 !important; }

/* ── SIDEBAR ── */
section[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border-light) !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 1rem !important;
}
section[data-testid="stSidebar"] .stMarkdown p {
    color: var(--text-tertiary) !important;
    font-size: 0.75rem !important;
}
section[data-testid="stSidebar"] label {
    color: var(--text-secondary) !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
}
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] .stCaption p {
    color: var(--text-muted) !important;
    font-size: 0.72rem !important;
}

/* ── INPUTS ── */
.stTextInput input, .stTextArea textarea {
    background: var(--bg-input) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: 6px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--text-tertiary) !important;
    box-shadow: 0 0 0 2px rgba(107,114,128,0.15) !important;
}

/* ── SELECTS ── */
.stSelectbox [data-baseweb="select"] > div,
.stMultiSelect [data-baseweb="select"] > div {
    background: var(--bg-input) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    color: var(--text-primary) !important;
}
.stSelectbox [data-baseweb="select"] span,
.stMultiSelect [data-baseweb="select"] span {
    color: var(--text-primary) !important;
}
.stSelectbox svg, .stMultiSelect svg {
    fill: var(--text-tertiary) !important;
}
[data-baseweb="popover"] {
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    box-shadow: var(--shadow-md) !important;
}
[data-baseweb="menu"] { background: var(--bg-secondary) !important; }
[data-baseweb="menu"] li, [role="option"] {
    color: var(--text-primary) !important;
    background: var(--bg-secondary) !important;
    font-size: 0.82rem !important;
}
[role="option"]:hover, [data-baseweb="menu"] li:hover,
[role="option"][aria-selected="true"] {
    background: var(--bg-tertiary) !important;
}

/* ── MULTISELECT TAGS ── */
.stMultiSelect span[data-baseweb="tag"] {
    background: var(--tag-1-bg) !important;
    border: 1px solid var(--tag-1-border) !important;
    border-radius: 4px !important;
    color: var(--tag-1-text) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.68rem !important;
    font-weight: 500 !important;
}
.stMultiSelect span[data-baseweb="tag"]:nth-child(3n+2) {
    background: var(--tag-2-bg) !important;
    border-color: var(--tag-2-border) !important;
    color: var(--tag-2-text) !important;
}
.stMultiSelect span[data-baseweb="tag"]:nth-child(3n+3) {
    background: var(--tag-3-bg) !important;
    border-color: var(--tag-3-border) !important;
    color: var(--tag-3-text) !important;
}
.stMultiSelect span[data-baseweb="tag"] span[role="presentation"] { color: inherit !important; }
.stMultiSelect [data-baseweb="clear-icon"] { color: var(--text-muted) !important; }

/* ── CHECKBOX ── */
.stCheckbox label { color: var(--text-secondary) !important; font-size: 0.8rem !important; font-weight: 500 !important; }

/* ── BUTTONS ── */
.stButton > button {
    background: var(--bg-secondary) !important;
    color: var(--text-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 600 !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.02em;
    transition: all 0.15s ease !important;
}
.stButton > button:hover {
    background: var(--bg-hover) !important;
    border-color: var(--text-muted) !important;
    box-shadow: var(--shadow-sm) !important;
}
.stButton > button[kind="primary"],
section[data-testid="stSidebar"] .stButton > button {
    background: var(--bg-btn-primary) !important;
    color: var(--text-on-primary) !important;
    border-color: var(--bg-btn-primary) !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--bg-btn-primary-hover) !important;
    box-shadow: var(--shadow-md) !important;
}
.stDownloadButton > button {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-secondary) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    border-radius: 6px !important;
}
.stDownloadButton > button:hover { border-color: var(--text-tertiary) !important; color: var(--text-primary) !important; }

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
    position: sticky !important;
    top: 44px !important;
    z-index: 998 !important;
    background: var(--bg-primary) !important;
    border-bottom: 1px solid var(--border-light) !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-muted) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 500 !important;
    border-bottom: 2px solid transparent !important;
    padding: 0.6rem 1rem !important;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--text-secondary) !important; }
.stTabs [aria-selected="true"] {
    color: var(--text-primary) !important;
    border-bottom: 2px solid var(--accent) !important;
    font-weight: 700 !important;
}

/* ── ALERTS ── */
.stSuccess > div { background: var(--success-bg) !important; border: 1px solid var(--success-border) !important; border-radius: 6px !important; color: var(--success-text) !important; }
.stError > div { background: var(--error-bg) !important; border: 1px solid var(--error-border) !important; border-radius: 6px !important; color: var(--error-text) !important; }
.stWarning > div { background: var(--warn-bg) !important; border: 1px solid var(--warn-border) !important; border-radius: 6px !important; color: var(--warn-text) !important; }
.stInfo > div { background: var(--info-bg) !important; border: 1px solid var(--info-border) !important; border-radius: 6px !important; color: var(--info-text) !important; }

/* ── SPINNER ── */
.stSpinner > div {
    border: 3px solid var(--border-light) !important;
    border-top-color: var(--accent) !important;
    border-radius: 50% !important;
    width: 28px; height: 28px;
    animation: cleared-spin 0.75s linear infinite !important;
}
.stSpinner > div > * { display: none !important; }
@keyframes cleared-spin { to { transform: rotate(360deg); } }

/* ── LAYOUT ── */
[data-testid="stCustomComponentV1"] { margin-bottom: -2rem !important; padding-bottom: 0 !important; line-height: 0 !important; }
iframe { display: block !important; margin-bottom: 0 !important; }
.stTabs { margin-top: 0 !important; }
[data-testid="stCustomComponentV1"] > div { padding-bottom: 0 !important; }
[data-baseweb="no-results"] { display: none !important; }
ul[data-baseweb="menu"] li:only-child[aria-disabled="true"] { display: none !important; }

/* ── RISK BANNERS ── */
.risk-critical { background: var(--risk-critical-bg); border: 1px solid var(--risk-critical-border); border-left: 4px solid var(--risk-critical-accent); border-radius: 6px; padding: 0.75rem 1.25rem; color: var(--risk-critical-text); font-size: 0.8rem; font-weight: 600; margin-bottom: 1rem; font-family: 'JetBrains Mono', monospace; letter-spacing: 0.05em; }
.risk-high { background: var(--risk-high-bg); border: 1px solid var(--risk-high-border); border-left: 4px solid var(--risk-high-accent); border-radius: 6px; padding: 0.75rem 1.25rem; color: var(--risk-high-text); font-size: 0.8rem; font-weight: 600; margin-bottom: 1rem; font-family: 'JetBrains Mono', monospace; letter-spacing: 0.05em; }
.risk-medium { background: var(--risk-medium-bg); border: 1px solid var(--risk-medium-border); border-left: 4px solid var(--risk-medium-accent); border-radius: 6px; padding: 0.75rem 1.25rem; color: var(--risk-medium-text); font-size: 0.8rem; font-weight: 600; margin-bottom: 1rem; font-family: 'JetBrains Mono', monospace; letter-spacing: 0.05em; }
.risk-low { background: var(--risk-low-bg); border: 1px solid var(--risk-low-border); border-left: 4px solid var(--risk-low-accent); border-radius: 6px; padding: 0.75rem 1.25rem; color: var(--risk-low-text); font-size: 0.8rem; font-weight: 600; margin-bottom: 1rem; font-family: 'JetBrains Mono', monospace; letter-spacing: 0.05em; }

/* ── FINDING CARDS ── */
.finding-card { background: var(--bg-secondary); border: 1px solid var(--border-light); border-radius: 6px; padding: 0.85rem 1rem; margin-bottom: 0.5rem; font-size: 0.8rem; color: var(--text-secondary); line-height: 1.6; box-shadow: var(--shadow-sm); }
.finding-critical { border-left: 4px solid var(--risk-critical-accent); }
.finding-major { border-left: 4px solid var(--risk-high-accent); }
.finding-minor { border-left: 4px solid #2563eb; }

/* ── META ── */
.meta-label { font-size: 0.62rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.2rem; font-weight: 600; }
.meta-value-pink { color: #be185d; font-size: 1.1rem; font-weight: 700; }
.meta-value-lavender { color: #7c3aed; font-size: 1.1rem; font-weight: 700; }
.meta-value-mint { color: #059669; font-size: 1.1rem; font-weight: 700; }
.meta-value-peach { color: #2563eb; font-size: 1.1rem; font-weight: 700; }

/* ── PANELS ── */
.ltx-panel { background: var(--ltx-bg); border: 1px solid var(--ltx-border); border-radius: 6px; padding: 1rem 1.25rem; margin-top: 0.75rem; }
.rights-expiring { background: var(--risk-high-bg); border: 1px solid var(--risk-high-border); border-radius: 6px; padding: 0.6rem 0.85rem; margin-bottom: 0.4rem; font-size: 0.78rem; color: var(--risk-high-text); font-weight: 500; }
.rights-ok { background: var(--risk-low-bg); border: 1px solid var(--risk-low-border); border-radius: 6px; padding: 0.6rem 0.85rem; margin-bottom: 0.4rem; font-size: 0.78rem; color: var(--text-muted); }
.metric-card { background: var(--bg-secondary); border: 1px solid var(--border-light); border-radius: 8px; padding: 1.25rem; text-align: center; box-shadow: var(--shadow-sm); }
.metric-number { font-size: 2rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; color: var(--text-primary); }
.metric-label { font-size: 0.6rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-muted); margin-top: 0.25rem; font-weight: 500; }
.section-divider { border: none; border-top: 1px solid var(--border-light); margin: 0.75rem 0; }

/* ── THEME TOGGLE ── */
.theme-toggle {
    display: inline-flex; align-items: center; gap: 0.5rem;
    padding: 0.35rem 0.75rem;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: 6px;
    cursor: pointer;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    font-weight: 500;
    color: var(--text-tertiary);
    letter-spacing: 0.05em;
    text-transform: uppercase;
    transition: all 0.15s;
    user-select: none;
}
.theme-toggle:hover { border-color: var(--text-muted); color: var(--text-primary); }
</style>
"""


def get_loading_overlay():
    return """
<div style="position:fixed;inset:0;background:var(--overlay-bg, rgba(248,249,250,0.92));z-index:9999;
     display:flex;flex-direction:column;align-items:center;justify-content:center;
     backdrop-filter:blur(8px);">
  <div style="width:48px;height:48px;border-radius:50%;
       border:4px solid var(--border-light, #e5e7eb);
       border-top-color:var(--accent, #111827);
       animation:cleared-spin 0.75s linear infinite;">
  </div>
  <div style="color:var(--text-primary, #111827);font-family:'JetBrains Mono',monospace;font-size:0.85rem;
       font-weight:600;margin-top:1.5rem;letter-spacing:0.02em;">
    Analyzing with Pegasus
  </div>
  <div style="color:var(--text-muted, #6b7280);font-family:'JetBrains Mono',monospace;font-size:0.72rem;
       margin-top:0.35rem;letter-spacing:0.02em;">
    This may take a minute
  </div>
</div>
<style>@keyframes cleared-spin { to { transform: rotate(360deg); } }</style>
"""


# Keep backwards compat
LOADING_OVERLAY = get_loading_overlay()


THEME_TOGGLE_JS = """
<script>
function toggleTheme() {
    const app = document.querySelector('.stApp');
    if (!app) return;
    const isDark = app.classList.toggle('dark-mode');
    localStorage.setItem('cleared-theme', isDark ? 'dark' : 'light');
}
// restore saved theme on load
(function() {
    const saved = localStorage.getItem('cleared-theme');
    if (saved === 'dark') {
        const app = document.querySelector('.stApp');
        if (app) app.classList.add('dark-mode');
    }
})();
</script>
"""
