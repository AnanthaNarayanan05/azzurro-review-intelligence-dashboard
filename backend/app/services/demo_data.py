"""Deterministic generator for SYNTHETIC demo reviews.

Everything produced here is invented. It exists so the dashboard can be demonstrated before a real
export is available. Every generated row carries ``Data origin = SYNTHETIC``, a ``SYN-`` review ID,
and is stored with ``is_synthetic = true`` and the source ``synthetic-demo``. It is never presented
as genuine guest feedback and never mixed into genuine totals.
"""

import csv
import io
import json
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from app.core.config import REPO_ROOT

DEMO_CONFIG_PATH = REPO_ROOT / "data" / "sample" / "demo_properties.json"
WEEKS = 26
RECENT_WINDOW_DAYS = 42  # "recent_drift" applies to reviews from the last six weeks
CSV_COLUMNS = [
    "Review ID",
    "Property",
    "Review Date",
    "Score",
    "Title",
    "Positive review",
    "Negative review",
    "Language",
    "Traveller type",
    "Data origin",
]

# aspect -> (positive phrases, negative phrases). Plain wording on purpose: these feed the
# keyword-based aspect detector and the sentiment engine, and they are obviously templated.
PHRASES: dict[str, tuple[list[str], list[str]]] = {
    "cleanliness": (
        [
            "The room was spotlessly clean.",
            "Everything felt fresh and very clean.",
            "Bathroom was immaculate and the sheets were crisp.",
        ],
        [
            "The room was dirty when we arrived.",
            "Found dust and stains on the carpet.",
            "The bathroom was not clean and had a musty smell.",
        ],
    ),
    "staff": (
        [
            "The reception staff were friendly and helpful.",
            "Staff went out of their way to help us.",
            "Lovely, welcoming team on the front desk.",
        ],
        [
            "The reception staff were rude and unhelpful.",
            "Staff seemed uninterested when we asked for help.",
            "Front desk ignored our request twice.",
        ],
    ),
    "check_in": (
        [
            "Check-in was quick and easy.",
            "Smooth check-in and early luggage storage.",
            "Check-out was fast with no fuss.",
        ],
        [
            "Check-in took far too long.",
            "We waited ages at check-in because the room was not ready.",
            "Check-out was slow and confusing.",
        ],
    ),
    "room_condition": (
        [
            "The room was modern and well presented.",
            "Nicely renovated room with good lighting.",
            "Room was spacious and tidy.",
        ],
        [
            "The room looked tired and worn.",
            "Furniture in the room was old and damaged.",
            "The room was small and dated.",
        ],
    ),
    "comfort": (
        [
            "The bed was very comfortable.",
            "Slept really well on the comfortable mattress.",
            "Pillows and bedding were great.",
        ],
        [
            "The bed was hard and uncomfortable.",
            "The mattress was lumpy and I slept badly.",
            "Pillows were flat and the room was too hot.",
        ],
    ),
    "noise": (
        ["It was quiet and peaceful at night.", "No noise problems at all."],
        [
            "Street noise kept us awake all night.",
            "Very noisy from the corridor and neighbouring rooms.",
            "Thin walls and loud noise late at night.",
        ],
    ),
    "facilities": (
        [
            "The gym and lounge facilities were great.",
            "Good facilities including a lovely rooftop.",
        ],
        ["The lift was often out of order.", "Facilities were limited and the gym was closed."],
    ),
    "location": (
        [
            "Excellent location close to transport and restaurants.",
            "Perfect location for exploring.",
            "Very convenient location and easy walk to the station.",
        ],
        [
            "The location was a bit far from the action.",
            "Inconvenient location with a long walk to transport.",
        ],
    ),
    "value": (
        ["Great value for money.", "Very good price for what you get."],
        ["Overpriced for the quality.", "Not good value for money."],
    ),
    "wifi": (
        ["Fast and reliable wifi throughout.", "The wifi was excellent for working."],
        ["The wifi kept dropping out.", "Wifi was slow and unreliable in the room."],
    ),
    "breakfast": (
        ["Breakfast was delicious with plenty of choice.", "Lovely breakfast and good coffee."],
        ["Breakfast was cold and limited.", "The breakfast was poor and overpriced."],
    ),
    "maintenance": (
        ["Everything in the room worked perfectly.", "No maintenance problems during our stay."],
        [
            "The air conditioning was broken.",
            "The shower leaked and the heater did not work.",
            "Broken light fittings and a faulty door lock.",
        ],
    ),
}
ASPECT_WEIGHTS = {
    "location": 7,
    "staff": 7,
    "cleanliness": 7,
    "comfort": 6,
    "room_condition": 5,
    "value": 4,
    "noise": 4,
    "check_in": 4,
    "facilities": 3,
    "wifi": 3,
    "breakfast": 3,
    "maintenance": 3,
}
TITLES = {
    "positive": ["Great stay", "Would stay again", "Lovely hotel", "Very happy with our stay"],
    "mixed": ["Good but a few issues", "Decent stay", "Mixed experience"],
    "negative": ["Disappointing", "Not as expected", "Would not recommend"],
}
# (positive text, language, rating): short non-English reviews to exercise language handling
FOREIGN = [
    ("Muy buena ubicación y personal amable.", "es", 9.0),
    ("Très propre et bien situé.", "fr", 8.8),
    ("Gutes Zimmer, freundliches Personal.", "de", 9.2),
]
TRAVELLER_TYPES = ["Couple", "Solo traveller", "Family", "Group of friends", "Business traveller"]


