import re
from typing import List, Tuple
from backend.app.schemas import PrivacyReport, RedactedEntity

# Regex patterns for deterministic, zero-overhead FERPA & PII scrubbing
PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    # UTD ID: 10-digit ID starting with 202 (e.g. 2025123456)
    ("UTD_ID", re.compile(r"\b202\d{7}\b"), "[REDACTED_UTD_ID]"),
    # Standard SSN: 123-45-6789 or 9-digit continuous SSN
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    # Email addresses
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    # Phone numbers: US formats with optional +1, parenthesis, dashes, dots
    ("PHONE", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED_PHONE]"),
]


def redact_pii(text: str) -> PrivacyReport:
    """
    Scrub FERPA and PII entities (UTD IDs, SSNs, emails, phone numbers)
    from user input before prompt construction and upstream inference.
    """
    if not text:
        return PrivacyReport(
            original_text="",
            sanitized_text="",
            redacted_count=0,
            entities=[],
        )

    all_matches: List[Tuple[int, int, str, str, str]] = []  # (start, end, entity_type, raw_text, replacement)

    for entity_type, pattern, replacement in PATTERNS:
        for match in pattern.finditer(text):
            all_matches.append((match.start(), match.end(), entity_type, match.group(0), replacement))

    # Sort matches by start position descending to replace without offset shifting
    # For overlaps, pick the longest match first
    all_matches.sort(key=lambda m: (m[0], -(m[1] - m[0])))

    # Filter out overlapping matches
    filtered_matches: List[Tuple[int, int, str, str, str]] = []
    last_end = -1
    # Sort ascending to deduplicate overlaps
    all_matches.sort(key=lambda m: (m[0], -(m[1] - m[0])))
    for m in all_matches:
        start, end, etype, raw, repl = m
        if start >= last_end:
            filtered_matches.append(m)
            last_end = end

    # Record entities in ascending order
    entities: List[RedactedEntity] = [
        RedactedEntity(
            entity_type=m[2],
            start=m[0],
            end=m[1],
            text=m[3],
        )
        for m in filtered_matches
    ]

    # Perform replacements from right to left
    sanitized = text
    for start, end, _, _, repl in reversed(filtered_matches):
        sanitized = sanitized[:start] + repl + sanitized[end:]

    return PrivacyReport(
        original_text=text,
        sanitized_text=sanitized,
        redacted_count=len(filtered_matches),
        entities=entities,
    )
