"""
date_checker.py — BVRIT Date & Deadline Checker Tool

Extracts dates from retrieved knowledge base context, parses them,
and returns whether they are past, today, or upcoming with days remaining.

Usage (as module):
    from date_checker import check_dates_in_context, format_date_response
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional

# Today's date — used for all comparisons
def get_today() -> date:
    return date.today()


# ── Date pattern definitions ──────────────────────────────────────────────────

# Month name maps
MONTH_NAMES = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

# Regex patterns for date extraction — ordered from most to least specific
DATE_PATTERNS = [
    # DD Month YYYY  — e.g. "15 July 2026", "3rd April 2025"
    (r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(january|february|march|april|may|june|july|"
     r"august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"
     r"\s+(\d{4})\b", "dmy"),

    # Month DD, YYYY  — e.g. "July 15, 2026"
    (r"\b(january|february|march|april|may|june|july|"
     r"august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"
     r"\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", "mdy"),

    # DD/MM/YYYY or DD-MM-YYYY
    (r"\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\b", "dmy_num"),

    # YYYY-MM-DD (ISO)
    (r"\b(\d{4})-(\d{2})-(\d{2})\b", "iso"),

    # Month YYYY (no day — use 1st of month)
    (r"\b(january|february|march|april|may|june|july|"
     r"august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"
     r"\s+(\d{4})\b", "my"),

    # Academic year ranges — e.g. "2025-26", "2025-2026"
    (r"\b(20\d{2})[-–](20\d{2}|\d{2})\b", "ay"),
]

# Keywords that indicate a date is deadline/event related
DATE_CONTEXT_KEYWORDS = [
    "deadline", "last date", "due date", "closing date", "open", "opens",
    "closes", "start", "starts", "begin", "begins", "end", "ends",
    "exam", "test", "notification", "apply", "application", "admission",
    "counselling", "counseling", "registration", "schedule", "date",
    "event", "fest", "workshop", "ceremony", "convocation", "result",
    "merit list", "allotment", "reporting", "cutoff", "release",
]


def parse_date(text: str, pattern_type: str, groups: tuple) -> Optional[date]:
    """Parse a regex match into a date object."""
    try:
        if pattern_type == "dmy":
            day, month_str, year = int(groups[0]), groups[1].lower(), int(groups[2])
            return date(year, MONTH_NAMES[month_str], day)

        elif pattern_type == "mdy":
            month_str, day, year = groups[0].lower(), int(groups[1]), int(groups[2])
            return date(year, MONTH_NAMES[month_str], day)

        elif pattern_type == "dmy_num":
            day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
            if 1 <= month <= 12 and 1 <= day <= 31:
                return date(year, month, day)

        elif pattern_type == "iso":
            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
            return date(year, month, day)

        elif pattern_type == "my":
            month_str, year = groups[0].lower(), int(groups[1])
            return date(year, MONTH_NAMES[month_str], 1)

        # Academic year — return start date (Aug 1 of start year)
        elif pattern_type == "ay":
            start_year = int(groups[0])
            return date(start_year, 8, 1)

    except (ValueError, KeyError):
        return None

    return None


def get_surrounding_context(text: str, match_start: int, match_end: int, window: int = 120) -> str:
    """Extract text around a date match for context labelling."""
    start = max(0, match_start - window)
    end = min(len(text), match_end + window)
    snippet = text[start:end].strip()
    # Clean up whitespace
    snippet = re.sub(r"\s+", " ", snippet)
    return snippet


def infer_label(context_snippet: str) -> str:
    """Try to infer what kind of date this is from surrounding text."""
    s = context_snippet.lower()
    if any(w in s for w in ["admission", "apply", "application", "registration", "enroll"]):
        return "Admission / Application"
    if any(w in s for w in ["exam", "eamcet", "test", "entrance"]):
        return "Entrance Exam"
    if any(w in s for w in ["result", "merit", "rank", "allotment"]):
        return "Result / Allotment"
    if any(w in s for w in ["fee", "payment", "tuition"]):
        return "Fee Payment"
    if any(w in s for w in ["counselling", "counseling", "reporting"]):
        return "Counselling / Reporting"
    if any(w in s for w in ["fest", "event", "workshop", "seminar", "symposium"]):
        return "Event / Workshop"
    if any(w in s for w in ["convocation", "graduation", "ceremony"]):
        return "Ceremony"
    if any(w in s for w in ["deadline", "last date", "closing", "due date"]):
        return "Deadline"
    return "Date"


def classify_date(d: date, today: date) -> dict:
    """Classify a date as past, today, or upcoming and compute days."""
    delta = (d - today).days
    if delta < 0:
        return {
            "status": "past",
            "days": abs(delta),
            "label": f"Passed {abs(delta)} day{'s' if abs(delta) != 1 else ''} ago"
            if abs(delta) <= 365
            else f"Passed on {d.strftime('%d %b %Y')}",
        }
    elif delta == 0:
        return {"status": "today", "days": 0, "label": "Today!"}
    else:
        return {
            "status": "upcoming",
            "days": delta,
            "label": f"In {delta} day{'s' if delta != 1 else ''}"
            if delta <= 90
            else f"On {d.strftime('%d %b %Y')} ({delta} days away)",
        }


def check_dates_in_context(context: str, question: str = "") -> list[dict]:
    """
    Extract all dates from context text and classify them relative to today.
    """
    today = get_today()
    q = question.lower()
    asking_upcoming = any(w in q for w in ["when is", "deadline", "last date", "upcoming",
                                            "next", "schedule", "how many days left", "days remaining",
                                            "is it open", "still open", "closing"])
    asking_elapsed = any(w in q for w in ["since how many", "how long has", "how many days has",
                                           "been running", "how long ago", "since when"])

    found: list[dict] = []
    seen_dates: set[date] = set()

    for pattern, ptype in DATE_PATTERNS:
        for match in re.finditer(pattern, context, re.IGNORECASE):
            parsed = parse_date(match.group(), ptype, match.groups())
            if parsed is None or parsed in seen_dates:
                continue

            # Skip historical dates unless near a relevant keyword
            if parsed.year < 2025:
                snippet_check = get_surrounding_context(context, match.start(), match.end(), 80)
                if not any(kw in snippet_check.lower() for kw in DATE_CONTEXT_KEYWORDS):
                    continue

            # For academic year pattern, only use if it's 2025 or later
            if ptype == "ay" and parsed.year < 2025:
                continue

            seen_dates.add(parsed)
            snippet = get_surrounding_context(context, match.start(), match.end())
            classification = classify_date(parsed, today)
            event_label = infer_label(snippet)

            # If asking about upcoming, skip clearly irrelevant past dates
            if asking_upcoming and classification["status"] == "past" and classification["days"] > 60:
                continue

            found.append({
                "date": parsed,
                "date_str": parsed.strftime("%d %B %Y"),
                "event_label": event_label,
                "status": classification["status"],
                "days": classification["days"],
                "relative_label": classification["label"],
                "context_snippet": snippet,
                "asking_elapsed": asking_elapsed,
            })

    order = {"upcoming": 0, "today": 1, "past": 2}
    found.sort(key=lambda x: (order[x["status"]], x["days"] if x["status"] == "upcoming" else -x["days"]))
    return found


def format_date_response(dates: list[dict], question: str = "") -> str:
    """Format date check results as a human-readable markdown string."""
    today = get_today()
    q = question.lower()
    asking_elapsed = any(w in q for w in ["since how many", "how long has", "how many days has",
                                           "been running", "how long ago", "since when"])
    asking_upcoming = any(w in q for w in ["when is", "deadline", "last date", "upcoming",
                                            "next", "schedule", "days remaining", "still open"])

    # If asking for elapsed time — find the most relevant past date and compute
    if asking_elapsed and dates:
        past_dates = [d for d in dates if d["status"] == "past"]
        if past_dates:
            # Pick most recent past date (smallest days value = most recent)
            best = min(past_dates, key=lambda x: x["days"])
            lines = [
                f"## 📅 Duration Check — as of {today.strftime('%d %B %Y')}\n",
                f"The most relevant date found: **{best['date_str']}** ({best['event_label']})",
                f"That was **{best['days']} days ago** from today.",
            ]
            if best["days"] >= 365:
                years = best["days"] // 365
                rem = best["days"] % 365
                lines.append(f"That's approximately **{years} year{'s' if years>1 else ''} and {rem} days**.")
            lines.append(f"\n> {best['context_snippet'][:200]}…")
            lines.append("\n_Always verify with the official website or admissions office._")
            return "\n".join(lines)

    if not dates:
        return ""  # Signal to caller: no useful dates, skip the date block entirely

    # If asking about upcoming but only past dates found — skip the block
    if asking_upcoming and all(d["status"] == "past" for d in dates):
        return ""

    # If asking comparison but all past dates are stale (>90 days ago) — skip
    if all(d["status"] == "past" and d["days"] > 90 for d in dates):
        return ""

    lines = [f"## 📅 Date Check — as of {today.strftime('%d %B %Y')}\n"]

    upcoming = [d for d in dates if d["status"] in ("upcoming", "today")]
    past = [d for d in dates if d["status"] == "past"]

    if upcoming:
        lines.append("### ✅ Upcoming / Active")
        for d in upcoming:
            emoji = "🔴" if d["days"] <= 7 else "🟡" if d["days"] <= 30 else "🟢"
            lines.append(
                f"{emoji} **{d['date_str']}** — {d['event_label']}  \n"
                f"   _{d['relative_label']}_  \n"
                f"   > {d['context_snippet'][:180]}…\n"
            )

    if past and not asking_upcoming:
        lines.append("### ⏮ Past Dates")
        for d in past[:3]:
            lines.append(
                f"- **{d['date_str']}** — {d['event_label']} _{d['relative_label']}_"
            )

    lines.append(
        "\n_Dates extracted from retrieved knowledge base content. "
        "Always verify with the official website or admissions office for confirmed schedules._"
    )
    return "\n".join(lines)


if __name__ == "__main__":
    # Quick smoke test
    sample = """
    TSEAMCET 2026 applications open from 15 March 2026.
    Last date to apply without late fee: 10 April 2026.
    Hall ticket download: 25 April 2026.
    TSEAMCET exam date: 5 May 2026 to 8 May 2026.
    Results expected: June 2026.
    Counselling begins: 2026-07-15.
    Academic year 2026-27 commences: August 2026.
    Previous NAAC visit: March 2020.
    """
    results = check_dates_in_context(sample, "when is the admission deadline")
    print(format_date_response(results))