@dataclass(frozen=True)
class DemoProperty:
    code: str
    name: str
    listing_url: str | None
    quality: float
    aspect_bias: dict[str, float]
    recent_drift: dict[str, float]


def load_demo_properties(path: Path = DEMO_CONFIG_PATH) -> list[DemoProperty]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        DemoProperty(
            code=p["code"],
            name=p["name"],
            listing_url=p.get("listing_url"),
            quality=p["profile"]["quality"],
            aspect_bias=p["profile"].get("aspect_bias", {}),
            recent_drift=p["profile"].get("recent_drift", {}),
        )
        for p in raw["properties"]
    ]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def generate_rows(properties: list[DemoProperty], anchor: date, seed: int = 20260101) -> list[dict]:
    """Synthetic reviews for the last 26 weeks up to ``anchor``. Same inputs -> same output."""
    rows: list[dict] = []
    for prop in properties:
        rng = random.Random(f"{seed}:{prop.code}")
        days_ago_list: list[int] = list(
            range(14)
        )  # at least one review on each of the last 14 days
        for week in range(WEEKS):
            extra = rng.randint(4, 7) if week < 2 else rng.randint(2, 6)
            days_ago_list.extend(week * 7 + rng.randint(0, 6) for _ in range(extra))
        for days_ago in sorted(days_ago_list, reverse=True):
            review_date = anchor - timedelta(days=days_ago)
            rows.append(
                _make_review(rng, prop, review_date, days_ago < RECENT_WINDOW_DAYS, len(rows))
            )
    for index, row in enumerate(rows, start=1):  # stable, unique IDs
        row["Review ID"] = f"SYN-{row.pop('_code').upper()}-{index:05d}"
    return rows


def _make_review(
    rng: random.Random, prop: DemoProperty, review_date: date, recent: bool, serial: int
) -> dict:
    base = {
        "Property": prop.name,
        "Review Date": review_date.isoformat(),
        "Traveller type": rng.choice(TRAVELLER_TYPES),
        "Data origin": "SYNTHETIC",
        "_code": prop.code,
    }
    if rng.random() < 0.05:  # short non-English review
        text, language, rating = rng.choice(FOREIGN)
        return base | {
            "Score": f"{_clamp(rating + rng.uniform(-0.4, 0.4), 1, 10):.1f}",
            "Title": "",
            "Positive review": text,
            "Negative review": "",
            "Language": language,
        }

    aspects = list(ASPECT_WEIGHTS)
    chosen: list[str] = []
    wanted = rng.randint(2, 4)
    while len(chosen) < wanted:
        pick = rng.choices(aspects, weights=[ASPECT_WEIGHTS[a] for a in aspects])[0]
        if pick not in chosen:
            chosen.append(pick)

    positives: list[str] = []
    negatives: list[str] = []
    for aspect in chosen:
        p_pos = prop.quality + prop.aspect_bias.get(aspect, 0.0)
        if recent:
            p_pos += prop.recent_drift.get(aspect, 0.0)
        good_phrases, bad_phrases = PHRASES[aspect]
        if rng.random() < _clamp(p_pos, 0.05, 0.95):
            positives.append(rng.choice(good_phrases))
        else:
            negatives.append(rng.choice(bad_phrases))

    share_positive = len(positives) / len(chosen)
    rating = _clamp(5.4 + 4.4 * share_positive + rng.uniform(-0.9, 0.9), 2.0, 10.0)
    if not negatives:
        negative_text = rng.choice(["Nothing", "Nothing", "N/A", ""])
    else:
        negative_text = " ".join(negatives)
    positive_text = " ".join(positives) if positives else rng.choice(["Nothing", ""])
    if share_positive >= 0.75:
        title = rng.choice(TITLES["positive"])
    elif share_positive >= 0.4:
        title = rng.choice(TITLES["mixed"])
    else:
        title = rng.choice(TITLES["negative"])

    return base | {
        "Score": "" if rng.random() < 0.03 else f"{rating:.1f}",  # a few reviews have no score
        "Title": title if rng.random() < 0.85 else "",
        "Positive review": positive_text,
        "Negative review": negative_text,
        "Language": "en",
    }


def rows_to_csv(rows: list[dict]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def generate_csv(anchor: date | None = None, seed: int = 20260101) -> bytes:
    return rows_to_csv(generate_rows(load_demo_properties(), anchor or date.today(), seed))
