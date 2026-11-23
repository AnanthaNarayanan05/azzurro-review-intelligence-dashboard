"""Analyse one review: language check, per-segment and overall sentiment, aspect mentions with
evidence.

Pure functions: no database access, so the behaviour is easy to unit test.
"""

from dataclasses import dataclass, field

from langdetect import DetectorFactory, LangDetectException, detect_langs

from app.analytics.nlp.aspects import Lexicon, detect_aspects
from app.analytics.nlp.preprocess import substantive_sentences
from app.analytics.nlp.sentiment import SentimentEngine, label_for, mean
from app.models.base import AnalysisStatus, SentimentLabel, SourceField, TextSegment

DetectorFactory.seed = 0  # language detection is probabilistic; fix the seed so runs are repeatable

# Detection on very short text is unreliable, so below this length the language stays "unknown".
MIN_CHARS_FOR_DETECTION = 30
MIN_DETECTION_CONFIDENCE = 0.90

SEGMENTS = (
    (TextSegment.POSITIVE, SourceField.POSITIVE),
    (TextSegment.NEGATIVE, SourceField.NEGATIVE),
    (TextSegment.BODY, SourceField.BODY),
)


@dataclass(frozen=True)
class SegmentScore:
    segment: TextSegment
    score: float
    label: SentimentLabel


@dataclass(frozen=True)
class MentionResult:
    aspect_key: str
    source_field: SourceField
    score: float
    label: SentimentLabel
    evidence_text: str
    matched_term: str


@dataclass
class ReviewAnalysis:
    status: AnalysisStatus
    language: str | None = None
    language_was_detected: bool = False
    segments: list[SegmentScore] = field(default_factory=list)
    overall: SegmentScore | None = None
    mentions: list[MentionResult] = field(default_factory=list)


def normalise_language(code: str | None) -> str | None:
    """`en-GB`, `EN`, `en_US` -> `en`. Anything unusable -> None (unknown)."""
    if not code:
        return None
    primary = code.strip().lower().replace("_", "-").split("-")[0]
    return primary if 2 <= len(primary) <= 3 and primary.isalpha() else None


def detect_language(text: str) -> str | None:
    """Detected language code, or None when the text is too short or the detector is unsure."""
    if len(text) < MIN_CHARS_FOR_DETECTION:
        return None
    try:
        best = detect_langs(text)[0]
    except LangDetectException:
        return None
    return best.lang.split("-")[0] if best.prob >= MIN_DETECTION_CONFIDENCE else None


def _mention_label(sentence_label: SentimentLabel, field_: SourceField) -> SentimentLabel:
    """A neutral sentence takes the polarity of the Booking.com box it was written in.

    The "disliked" box means the guest is describing something they did not like, even when the
    wording
    is mild. A clearly positive or negative sentence keeps its own label. This is a documented,
    configurable
    rule that has not been evaluated yet (docs/AI_ANALYTICS.md section 5).
    """
    if sentence_label is SentimentLabel.NEUTRAL:
        if field_ is SourceField.NEGATIVE:
            return SentimentLabel.NEGATIVE
        if field_ is SourceField.POSITIVE:
            return SentimentLabel.POSITIVE
    return sentence_label


def analyse_review(
    *,
    positive_text: str | None,
    negative_text: str | None,
    body_text: str | None,
    language: str | None,
    lexicon: Lexicon,
    engine: SentimentEngine,
) -> ReviewAnalysis:
    texts = {
        SourceField.POSITIVE: positive_text,
        SourceField.NEGATIVE: negative_text,
        SourceField.BODY: body_text,
    }
    sentences = {f: substantive_sentences(t, lexicon.placeholders) for f, t in texts.items()}
    if not any(sentences.values()):
        return ReviewAnalysis(status=AnalysisStatus.NO_TEXT, language=normalise_language(language))

    known_language = normalise_language(language)
    detected = False
    if known_language is None:
        known_language = detect_language(" ".join(s for group in sentences.values() for s in group))
        detected = known_language is not None
    if known_language is not None and known_language != "en":
        return ReviewAnalysis(
            status=AnalysisStatus.NON_ENGLISH,
            language=known_language,
            language_was_detected=detected,
        )

    result = ReviewAnalysis(
        status=AnalysisStatus.ANALYSED, language=known_language, language_was_detected=detected
    )
    all_scores: list[float] = []
    for segment, source_field in SEGMENTS:
        scores = []
        for sentence in sentences[source_field]:
            score = engine.score(sentence)
            scores.append(score)
            sentence_label = label_for(score)
            for match in detect_aspects(sentence, lexicon):
                result.mentions.append(
                    MentionResult(
                        aspect_key=match.aspect_key,
                        source_field=source_field,
                        score=score,
                        label=_mention_label(sentence_label, source_field),
                        evidence_text=sentence,
                        matched_term=match.term,
                    )
                )
        if scores:
            segment_score = mean(scores)
            result.segments.append(SegmentScore(segment, segment_score, label_for(segment_score)))
            all_scores.extend(scores)

    overall = mean(all_scores)
    result.overall = SegmentScore(TextSegment.OVERALL, overall, label_for(overall))
    return result
