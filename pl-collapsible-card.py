from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Final, Literal

import chevron
import lxml.html
import prairielearn as pl

HERE: Final = Path(__file__).parent
TEMPLATE_PATH: Final = HERE / "pl-collapsible-card.mustache"

TITLE_DEFAULT: Final = ""
SUBTITLE_DEFAULT: Final = ""
FOOTER_DEFAULT: Final = ""
IMG_TOP_SRC_DEFAULT: Final = ""
IMG_TOP_ALT_DEFAULT: Final = ""
IMG_BOTTOM_SRC_DEFAULT: Final = ""
IMG_BOTTOM_ALT_DEFAULT: Final = ""
WIDTH_DEFAULT: Final = "auto"
VALID_WIDTHS: Final = frozenset({"25%", "50%", "75%", "auto"})
CENTERED_DEFAULT: Final = True
PANEL_INCLUSION_DEFAULT: Final = "auto"

type PanelInclusion = bool | Literal["auto"]

REQUIRED_ATTRIBS: Final = ["header"]
OPTIONAL_ATTRIBS: Final = [
    "title",
    "subtitle",
    "footer",
    "img-top-src",
    "img-top-alt",
    "img-bottom-src",
    "img-bottom-alt",
    "width",
    "centered",
    "include-in-correct-panel",
    "include-in-submission-panel",
    "score-names",
]


def _element(element_html: str) -> lxml.html.HtmlElement:
    return lxml.html.fragment_fromstring(element_html)


def _validate_header_and_width(element: lxml.html.HtmlElement) -> tuple[str, str]:
    header = pl.get_string_attrib(element, "header")
    if not header.strip():
        raise ValueError('Attribute "header" must not be empty.')

    width = pl.get_string_attrib(element, "width", WIDTH_DEFAULT)
    if width not in VALID_WIDTHS:
        raise ValueError(f"Invalid width: {width}.")

    return header, width


def _explicit_score_names(element: lxml.html.HtmlElement) -> tuple[str, ...] | None:
    if not pl.has_attrib(element, "score-names"):
        return None

    raw_names = pl.get_string_attrib(element, "score-names")
    names = [name.strip() for name in raw_names.split(",")]
    if not names or any(not name for name in names):
        raise ValueError(
            'Attribute "score-names" must be a comma-separated list of nonempty names.'
        )

    return tuple(dict.fromkeys(names))


def _automatic_score_names(element: lxml.html.HtmlElement) -> tuple[str, ...]:
    names = (
        descendant.attrib["answers-name"].strip()
        for descendant in element.iterdescendants()
        if "answers-name" in descendant.attrib
    )
    return tuple(dict.fromkeys(name for name in names if name))


def _score_names(element: lxml.html.HtmlElement) -> tuple[str, ...]:
    explicit_names = _explicit_score_names(element)
    if explicit_names is not None:
        return explicit_names
    return _automatic_score_names(element)


def _panel_inclusion(element: lxml.html.HtmlElement, attribute: str) -> PanelInclusion:
    value = pl.get_string_attrib(element, attribute, PANEL_INCLUSION_DEFAULT)
    if value == "auto":
        return "auto"
    return pl.get_boolean_attrib(element, attribute)


def _include_in_panel(setting: PanelInclusion, read_only: bool) -> bool:
    if setting == "auto":
        return not read_only
    return setting


def _is_fully_correct(score: Any) -> bool:
    if score is None:
        return False
    try:
        return math.isclose(float(score), 1.0)
    except (TypeError, ValueError):
        return False


def _should_open(
    score_names: tuple[str, ...],
    partial_scores: dict[str, Any],
    was_graded: bool,
) -> bool:
    if not score_names:
        return not was_graded

    return any(
        name not in partial_scores
        or not _is_fully_correct(partial_scores[name].get("score"))
        for name in score_names
    )


