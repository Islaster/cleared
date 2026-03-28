"""Constants and configuration for Cleared compliance app."""

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

PLATFORMS = [
    "YouTube", "TikTok", "Instagram", "Broadcast pre-watershed",
    "Streaming (Netflix/HBO)", "Roblox", "The Sphere", "Custom",
]

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

# Demo video IDs
DEMO_VIDEO_ID = "69bf04be251dc4f29f376218"
DEMO_INDEX_ID = "69bf0452a434aab7c15a12b4"
DEMO_VIDEO_LABEL = "compliance-practice-10"
DEMO_VIDEO_FILENAME = "compliance-practice-10.mp4"
