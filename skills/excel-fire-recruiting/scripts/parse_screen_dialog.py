#!/usr/bin/env python3
"""Pull the deterministic fields out of a HireScore Screen-dialog description string.

The HireScore cycle detail page renders each applicant's Screen view as a modal whose
`role: dialog` node carries a long flattened string in its `description` attribute. That
string looks roughly like:

    "Download as PDF SCREEN WITH <position> <mm/dd/yyyy>
     <Full Name> <street> <City> <ST> <zip> <email> <10-digit phone>
     EDUCATION ... EXPERIENCE ... No expertise 1 - Expert 5 EXPERTISE ...
     POSITION: <position> SUBMITTED: <mm/dd/yyyy>"

This helper extracts only the fields that must be *deterministic* (contact info + section
splits). Narrative sections (education/experience/expertise) are returned as raw strings so
the calling agent can read them directly and pick *one* specific hook for the email.

Importable:

    from parse_screen_dialog import parse
    data = parse(dialog_description_text)

Runnable:

    $ python3 parse_screen_dialog.py < dialog.txt
"""

from __future__ import annotations

import json
import re
import sys
from typing import Optional


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(\d{10})(?!\d)")
ZIP_RE = re.compile(r"\b(\d{5})(?:-\d{4})?\b")
DATE_RE = re.compile(r"(\d{2}/\d{2}/\d{4})")


def _first_match(pattern: re.Pattern, text: str) -> Optional[str]:
    m = pattern.search(text)
    return m.group(0) if m else None


def parse(text: str) -> dict:
    """Return a dict with the extracted fields.

    Fields: name, email, phone, city, state, zip, position, submitted_on,
    highest_education, education_raw, experience_raw, expertise_raw, full_text.
    Missing fields come back as empty strings so the template step can detect and skip.
    """
    if not text:
        return {}

    clean = re.sub(r"\s+", " ", text).strip()

    out = {
        "name": "",
        "email": "",
        "phone": "",
        "city": "",
        "state": "",
        "zip": "",
        "position": "",
        "submitted_on": "",
        "education_raw": "",
        "experience_raw": "",
        "expertise_raw": "",
        "full_text": clean,
    }

    # Deterministic contact fields.
    email = _first_match(EMAIL_RE, clean)
    if email:
        out["email"] = email
    phone_m = PHONE_RE.search(clean)
    if phone_m:
        out["phone"] = phone_m.group(1)

    # Position + submitted date live in the footer.
    pos_m = re.search(r"POSITION:\s*(.*?)\s+SUBMITTED:\s*(\d{2}/\d{2}/\d{4})", clean)
    if pos_m:
        out["position"] = pos_m.group(1).strip()
        out["submitted_on"] = pos_m.group(2)

    # Section bodies as raw text; delimiters come from hirescore-dom-notes.md.
    def _section(start_token: str, end_tokens: list[str]) -> str:
        start = clean.find(start_token)
        if start == -1:
            return ""
        start += len(start_token)
        end = len(clean)
        for tok in end_tokens:
            pos = clean.find(tok, start)
            if pos != -1 and pos < end:
                end = pos
        return clean[start:end].strip()

    out["education_raw"] = _section("EDUCATION", ["EXPERIENCE", "No expertise 1 - Expert 5"])
    out["experience_raw"] = _section("EXPERIENCE", ["No expertise 1 - Expert 5", "EXPERTISE", "POSITION:"])
    # "EXPERTISE" appears TWICE: once as part of the legend ("No expertise 1 - Expert 5")
    # and once as the section header. Use the second occurrence.
    exp_header = clean.find("EXPERTISE", clean.find("No expertise 1 - Expert 5") + 1) if "No expertise 1 - Expert 5" in clean else clean.find("EXPERTISE")
    if exp_header != -1:
        exp_start = exp_header + len("EXPERTISE")
        exp_end = clean.find("POSITION:", exp_start)
        if exp_end == -1:
            exp_end = len(clean)
        out["expertise_raw"] = clean[exp_start:exp_end].strip()

    # Name, city, state, zip are the tricky parts. Work off the preamble (everything before
    # the word "EDUCATION"), subtract the known-good bits, and use the zip as an anchor.
    preamble = clean.split("EDUCATION", 1)[0]
    if email:
        preamble = preamble.replace(email, " ")
    if phone_m:
        preamble = preamble.replace(phone_m.group(1), " ")
    preamble = re.sub(r"\s+", " ", preamble).strip()

    STREET_SUFFIXES = {
        "street", "st", "avenue", "ave", "road", "rd", "drive", "dr", "lane", "ln",
        "way", "blvd", "boulevard", "court", "ct", "parkway", "pkwy", "place", "pl",
        "terrace", "ter", "trail", "trl", "circle", "cir", "highway", "hwy", "route",
        "rt", "rte", "loop",
    }
    zip_m = ZIP_RE.search(preamble)
    if zip_m:
        out["zip"] = zip_m.group(1)
        before = preamble[: zip_m.start()].strip().split()
        # State = last 2-letter uppercase token before zip
        if before and len(before[-1]) == 2 and before[-1].isupper():
            out["state"] = before.pop()
        # City: walk back capitalized tokens until we hit a digit (street number) or a
        # street-suffix token (e.g. "Street"), whichever comes first. Cap at 3 tokens to
        # avoid runaway multi-word city names on malformed inputs.
        city_tokens: list[str] = []
        while before and len(city_tokens) < 3:
            t = before[-1]
            if t.isdigit():
                break
            if t.lower().strip(".,") in STREET_SUFFIXES:
                # Leave the suffix (and everything before it) on `before` as street
                # context; the city is whatever we've already collected.
                break
            if not t[:1].isupper():
                break
            city_tokens.insert(0, before.pop())
        out["city"] = " ".join(city_tokens)
        # Name is everything before the street number. We approximate "street number" as
        # the first pure-digit token in `before`.
        for i, t in enumerate(before):
            if t.isdigit():
                name_tokens = before[:i]
                break
        else:
            name_tokens = before
        # Drop the leading "Download as PDF SCREEN WITH <position> <date>" chrome.
        text_before_name = " ".join(name_tokens)
        # cut everything up to and including the last mm/dd/yyyy date in that span
        last_date = None
        for m in DATE_RE.finditer(text_before_name):
            last_date = m
        if last_date:
            text_before_name = text_before_name[last_date.end():]
        out["name"] = text_before_name.strip()

    return out


def _main() -> int:
    text = sys.stdin.read()
    result = parse(text)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