def _aggregate_score(
    score_names: tuple[str, ...], partial_scores: dict[str, Any]
) -> float | None:
    if not score_names:
        return None

    weighted_score = 0.0
    total_weight = 0.0
    for name in score_names:
        partial_score = partial_scores.get(name)
        if partial_score is None or partial_score.get("score") is None:
            return None

        try:
            score = float(partial_score["score"])
            weight = float(partial_score.get("weight", 1))
        except (TypeError, ValueError):
            return None

        if not math.isfinite(score) or not math.isfinite(weight) or weight < 0:
            return None

        weighted_score += score * weight
        total_weight += weight

    if total_weight <= 0:
        return None
    return weighted_score / total_weight


def _score_badge(score: float | None) -> dict[str, Any] | None:
    if score is None:
        return None
    if score >= 1:
        return {"correct": True}
    if score <= 0:
        return {"incorrect": True}
    return {"partial": round(score * 100)}


def _was_graded(data: pl.QuestionData) -> bool:
    return data.get("num_valid_submissions", 0) > 0


def prepare(element_html: str, data: pl.QuestionData) -> None:
    element = _element(element_html)
    pl.check_attribs(element, REQUIRED_ATTRIBS, OPTIONAL_ATTRIBS)
    _validate_header_and_width(element)
    pl.get_boolean_attrib(element, "centered", CENTERED_DEFAULT)
    _panel_inclusion(element, "include-in-correct-panel")
    _panel_inclusion(element, "include-in-submission-panel")
    _explicit_score_names(element)


def render(element_html: str, data: pl.QuestionData) -> str:
    element = _element(element_html)
    header, width = _validate_header_and_width(element)
    centered = pl.get_boolean_attrib(element, "centered", CENTERED_DEFAULT)
    score_names = _score_names(element)
    read_only = not score_names
    panel = data.get("panel", "question")
    include_in_correct_panel = _panel_inclusion(element, "include-in-correct-panel")
    include_in_submission_panel = _panel_inclusion(
        element, "include-in-submission-panel"
    )

    if panel == "answer" and not _include_in_panel(include_in_correct_panel, read_only):
        return ""
    if panel == "submission" and not _include_in_panel(
        include_in_submission_panel, read_only
    ):
        return ""

    partial_scores = data.get("partial_scores", {})
    was_graded = _was_graded(data)
    is_correct_panel = panel == "answer"

    title = pl.get_string_attrib(element, "title", TITLE_DEFAULT)
    subtitle = pl.get_string_attrib(element, "subtitle", SUBTITLE_DEFAULT)
    footer = pl.get_string_attrib(element, "footer", FOOTER_DEFAULT)
    img_top_src = pl.get_string_attrib(element, "img-top-src", IMG_TOP_SRC_DEFAULT)
    img_top_alt = pl.get_string_attrib(element, "img-top-alt", IMG_TOP_ALT_DEFAULT)
    img_bottom_src = pl.get_string_attrib(
        element, "img-bottom-src", IMG_BOTTOM_SRC_DEFAULT
    )
    img_bottom_alt = pl.get_string_attrib(
        element, "img-bottom-alt", IMG_BOTTOM_ALT_DEFAULT
    )

    html_params: dict[str, Any] = {
        "header": header,
        "subtitle": subtitle,
        "footer": footer,
        "img-top-src": img_top_src,
        "img-top-alt": img_top_alt,
        "img-bottom-src": img_bottom_src,
        "img-bottom-alt": img_bottom_alt,
        # A native <details> combined with Bootstrap's card styles does not
        # consistently stretch like pl-card in every parent layout. Make the
        # default explicit while preserving the requested percentage classes.
        "width": "100" if width == "auto" else width.removesuffix("%"),
        "centered": centered and width != "auto",
        "content": pl.inner_html(element),
        "open": is_correct_panel
        or _should_open(score_names, partial_scores, was_graded),
        "score_badge": (
            None
            if is_correct_panel
            else _score_badge(_aggregate_score(score_names, partial_scores))
        ),
    }
    # Empty strings still trigger a Chevron section, so omit an empty title.
    if title:
        html_params["title"] = {"title": title}

    with TEMPLATE_PATH.open(encoding="utf-8") as template:
        return chevron.render(template, html_params).strip()
