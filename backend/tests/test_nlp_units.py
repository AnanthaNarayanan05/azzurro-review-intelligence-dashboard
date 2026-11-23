"""Unit tests for the NLP building blocks. No database: these are pure functions."""

import pytest

from app.analytics import stats
from app.analytics.nlp.aspects import detect_aspects, load_lexicon
from app.analytics.nlp.preprocess import is_placeholder, split_sentences, substantive_sentences
from app.analytics.nlp.review_analysis import (
    analyse_review,
    detect_language,
    normalise_language,
)
from app.analytics.nlp.sentiment import VaderEngine, label_for
from app.models.base import AnalysisStatus, SentimentLabel, SourceField, TextSegment

LEXICON = load_lexicon()
ENGINE = VaderEngine()


def analyse(positive=None, negative=None, body=None, language=None):
    return analyse_review(
        positive_text=positive,
        negative_text=negative,
        body_text=body,
        language=language,
        lexicon=LEXICON,
        engine=ENGINE,
    )


# ------------------------------------------------------------------ placeholders and sentences
@pytest.mark.parametrize(
    "text",
    ["Nothing", "  nothing.  ", "N/A", "n.a.", "None!", "No comment", "Nothing to complain about"],
)
def test_placeholders_are_recognised(text):
    assert is_placeholder(text, LEXICON.placeholders)


@pytest.mark.parametrize("text", ["Everything", "Nothing but noise", "No hot water", "Good"])
def test_real_statements_are_not_placeholders(text):
    assert not is_placeholder(text, LEXICON.placeholders)


def test_everything_is_scored_not_skipped():
    assert substantive_sentences("Everything!", LEXICON.placeholders) == ["Everything!"]


def test_split_sentences_handles_punctuation_and_newlines():
    parts = split_sentences("Clean room. Staff were lovely!\nBreakfast was poor, but cheap?")
    assert parts == ["Clean room.", "Staff were lovely!", "Breakfast was poor, but cheap?"]


def test_split_sentences_empty_and_none():
    assert split_sentences("") == []
    assert substantive_sentences(None, LEXICON.placeholders) == []


# ------------------------------------------------------------------ sentiment
@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("The room was spotless and the staff were wonderful.", SentimentLabel.POSITIVE),
        ("The room was dirty and the bathroom smelled.", SentimentLabel.NEGATIVE),
        ("Breakfast was average.", SentimentLabel.NEUTRAL),
    ],
)
def test_vader_labels_obvious_sentences(text, label):
    assert label_for(ENGINE.score(text)) is label


def test_label_thresholds_are_inclusive_of_neutral_band():
    assert label_for(0.05) is SentimentLabel.POSITIVE
    assert label_for(0.049) is SentimentLabel.NEUTRAL
    assert label_for(-0.049) is SentimentLabel.NEUTRAL
    assert label_for(-0.05) is SentimentLabel.NEGATIVE


# ------------------------------------------------------------------ aspects
def keys(sentence):
    return {m.aspect_key for m in detect_aspects(sentence, LEXICON)}


def test_wildcard_matches_word_stems():
    assert "cleanliness" in keys("The room was cleaned daily")
    assert "cleanliness" in keys("Dirty carpets")


def test_terms_match_whole_words_only():
    assert "location" not in keys("The relocation was handled")
    assert "facilities" not in keys("The spaghetti was fine")  # 'spa' must not match inside a word


def test_exclusion_phrases_are_blanked_before_matching():
    assert "staff_service" not in keys("Room service was slow")
    assert "value_for_money" not in keys("A service charge was added")


def test_one_sentence_can_mention_several_aspects():
    assert {"location", "staff_service"} <= keys("Great location and friendly staff")


def test_bare_room_is_not_an_aspect():
    assert keys("The room was nice") == set()


def test_lexicon_has_version_and_eight_aspects():
    assert LEXICON.version
    assert len(LEXICON.aspects) == 8


# ------------------------------------------------------------------ language
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("en-GB", "en"),
        ("EN", "en"),
        ("en_US", "en"),
        ("fr", "fr"),
        ("", None),
        (None, None),
        ("1", None),
    ],
)
def test_language_codes_are_normalised(raw, expected):
    assert normalise_language(raw) == expected


