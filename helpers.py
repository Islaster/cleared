"""Helper functions for parsing, scoring, logging, and metrics."""

import re
import json
from datetime import datetime, date


def parse_findings(report):
    """Extract timestamped findings from a compliance report."""
    findings = []
    lines = report.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.lower().startswith("timestamp:") and "[" in line:
            ts_match = re.search(r'\[[\d:]+(?:-[\d:]+)?\]', line)
            ts_str = ts_match.group(0) if ts_match else ""

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

        if re.match(r'^\[[\d:]+', line):
            findings.append(line)
            i += 1
            continue

        i += 1
    return findings


def severity_score(report):
    """Compute a weighted severity score from a report."""
    score = 0
    score += report.count("CRITICAL") * 10
    score += report.count("MAJOR") * 7
    score += report.count("MINOR") * 3
    return score


def parse_timestamp_seconds(finding):
    """Extract timestamp in seconds from a finding string."""
    try:
        match = re.search(r'\[(\d+):(\d+)', finding)
        if match:
            return int(match.group(1)) * 60 + int(match.group(2))
    except Exception:
        pass
    return 0


def log_feedback(finding, decision, video_id, ruleset, platforms, jurisdictions):
    """Append a reviewer decision to the feedback log."""
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


def build_prompt(ruleset_name, custom_rules, platforms, jurisdictions, audio_flags, include_rights):
    """Build the compliance analysis prompt for TwelveLabs Pegasus."""
    from config import RULESETS, JURISDICTIONS

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
