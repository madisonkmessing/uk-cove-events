"""
UK Cove — Weekly Events Aggregator
-----------------------------------
Pulls events from multiple sources, filters to things open to all UK students,
scores them for "college student appeal," and writes a ranked weekly JSON feed.
The single highest-scored event is flagged as the "top pick" for the hero slot.

SCHEDULE: runs every Sunday at 8:00 PM, picking the events for the coming week.
  - Cron line (server-local time):     0 20 * * 0 python3 weekly_events.py
  - See run_scheduler() at the bottom for a pure-Python alternative if you
    don't have access to a system cron (e.g. running this as a long-lived
    process or a single scheduled cloud function).

SOURCE STATUS (see chat for full explanation):
  - campus_rec    : WORKING — plain HTML, scraped directly below.
  - uk_athletics  : WORKING — server-rendered schedule page, scraped below.
  - visitlex      : STUB — structure not yet confirmed, fill in selectors once checked.
  - engage        : NOT IMPLEMENTED — requires UK to enable an RSS/iCal feed or grant
                    an Anthology/Campus Labs API key. This script has a slot ready
                    for it (see fetch_engage_events) once that access exists.
  - eventbrite    : NOT IMPLEMENTED — no public search API exists anymore, and
                    scraping their JS-rendered search pages sits in a ToS gray zone.
                    Left as a manual-curation slot (see MANUAL_EVENTS below) instead.

Install deps:
    pip install requests beautifulsoup4 schedule --break-system-packages
"""

import json
import re
import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

import requests
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Event:
    title: str
    source: str                      # "campus_rec" | "visitlex" | "engage" | "manual"
    start: Optional[str] = None      # ISO 8601 if known
    end: Optional[str] = None
    location: Optional[str] = None
    description: str = ""
    url: Optional[str] = None
    open_to_all_uk: bool = True      # filtered out downstream if False
    interest_signal: int = 0         # e.g. RSVP count, "going" count, attendance cap
    tags: list = field(default_factory=list)
    score: float = 0.0               # filled in by rank_events()
    is_top_pick: bool = False        # set on exactly one event — the hero slot


# ---------------------------------------------------------------------------
# Source 1: UK Campus Recreation events (working scraper — static HTML)
# ---------------------------------------------------------------------------

CAMPUS_REC_URL = "https://studentsuccess.uky.edu/campus-recreation/events"

