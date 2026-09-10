"""Map bounded resume text onto the existing Cyber Warrior schema.

Deliberately conservative. Every value returned must be traceable to a span of the
uploaded document: when a field cannot be read with confidence it is left empty
rather than guessed, because the citizen reviews and confirms these suggestions
and an invented degree or employer is worse than a blank field.

Contact details are never emitted. Name, mobile and email are identity-verified
fields elsewhere in the journey and must not be reachable from resume text.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

MAX_BIO_CHARS = 600
MAX_DESCRIPTION_CHARS = 400
MAX_ITEMS_PER_SECTION = 6
MAX_SKILLS = 20

SECTION_PATTERNS: dict[str, tuple[str, ...]] = {
    "summary": ("summary", "objective", "profile", "about me", "career objective"),
    "skills": ("skills", "technical skills", "core competencies", "areas of expertise", "expertise"),
    "education": ("education", "academic", "qualification", "qualifications", "academics"),
    "experience": ("experience", "work experience", "employment", "professional experience", "work history"),
    "certifications": ("certification", "certifications", "certificates", "licenses", "courses"),
}

DEGREE_TOKENS = (
    "bachelor", "master", "b.tech", "btech", "b.e", "be ", "m.tech", "mtech", "m.e",
    "b.sc", "bsc", "m.sc", "msc", "mba", "bca", "mca", "b.com", "m.com", "phd",
    "doctorate", "diploma", "b.a", "m.a", "higher secondary",
)
INSTITUTION_TOKENS = (
    "university", "institute", "college", "school", "academy", "polytechnic",
    "iit", "nit", "iiit", "vidyalaya", "campus",
)
ORGANISATION_TOKENS = (
    "ltd", "limited", "pvt", "private", "inc", "llp", "technologies", "technology",
    "solutions", "systems", "labs", "laboratories", "services", "consulting",
    "software", "infotech", "corporation", "company", "foundation", "centre", "center",
)
TITLE_TOKENS = (
    "engineer", "developer", "analyst", "intern", "manager", "consultant", "officer",
    "administrator", "architect", "specialist", "lead", "associate", "volunteer",
    "researcher", "trainee", "executive", "coordinator", "technician",
    "investigator", "auditor", "responder", "tester", "scientist",
)
CURRENT_TOKENS = ("present", "current", "till date", "to date", "ongoing")

BULLET = re.compile(r"^[\-•●▪\*·–—>\s]+")
SPLIT_SKILLS = re.compile(r"[,;|/•·]|\s{2,}")
# "Bengaluru, Karnataka" - a city/state pair, the only location shape we accept.
LOCATION = re.compile(r"^([A-Z][A-Za-z.\- ]{2,30}),\s*([A-Z][A-Za-z.\- ]{2,30})$")
DATE_RANGE = re.compile(
    r"(19|20)\d{2}\s*(?:-|–|—|to)\s*((19|20)\d{2}|present|current|till date|to date|ongoing)",
    re.IGNORECASE,
)
CONTACT = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|(?:\+?\d[\d\s\-()]{7,}\d)")


def _clean(line: str) -> str:
    return BULLET.sub("", line).strip()


def _heading_for(line: str) -> str | None:
    """Return the section a line introduces, if it reads like a heading."""
    text = _clean(line).lower().strip(":").strip()
    if not text or len(text) > 40:
        return None
    words = text.split()
    if len(words) > 4:
        return None
    for section, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            if text == pattern or text == pattern + "s" or text.startswith(pattern + " "):
                return section
    return None


def split_sections(text: str) -> dict[str, list[str]]:
    """Group non-empty lines under the last heading seen."""
    sections: dict[str, list[str]] = {name: [] for name in SECTION_PATTERNS}
    sections["header"] = []
    current = "header"
    for raw in text.split("\n"):
        line = _clean(raw)
        if not line:
            continue
        heading = _heading_for(raw)
        if heading:
            current = heading
            continue
        sections[current].append(line)
    return sections


def _has(line: str, tokens: Iterable[str]) -> bool:
    lowered = " " + line.lower() + " "
    return any(token in lowered for token in tokens)


def _strip_dates(line: str) -> str:
    return re.sub(r"\(?\b(19|20)\d{2}\b\s*(?:-|–|—|to)?\s*((19|20)\d{2}|present|current)?\)?", "", line, flags=re.IGNORECASE).strip(" ,-|–—")


def _location_from(lines: list[str]) -> str | None:
    """Find a "City, State" line.

    A job line such as "Security Analyst, Aegis Cyber Solutions Pvt Ltd" has the
    same comma shape as a city/state pair, so employer and job-title wording is
    rejected explicitly rather than trusted to the pattern alone.
    """
    for line in lines[:12]:
        candidate = _strip_dates(_clean(line))
        if CONTACT.search(candidate):
            continue
        if _has(candidate, ORGANISATION_TOKENS) or _has(candidate, TITLE_TOKENS):
            continue
        match = LOCATION.match(candidate)
        if match:
            return f"{match.group(1).strip()}, {match.group(2).strip()}"
    return None


def _bio_from(lines: list[str], exclude: str | None = None) -> str | None:
    # A location line often sits inside the summary block; it belongs to the
    # location field, not the bio.
    kept = [line for line in lines if exclude is None or _clean(line) != exclude]
    text = " ".join(kept).strip()
    if len(text) < 40:
        return None
    # Never carry a contact detail into the profile bio.
    text = CONTACT.sub("", text).strip()
    return text[:MAX_BIO_CHARS].strip() or None


def _skills_from(lines: list[str], known_skills: list[str] | None) -> list[str]:
    tokens: list[str] = []
    for line in lines:
        for piece in SPLIT_SKILLS.split(line):
            token = piece.strip(" .:-–—")
            if 2 <= len(token) <= 40 and not CONTACT.search(token):
                tokens.append(token)

    if known_skills:
        # Prefer the project's own catalog so the review screen can pre-select rows.
        catalog = {name.lower(): name for name in known_skills}
        haystack = " ".join(tokens).lower()
        matched = [name for lowered, name in catalog.items() if lowered in haystack]
        if matched:
            return _dedupe(matched)[:MAX_SKILLS]
    return _dedupe(tokens)[:MAX_SKILLS]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        key = value.lower()
        if key not in seen:
            seen.add(key)
            out.append(value)
    return out


def _education_from(lines: list[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for line in lines:
        if not _has(line, DEGREE_TOKENS) and not _has(line, INSTITUTION_TOKENS):
            continue
        cleaned = _strip_dates(line)
        parts = [part.strip() for part in re.split(r"[,|–—]|\s-\s", cleaned) if part.strip()]
        degree = next((part for part in parts if _has(part, DEGREE_TOKENS)), None)
        institution = next((part for part in parts if _has(part, INSTITUTION_TOKENS)), None)
        field = None
        if degree:
            match = re.search(r"\bin\s+([A-Za-z &]{3,40})", degree, re.IGNORECASE)
            if match:
                field = match.group(1).strip()
                degree = degree[: match.start()].strip(" ,-")
        if field is None:
            field = next((part for part in parts if part not in {degree, institution} and len(part) > 3), None)
        if not degree and not institution:
            continue
        entry = {"institution": institution, "degree": degree, "field_of_study": field}
        if entry not in entries:
            entries.append(entry)
        if len(entries) >= MAX_ITEMS_PER_SECTION:
            break
    return entries


def _experience_from(lines: list[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    pending: dict[str, Any] | None = None
    for line in lines:
        looks_like_heading = _has(line, ORGANISATION_TOKENS) or _has(line, TITLE_TOKENS) or bool(DATE_RANGE.search(line))
        if looks_like_heading:
            if pending:
                entries.append(pending)
                if len(entries) >= MAX_ITEMS_PER_SECTION:
                    return entries
            is_current = _has(line, CURRENT_TOKENS)
            cleaned = _strip_dates(line)
            parts = [part.strip() for part in re.split(r"[,|–—]|\s-\s|\sat\s", cleaned) if part.strip()]
            title = next((part for part in parts if _has(part, TITLE_TOKENS)), None)
            organisation = next((part for part in parts if _has(part, ORGANISATION_TOKENS) and part != title), None)
            if organisation is None:
                organisation = next((part for part in parts if part != title), None)
            if title is None and organisation is not None:
                # "<role>, <employer>" is the common shape; take the part that sits
                # before the employer rather than dropping the role entirely.
                index = parts.index(organisation) if organisation in parts else 0
                if index > 0:
                    title = parts[index - 1]
            pending = {
                "organization": organisation,
                "title": title,
                "description": None,
                "is_current": is_current,
            }
            continue
        if pending is not None:
            existing = pending["description"] or ""
            merged = (existing + " " + line).strip()
            pending["description"] = merged[:MAX_DESCRIPTION_CHARS]
    if pending and len(entries) < MAX_ITEMS_PER_SECTION:
        entries.append(pending)
    return [entry for entry in entries if entry.get("organization") or entry.get("title")]


def _certifications_from(lines: list[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for line in lines:
        cleaned = _strip_dates(line)
        if len(cleaned) < 3:
            continue
        issuer = None
        match = re.split(r"\s(?:-|–|—|\||by|from)\s", cleaned, maxsplit=1, flags=re.IGNORECASE)
        name = match[0].strip()
        if len(match) > 1 and match[1].strip():
            issuer = match[1].strip()
        if not name:
            continue
        entry = {"name": name[:120], "issuing_organization": issuer[:120] if issuer else None}
        if entry not in entries:
            entries.append(entry)
        if len(entries) >= MAX_ITEMS_PER_SECTION:
            break
    return entries


def structure_resume(text: str, known_skills: list[str] | None = None) -> dict[str, Any]:
    """Produce reviewable suggestions in the shape the review screen already reads."""
    sections = split_sections(text)
    # Only the header and summary blocks are trusted for a location; the experience
    # block is full of "Role, Employer" lines that mimic a city/state pair.
    location = _location_from(sections["header"]) or _location_from(sections["summary"])
    bio = _bio_from(sections["summary"], exclude=location)
    return {
        "profile": {"bio": bio, "location": location},
        "skills": _skills_from(sections["skills"], known_skills),
        "education": _education_from(sections["education"]),
        "experience": _experience_from(sections["experience"]),
        "certifications": _certifications_from(sections["certifications"]),
    }