def test_detects_clearly_non_english_text():
    assert detect_language("La chambre était très propre et le personnel très aimable.") == "fr"


def test_short_text_language_is_unknown():
    assert detect_language("Bon hotel") is None


# ------------------------------------------------------------------ whole-review analysis
def test_review_without_text_is_no_text():
    assert analyse().status is AnalysisStatus.NO_TEXT
    assert analyse(positive="Nothing", negative="N/A").status is AnalysisStatus.NO_TEXT


def test_declared_non_english_review_is_not_scored():
    result = analyse(positive="La chambre était propre", language="fr-FR")
    assert result.status is AnalysisStatus.NON_ENGLISH
    assert result.language == "fr"
    assert result.overall is None
    assert result.mentions == []


def test_detected_non_english_review_is_flagged_as_detected():
    result = analyse(positive="La chambre était très propre et le personnel très aimable.")
    assert result.status is AnalysisStatus.NON_ENGLISH
    assert result.language_was_detected


def test_declared_english_review_is_scored():
    result = analyse(positive="Lovely clean room, friendly staff.", language="en-GB")
    assert result.status is AnalysisStatus.ANALYSED
    assert not result.language_was_detected
    assert result.overall is not None
    assert result.overall.label is SentimentLabel.POSITIVE
    assert {s.segment for s in result.segments} == {TextSegment.POSITIVE}


def test_overall_is_mean_of_sentence_scores_across_boxes():
    result = analyse(positive="Lovely clean room.", negative="Staff were rude and unhelpful.")
    expected = (
        ENGINE.score("Lovely clean room.") + ENGINE.score("Staff were rude and unhelpful.")
    ) / 2
    assert result.overall.score == pytest.approx(expected)
    assert {s.segment for s in result.segments} == {TextSegment.POSITIVE, TextSegment.NEGATIVE}


def test_neutral_sentence_in_negative_box_becomes_a_negative_mention():
    # VADER scores this 0.0, but guests only write it in the "disliked" box when it was a problem.
    assert label_for(ENGINE.score("The wifi was slow and kept dropping.")) is SentimentLabel.NEUTRAL
    result = analyse(negative="The wifi was slow and kept dropping.")
    [mention] = result.mentions
    assert mention.aspect_key == "wifi_connectivity"
    assert mention.source_field is SourceField.NEGATIVE
    assert mention.label is SentimentLabel.NEGATIVE
    assert mention.evidence_text == "The wifi was slow and kept dropping."


def test_clear_sentence_keeps_its_own_label_in_the_other_box():
    result = analyse(negative="Great location though.")
    [mention] = result.mentions
    assert mention.label is SentimentLabel.POSITIVE


def test_neutral_sentence_in_positive_box_becomes_positive():
    result = analyse(positive="Breakfast was average.")
    [mention] = result.mentions
    assert mention.label is SentimentLabel.POSITIVE


def test_neutral_sentence_in_body_stays_neutral():
    result = analyse(body="Breakfast was average.")
    [mention] = result.mentions
    assert mention.label is SentimentLabel.NEUTRAL


# ------------------------------------------------------------------ statistics helpers
def test_mean_and_intervals():
    assert stats.mean([]) is None
    assert stats.mean([2, 4]) == 3
    assert stats.mean_interval([5]) is None
    low, high = stats.mean_interval([7, 8, 9, 8, 8, 7, 9, 8])
    assert low < 8 < high


def test_difference_of_proportions_matches_hand_calculation():
    result = stats.difference_of_proportions(30, 100, 10, 100)
    assert result["difference"] == pytest.approx(0.20)
    # margin = 1.96 * sqrt(0.3*0.7/100 + 0.1*0.9/100) = 1.96 * sqrt(0.003) = 0.10735
    assert result["ci_low"] == pytest.approx(0.20 - 0.10735, abs=1e-4)
    assert stats.excludes_zero(result)


def test_interval_that_spans_zero_is_not_significant():
    result = stats.difference_of_proportions(10, 40, 9, 40)
    assert not stats.excludes_zero(result)


def test_differences_need_data():
    assert stats.difference_of_means([5.0], [4.0, 6.0]) is None
    assert stats.difference_of_proportions(0, 0, 1, 2) is None