def fetch_campus_rec_events() -> list[Event]:
    resp = requests.get(CAMPUS_REC_URL, timeout=15, headers={"User-Agent": "UKCoveBot/1.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    # NOTE: UK's Drupal events list currently renders one <article> or
    # <div class="event-teaser"> per event when events exist. Selector below
    # is a best-guess based on Drupal's common event-listing markup and
    # SHOULD BE VERIFIED/adjusted once the page actually has live events
    # (at the time of writing it shows "no upcoming events").
    cards = soup.select("article, .event-teaser, .views-row")

    for card in cards:
        title_el = card.select_one("h2, h3, .field--name-title")
        if not title_el:
            continue
        link_el = card.select_one("a")
        date_el = card.select_one("time, .date-display-single")

        events.append(Event(
            title=title_el.get_text(strip=True),
            source="campus_rec",
            start=date_el.get("datetime") if date_el else None,
            url=requests.compat.urljoin(CAMPUS_REC_URL, link_el["href"]) if link_el else None,
            description=card.get_text(" ", strip=True)[:300],
            open_to_all_uk=True,
            tags=["wellness", "fitness", "free"],
        ))
    return events


# ---------------------------------------------------------------------------
# Source 3: UK Athletics composite schedule (working scraper — server-rendered)
# ---------------------------------------------------------------------------

UK_ATHLETICS_URL = "https://ukathletics.com/all-sports-schedule/"

def fetch_uk_athletics_events() -> list[Event]:
    resp = requests.get(UK_ATHLETICS_URL, timeout=15, headers={"User-Agent": "UKCoveBot/1.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    # UK Athletics runs on the WMT Digital platform, which is server-rendered
    # (unlike Engage). Selectors below target the common WMT schedule-row
    # markup; VERIFY against the live page once you have scraper access set
    # up, since WMT's exact class names can vary by site config.
    rows = soup.select(".schedule-row, .c-schedule__row, tr")

    for row in rows:
        opponent_el = row.select_one(".schedule-opponent, .c-schedule__opponent, td")
        sport_el = row.select_one(".schedule-sport, .c-schedule__sport")
        date_el = row.select_one("time, .schedule-date, .c-schedule__date")
        link_el = row.select_one("a")

        if not opponent_el:
            continue

        title_text = opponent_el.get_text(strip=True)
        sport_text = sport_el.get_text(strip=True) if sport_el else ""
        full_title = f"Kentucky {sport_text} vs. {title_text}".strip() if sport_text else title_text

        events.append(Event(
            title=full_title,
            source="uk_athletics",
            start=date_el.get("datetime") if date_el else None,
            url=requests.compat.urljoin(UK_ATHLETICS_URL, link_el["href"]) if link_el else None,
            description=row.get_text(" ", strip=True)[:300],
            open_to_all_uk=True,
            tags=["sports", "school spirit"],
        ))
    return events


# ---------------------------------------------------------------------------
# Source 4: VisitLex calendar (STUB — confirm page structure before relying on this)
# ---------------------------------------------------------------------------

VISITLEX_URL = "https://www.visitlex.com/things-to-do/calendar-of-events/"

def fetch_visitlex_events() -> list[Event]:
    resp = requests.get(VISITLEX_URL, timeout=15, headers={"User-Agent": "UKCoveBot/1.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    # PLACEHOLDER SELECTORS — inspect the live page's HTML (view-source or
    # browser devtools) and replace these with the real class names before
    # trusting this in production. Left intentionally generic.
    cards = soup.select(".event-card, .tribe-events-list-event-row, article")

    for card in cards:
        title_el = card.select_one("h2, h3, .event-title")
        if not title_el:
            continue
        link_el = card.select_one("a")
        date_el = card.select_one("time")

        events.append(Event(
            title=title_el.get_text(strip=True),
            source="visitlex",
            start=date_el.get("datetime") if date_el else None,
            url=link_el["href"] if link_el else None,
            description=card.get_text(" ", strip=True)[:300],
            open_to_all_uk=True,   # community events — generally open, but not UK-specific
            tags=["community", "lexington"],
        ))
    return events


# ---------------------------------------------------------------------------
# Source 5: Engage (campuslabs) — NOT IMPLEMENTED, needs UK-side access
# ---------------------------------------------------------------------------

def fetch_engage_events(api_key: Optional[str] = None, ical_url: Optional[str] = None) -> list[Event]:
    """
    Two real options once UK grants access, neither usable without it:

    1. ical_url: if a UK admin enables a public iCal/RSS feed for Engage
       events (Admin > Events > Settings in Engage), parse it with the
       `icalendar` package here.

    2. api_key: if UK is an Anthology-licensed campus and approves a
       developer API key, call:
           https://engage-api.campuslabs.com/api/v3.0/discovery/event
       with header {"X-Engage-Api-Key": api_key}.

    Until one of those exists, this returns an empty list rather than
    guessing at private endpoints.
    """
    if not api_key and not ical_url:
        return []
    raise NotImplementedError("Wire this up once UK provides feed/API access.")


# ---------------------------------------------------------------------------
# Source 6: Eventbrite — manual curation slot (no reliable automated path)
# ---------------------------------------------------------------------------

# Add events here by hand each week (or have an ambassador/intern do it) until
# a compliant data source exists (e.g. asking specific organizers to submit
# directly, or an official Eventbrite partnership).
MANUAL_EVENTS: list[Event] = [
    # Event(title="Example trivia night", source="manual", start="2026-07-02T19:00:00",
    #       location="...", url="https://www.eventbrite.com/e/...", tags=["social"]),
]


# ---------------------------------------------------------------------------
# Filtering + ranking
# ---------------------------------------------------------------------------

COLLEGE_APPEAL_KEYWORDS = [
    "free", "student", "trivia", "open mic", "yoga", "wellness", "mental health",
    "social", "club", "intramural", "fitness", "music", "concert", "festival",
    "volunteer", "career", "networking", "food", "game night", "movie",
]

def looks_open_to_all(event: Event) -> bool:
    """Filter out anything that reads as restricted (members-only, RSO-internal, etc.)."""
    blocked_terms = ["members only", "invite only", "rso officers", "executive board"]
    text = f"{event.title} {event.description}".lower()
    return not any(term in text for term in blocked_terms)

def score_event(event: Event) -> float:
    text = f"{event.title} {event.description}".lower()
    keyword_hits = sum(1 for kw in COLLEGE_APPEAL_KEYWORDS if kw in text)

    score = keyword_hits * 2.0
    score += min(event.interest_signal, 500) / 50.0   # diminishing returns on raw popularity

    if event.source == "campus_rec":
        score += 1.5   # slight boost: official UK wellness programming aligns with Cove's mission
    if event.source == "uk_athletics":
        score += 2.0   # high, reliable draw — sporting events consistently pull big student turnout

    # "free" boosts appeal, but don't reward it for ticketed sources where the
    # text might mention "free t-shirt night" etc. while tickets still cost money
    if "free" in text and event.source != "uk_athletics":
        score += 1.5

    return round(score, 2)

def rank_events(events: list[Event]) -> list[Event]:
    filtered = [e for e in events if e.open_to_all_uk and looks_open_to_all(e)]
    for e in filtered:
        e.score = score_event(e)
    ranked = sorted(filtered, key=lambda e: e.score, reverse=True)

    # exactly one event (the highest scorer) gets the hero/"top pick" slot
    if ranked:
        ranked[0].is_top_pick = True

    return ranked


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_weekly_pull(output_path: str = "docs/events_this_week.json", top_n: int = 12):
    all_events: list[Event] = []

    try:
        all_events += fetch_campus_rec_events()
    except Exception as e:
        print(f"[warn] campus_rec fetch failed: {e}")

    try:
        all_events += fetch_uk_athletics_events()
    except Exception as e:
        print(f"[warn] uk_athletics fetch failed: {e}")

    try:
        all_events += fetch_visitlex_events()
    except Exception as e:
        print(f"[warn] visitlex fetch failed: {e}")

    all_events += fetch_engage_events()   # no-op until access exists
    all_events += MANUAL_EVENTS

    ranked = rank_events(all_events)[:top_n]

    output = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "week_of": datetime.date.today().isoformat(),
        "count": len(ranked),
        "events": [asdict(e) for e in ranked],
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    top = next((e for e in ranked if e.is_top_pick), None)
    print(f"Wrote {len(ranked)} ranked events to {output_path}")
    if top:
        print(f"Top pick: {top.title} (score {top.score})")


# ---------------------------------------------------------------------------
# Scheduling — runs every Sunday at 8:00 PM
# ---------------------------------------------------------------------------
#
# OPTION A (recommended for a real server/host): use system cron, since it
# survives reboots and doesn't require this script to run continuously.
#   1. Run:  crontab -e
#   2. Add:  0 20 * * 0 /usr/bin/python3 /path/to/weekly_events.py
#      (0 20 * * 0  =  minute 0, hour 20 (8 PM), any day-of-month, any
#       month, weekday 0 = Sunday)
#
# OPTION B (if you don't have cron access — e.g. a simple always-on process
# or container): use the `schedule` package below instead. This requires
# the script to keep running continuously (run_scheduler(), not run_weekly_pull()
# directly), so it's better suited to a small persistent worker than a
# serverless/cloud function.

def run_scheduler():
    import time
    import schedule

    schedule.every().sunday.at("20:00").do(run_weekly_pull)
    print("Scheduler started — will pick next week's events every Sunday at 8:00 PM.")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    import sys
    if "--schedule" in sys.argv:
        run_scheduler()
    else:
        run_weekly_pull()
