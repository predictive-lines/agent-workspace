#!/usr/bin/env python3
"""Build the EFP Interviews Notion database + per-stage templates.

Strategy:
1. Create a data source (database) under the ai-space root page.
2. Properties: Candidate (title), Email, Stage (select), Date, Interviewer,
   Decision (select), HireScore URL, Cycle, Notes summary.
3. Parse references/interview-questions.md into 4 stage-scoped question sets.
4. Create 4 "template" pages in the database (one per stage). Each page body
   is the full question list for that stage, as toggle blocks:
     - Toggle header = the question text
     - Inside each toggle:
         - Callout block with the listening-for / answer guidance
         - Blank paragraph block (the input field — fill in during interview)

Run:  python3 build_notion_interview_db.py

Requires NOTION_API_KEY file at ~/.config/notion/api_key.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

API_KEY = Path("~/.config/notion/api_key").expanduser().read_text().strip()
NOTION_VERSION = "2025-09-03"
BASE = "https://api.notion.com/v1"
AI_SPACE_PAGE_ID = "2ff7e702-d98c-80a9-bf01-d03635e5e5f4"

QUESTIONS_FILE = Path(
    "~/.openclaw/workspace/skills/excel-fire-recruiting/references/interview-questions.md"
).expanduser()


def api(method: str, path: str, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {API_KEY}")
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        raise


# --- Markdown parsing ---
# We want to extract, per section, a list of questions where each question is:
#   { "text": "...", "guidance": "..." }
# A question starts at a line beginning with `- `[Tag]` ` followed by bold text
# or plain text, and continues through indented sub-bullets until the next
# top-level `- ` or a section break.

QUESTION_RE = re.compile(r"^- `\[(Kevin|Kevin → EEOC-safe|EEOC|Role|Trade|Recruit)\]`\s+(.*)$")


def parse_markdown(path: Path):
    """Parse the interview-questions.md file.

    Returns a dict: { section_title: [ {text, guidance, tag} ] }
    Only returns sections that have at least one question.
    """
    text = path.read_text()
    lines = text.splitlines()

    sections: dict[str, list[dict]] = {}
    current_section = None
    current_subsection = None
    current_q: dict | None = None

    def flush_q():
        nonlocal current_q
        if current_q is None:
            return
        section_key = current_section or "Misc"
        if current_subsection:
            section_key = f"{current_section} :: {current_subsection}"
        sections.setdefault(section_key, []).append(current_q)
        current_q = None

    for raw in lines:
        line = raw.rstrip()

        # Top-level H2 section
        m = re.match(r"^## (.+)$", line)
        if m:
            flush_q()
            current_section = m.group(1).strip()
            current_subsection = None
            continue
        # H3 subsection
        m = re.match(r"^### (.+)$", line)
        if m:
            flush_q()
            current_subsection = m.group(1).strip()
            continue

        # New question (unindented bullet with tag)
        m = QUESTION_RE.match(line)
        if m:
            flush_q()
            tag, rest = m.group(1), m.group(2).strip()
            # Strip leading/trailing bold markers from question text
            rest = rest.strip()
            current_q = {"tag": tag, "text": rest, "guidance_lines": []}
            continue

        # Indented continuation (sub-bullets or continuation of prior line)
        if current_q is not None and (line.startswith("  ") or line == ""):
            if line.strip() == "" and not current_q["guidance_lines"]:
                # skip leading blank line inside question
                continue
            current_q["guidance_lines"].append(line)
            continue

        # Anything else (non-indented text or new heading will be caught above)
        # This means we're outside a question block.
        flush_q()

    flush_q()

    # Drop meta sections that aren't real question sections
    for junk in list(sections.keys()):
        base = junk.split(" :: ")[0]
        if base in {"Sourcing tags", "How to use this document",
                    "Proposed 4-stage interview process",
                    "Red-flag list — questions to NEVER ask, with safe alternatives",
                    "Debrief template"}:
            del sections[junk]

    # Normalize guidance_lines → single markdown string, strip trailing blanks
    for section, qs in sections.items():
        for q in qs:
            # dedent 2 spaces
            g = "\n".join(l[2:] if l.startswith("  ") else l for l in q["guidance_lines"])
            g = g.strip()
            q["guidance"] = g
            del q["guidance_lines"]

    return sections


# --- Stage mapping: which sections go into which stage template ---
# Based on the 4-stage arc in SKILL.md + the question-bank structure.
# Stage 1 = Phone R1 (30 min, Justin solo) — §1-§5 + first pass of §6 Code&AHJ
# Stage 2 = Zoom R2 (45 min, Kevin + Keith) — most of §6 Trade + flood story + round-2 Zoom questions
# Stage 3 = Working Day (1 day, Marquette shop + crew) — observation + §7 recruit STAR + safety questions
# Stage 4 = References (volunteered contacts only) — tight script

STAGE_MAP = {
    "Phone R1 — 30 min (Justin solo)": [
        "1. Work ethic",
        "2. Honesty / integrity",
        "3. UP-of-Michigan-growth mindset",
        "4. Openness to tech (Company Cam especially)",
        "5. Willingness to relocate (Marquette / UP)",
        "Role-specific technical screen (last 10 min of phone round 1, or round-2 Zoom)",
    ],
    "Zoom R2 — 45 min (Kevin + Keith + Justin)": [
        "Round-2 Zoom (Kevin's addition, call 04-18 0:44)",
        "6. Trade knowledge — sprinkler-industry-specific `[Trade]`",
    ],
    "Working Day — 1 day paid in Marquette": [
        "7. Trades-recruiting staples — behavioral / STAR `[Recruit]`",
    ],
    "References — candidate-volunteered only": [
        # No dedicated section — references are a script, not questions. Template body
        # will render the script verbatim instead of questions.
    ],
}


# --- Notion block helpers ---
MAX_TEXT = 1900  # Notion rich_text single content cap is ~2000 chars


def rt(content: str, bold=False, italic=False):
    """rich_text fragment."""
    out = []
    # Chunk long content
    while content:
        chunk, content = content[:MAX_TEXT], content[MAX_TEXT:]
        out.append({
            "type": "text",
            "text": {"content": chunk},
            "annotations": {
                "bold": bold,
                "italic": italic,
                "strikethrough": False,
                "underline": False,
                "code": False,
                "color": "default",
            },
        })
    return out


def heading(level: int, content: str):
    return {
        "object": "block",
        "type": f"heading_{level}",
        f"heading_{level}": {"rich_text": rt(content)},
    }


def paragraph(content: str = ""):
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": rt(content) if content else []},
    }


def callout(content: str, emoji: str = "🎯"):
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": rt(content),
            "icon": {"type": "emoji", "emoji": emoji},
            "color": "gray_background",
        },
    }


def toggle(header: str, children: list):
    return {
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": rt(header),
            "children": children,
        },
    }


def divider():
    return {"object": "block", "type": "divider", "divider": {}}


def question_to_blocks(q: dict):
    """Convert a parsed question to a toggle block with guidance + note field."""
    children = []
    if q.get("guidance"):
        # Split guidance by line — use paragraph for each to preserve formatting
        children.append(callout(q["guidance"], emoji="🎯"))
    # Input field: a blank paragraph block the interviewer types into
    children.append(paragraph(""))  # NOTES: (blank paragraph = typing area)

    # Prefix question with tag in brackets
    header = f"[{q['tag']}] {q['text']}"
    # Notion toggle header cap: keep under ~1900 chars
    header = header[:MAX_TEXT]
    return toggle(header, children)


def build_stage_body(stage_name: str, section_keys: list[str], sections: dict):
    """Build the list of blocks for a single stage template."""
    blocks = []
    blocks.append(heading(1, stage_name))

    # Stage 4 (references) gets a special body — no questions, just a script
    if "References" in stage_name:
        blocks.append(callout(
            "Reference calls: candidate-volunteered only. NEVER call current employer per Kevin's promise. "
            "Keep the call to 10-15 minutes. Listen for tone, not just content — hesitation, vague praise, "
            "and the what's-missing matters more than the words.",
            emoji="📞",
        ))
        blocks.append(heading(2, "Script"))
        script_lines = [
            "Hi [Reference Name], this is Justin Miller with Excel Fire Protection. "
            "[Candidate] gave me your name as a reference. I'm calling about a journeyman sprinkler "
            "fitter position. Got 10 minutes?",
            "",
            "1. How do you know [candidate], and for how long?",
            "2. What kind of work did you do together — scope, crew size, role?",
            "3. Three words to describe them on a jobsite?",
            "4. Biggest strength you saw in them — with a specific story?",
            "5. Area where they could grow — with a specific example?",
            "6. Would you work with them again? (listen for enthusiasm vs. pause)",
            "7. Anything you'd want to know if you were in my shoes?",
        ]
        for line in script_lines:
            blocks.append(paragraph(line))
        blocks.append(divider())
        blocks.append(heading(2, "Reference call log"))
        blocks.append(paragraph("Reference 1 (name + relationship):"))
        blocks.append(paragraph(""))
        blocks.append(paragraph("Reference 2 (name + relationship):"))
        blocks.append(paragraph(""))
        blocks.append(paragraph("Reference 3 (name + relationship):"))
        blocks.append(paragraph(""))
        blocks.append(heading(2, "Decision"))
        blocks.append(paragraph("Proceed to offer / pause / pass — and why:"))
        blocks.append(paragraph(""))
        return blocks

    blocks.append(callout(
        "For each question: click to expand, read the listening-for guidance, write your "
        "observations in the blank paragraph underneath. The guidance is a calibration aid — "
        "not a grading key. A good answer doesn't have to match verbatim; it has to show the underlying signal.",
        emoji="📝",
    ))
    blocks.append(paragraph(""))

    for section_key in section_keys:
        # Find all subsections that start with this top-level section name
        matched = []
        for key, qs in sections.items():
            base = key.split(" :: ")[0]
            if base == section_key:
                matched.append((key, qs))
        if not matched:
            continue

        blocks.append(heading(2, section_key))

        for key, qs in matched:
            # If this key has a subsection suffix, emit it as H3
            if " :: " in key:
                _, sub = key.split(" :: ", 1)
                blocks.append(heading(3, sub))
            for q in qs:
                blocks.append(question_to_blocks(q))

    # Debrief section at the bottom
    blocks.append(divider())
    blocks.append(heading(2, "Debrief (post-interview, fill in immediately after hanging up)"))
    blocks.append(paragraph("Overall impression (thumbs up / thumbs sideways / thumbs down):"))
    blocks.append(paragraph(""))
    blocks.append(paragraph("Top 3 signals you saw:"))
    blocks.append(paragraph(""))
    blocks.append(paragraph("Top 3 concerns / red flags (if any):"))
    blocks.append(paragraph(""))
    blocks.append(paragraph("Decision: proceed to next stage / pause and discuss / pass:"))
    blocks.append(paragraph(""))
    blocks.append(paragraph("Next step + by when:"))
    blocks.append(paragraph(""))
    return blocks


# --- Chunked block append (Notion caps at 100 children per request) ---
def append_blocks_chunked(page_id: str, blocks: list, chunk=90):
    """Append blocks to a page, respecting the 100-child-per-request cap."""
    for i in range(0, len(blocks), chunk):
        batch = blocks[i : i + chunk]
        api("PATCH", f"/blocks/{page_id}/children", {"children": batch})
        time.sleep(0.4)  # gentle rate-limit buffer


def create_database(parent_page_id: str):
    """Create the EFP Interviews database (data source in 2025-09-03 API)."""
    body = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": "EFP Interviews"}}],
        "properties": {
            "Candidate": {"title": {}},
            "Email": {"email": {}},
            "Stage": {
                "select": {
                    "options": [
                        {"name": "Phone R1", "color": "blue"},
                        {"name": "Zoom R2", "color": "purple"},
                        {"name": "Working Day", "color": "orange"},
                        {"name": "References", "color": "yellow"},
                    ]
                }
            },
            "Date": {"date": {}},
            "Interviewer": {"rich_text": {}},
            "Decision": {
                "select": {
                    "options": [
                        {"name": "Yes", "color": "green"},
                        {"name": "Maybe", "color": "yellow"},
                        {"name": "No", "color": "red"},
                        {"name": "Needs more info", "color": "gray"},
                    ]
                }
            },
            "HireScore URL": {"url": {}},
            "Cycle": {"rich_text": {}},
            "Role": {
                "select": {
                    "options": [
                        {"name": "Journeyman Sprinkler Fitter", "color": "default"},
                        {"name": "Apprentice", "color": "default"},
                        {"name": "Foreman", "color": "default"},
                        {"name": "Project Manager", "color": "default"},
                    ]
                }
            },
            "Summary": {"rich_text": {}},
        },
    }
    # In 2025-09-03, databases are created via POST /v1/databases still (deprecated path)
    # OR POST /v1/data_sources with parent. Let's use the older /databases endpoint which
    # the 2025-09-03 API still supports.
    try:
        return api("POST", "/databases", body)
    except urllib.error.HTTPError:
        # Fall back to data_sources endpoint
        body_ds = {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "title": body["title"],
            "properties": body["properties"],
        }
        return api("POST", "/data_sources", body_ds)


def create_template_page(database_id: str, stage_name: str, body_blocks: list):
    """Create a page inside the database that acts as a filled-in template."""
    stage_select = stage_name.split(" —")[0].strip()
    page = api("POST", "/pages", {
        "parent": {"database_id": database_id},
        "properties": {
            "Candidate": {
                "title": [{"type": "text", "text": {"content": f"[TEMPLATE] {stage_name}"}}]
            },
            "Stage": {"select": {"name": "Template"}},
            "Role": {"select": {"name": "Journeyman Sprinkler Fitter"}},
        },
    })
    # Append blocks in chunks
    append_blocks_chunked(page["id"], body_blocks)
    return page


# If DB already exists and is set up via patch, set EXISTING_DB_ID here to skip creation.
EXISTING_DB_ID = "de21c644-f8bd-47cb-bd18-bc68ecb02e0a"
EXISTING_DB_URL = "https://www.notion.so/de21c644f8bd47cbbd18bc68ecb02e0a"


def main():
    print("Parsing question bank…")
    sections = parse_markdown(QUESTIONS_FILE)
    print(f"  Parsed {sum(len(v) for v in sections.values())} questions across {len(sections)} sections")

    if EXISTING_DB_ID:
        db_id = EXISTING_DB_ID
        db_url = EXISTING_DB_URL
        print(f"\nUsing existing database: {db_id}")
    else:
        print("\nCreating database under ai-space…")
        db = create_database(AI_SPACE_PAGE_ID)
        db_id = db["id"]
        db_url = db.get("url")
        print(f"  Database created: {db_id}")

    print("\nCreating per-stage template pages…")
    for stage_name, section_keys in STAGE_MAP.items():
        print(f"  - {stage_name}…")
        blocks = build_stage_body(stage_name, section_keys, sections)
        page = create_template_page(db_id, stage_name, blocks)
        print(f"      {page.get('url')}")
        print(f"      {len(blocks)} blocks appended")

    print("\nDone.")
    print(f"\nDatabase URL: {db_url}")


if __name__ == "__main__":
    main()
