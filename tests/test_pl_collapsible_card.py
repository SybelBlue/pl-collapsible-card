from __future__ import annotations

import importlib
from collections.abc import Mapping
from html import escape
from typing import Any, Literal

import lxml.html
import pytest

collapsible_card = importlib.import_module("pl-collapsible-card")


def markup(
    content: str = "Card content",
    **attributes: object,
) -> str:
    values = {"header": "Work", **attributes}
    serialized = " ".join(
        f'{name}="{escape(str(value), quote=True)}"'
        for name, value in values.items()
        if value is not None
    )
    return f"<pl-collapsible-card {serialized}>{content}</pl-collapsible-card>"


def question_data(
    partial_scores: Mapping[str, Mapping[str, object]] | None = None,
    panel: Literal["answer", "question", "submission"] = "question",
    num_valid_submissions: int = 0,
) -> dict[str, Any]:
    return {
        "partial_scores": partial_scores or {},
        "panel": panel,
        "num_valid_submissions": num_valid_submissions,
    }


def rendered_element(
    source: str,
    partial_scores: Mapping[str, Mapping[str, object]] | None = None,
    panel: Literal["answer", "question", "submission"] = "question",
    num_valid_submissions: int = 0,
) -> lxml.html.HtmlElement:
    rendered = collapsible_card.render(
        source,
        question_data(
            partial_scores,
            panel=panel,
            num_valid_submissions=num_valid_submissions,
        ),
    )
    return lxml.html.fragment_fromstring(rendered)


def elements_with_class(
    element: lxml.html.HtmlElement, class_name: str
) -> list[lxml.html.HtmlElement]:
    return element.xpath(
        './/*[contains(concat(" ", normalize-space(@class), " "), $class_name)]',
        class_name=f" {class_name} ",
    )


class TestValidation:
    def test_header_is_required(self) -> None:
        source = "<pl-collapsible-card>Content</pl-collapsible-card>"
        with pytest.raises(ValueError, match="header"):
            collapsible_card.prepare(source, question_data())

    @pytest.mark.parametrize("header", ["", "   "])
    def test_header_must_not_be_empty(self, header: str) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            collapsible_card.prepare(markup(header=header), question_data())

    def test_unknown_attribute_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unknown attribute"):
            collapsible_card.prepare(markup(unknown="value"), question_data())

    @pytest.mark.parametrize("width", ["25%", "50%", "75%", "auto"])
    def test_supported_width_is_accepted(self, width: str) -> None:
        collapsible_card.prepare(markup(width=width), question_data())

    def test_invalid_width_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid width"):
            collapsible_card.prepare(markup(width="100%"), question_data())

    @pytest.mark.parametrize("centered", ["true", "false"])
    def test_centered_accepts_boolean_values(self, centered: str) -> None:
        collapsible_card.prepare(markup(centered=centered), question_data())

    def test_invalid_centered_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="centered"):
            collapsible_card.prepare(markup(centered="sometimes"), question_data())

    @pytest.mark.parametrize(
        "attribute",
        ["include-in-correct-panel", "include-in-submission-panel"],
    )
    @pytest.mark.parametrize("value", ["auto", "true", "false"])
    def test_panel_inclusion_accepts_auto_or_boolean(
        self, attribute: str, value: str
    ) -> None:
        collapsible_card.prepare(markup(**{attribute: value}), question_data())

    @pytest.mark.parametrize(
        "attribute",
        ["include-in-correct-panel", "include-in-submission-panel"],
    )
    def test_panel_inclusion_rejects_other_values(self, attribute: str) -> None:
        with pytest.raises(ValueError, match=attribute):
            collapsible_card.prepare(
                markup(**{attribute: "sometimes"}), question_data()
            )

    @pytest.mark.parametrize("score_names", ["", "   ", "a,", ",a", "a,,b"])
    def test_explicit_score_names_reject_empty_entries(self, score_names: str) -> None:
        with pytest.raises(ValueError, match="nonempty names"):
            collapsible_card.prepare(
                markup(**{"score-names": score_names}), question_data()
            )


class TestCardRendering:
    def test_default_width_fills_the_available_horizontal_space(self) -> None:
        details = rendered_element(markup())

        assert "w-100" in details.get("class", "").split()
        assert "mx-auto" not in details.get("class", "").split()

    def test_narrow_card_is_centered_by_default(self) -> None:
        details = rendered_element(markup(width="50%"))

        assert "mx-auto" in details.get("class", "").split()

    def test_centered_false_leaves_narrow_card_at_inline_start(self) -> None:
        details = rendered_element(markup(width="50%", centered="false"))

        assert "mx-auto" not in details.get("class", "").split()

    def test_centered_true_does_not_add_margins_to_full_width_card(self) -> None:
        details = rendered_element(markup(width="auto", centered="true"))

        assert "mx-auto" not in details.get("class", "").split()

    def test_card_structure_matches_the_accessible_disclosure_order(self) -> None:
        source = markup(
            "<p>Body</p>",
            header="Overview",
            title="Title",
            subtitle="Subtitle",
            footer="Footer",
            **{
                "img-top-src": "top.png",
                "img-top-alt": "Top image",
                "img-bottom-src": "bottom.png",
                "img-bottom-alt": "Bottom image",
                "width": "50%",
            },
        )

        details = rendered_element(source)

        assert details.tag == "details"
        assert details.get("class") == "card w-50 my-4 mx-auto pl-collapsible-card"
        assert details[0].tag == "summary"
        assert details[0].text_content().strip() == "Overview"
        assert details[1].tag == "img"
        assert details[1].get("src") == "top.png"
        assert details[1].get("alt") == "Top image"
        assert elements_with_class(details, "card-title")[0].text_content().strip() == (
            "Title"
        )
        assert (
            elements_with_class(details, "card-subtitle")[0].text_content().strip()
            == "Subtitle"
        )
        assert (
            details.xpath('.//div[contains(@class, "card-body")]/p')[0].text_content()
            == "Body"
        )
        assert elements_with_class(details, "card-img-bottom")[0].get("alt") == (
            "Bottom image"
        )
        assert (
            elements_with_class(details, "card-footer")[0].text_content().strip()
            == "Footer"
        )

    def test_rich_header_and_footer_render_as_markup(self) -> None:
        details = rendered_element(
            markup(
                header="<strong>Overview</strong>",
                footer="<em>Footer</em>",
            )
        )

        assert details.xpath("./summary/strong")[0].text == "Overview"
        assert (
            details.xpath(
                './div[contains(concat(" ", normalize-space(@class), " "), " card-footer ")]/em'
            )[0].text
            == "Footer"
        )

    def test_image_values_are_escaped(self) -> None:
        details = rendered_element(
            markup(
                **{
                    "img-top-src": 'image.png?x=1&label="test"',
                    "img-top-alt": 'A "quoted" image',
                }
            )
        )

        image = elements_with_class(details, "card-img-top")[0]
        assert image.get("src") == 'image.png?x=1&label="test"'
        assert image.get("alt") == 'A "quoted" image'

    @pytest.mark.parametrize("panel", ["question", "submission"])
    def test_score_driven_open_state_applies_outside_correct_panel(
        self, panel: Literal["question", "submission"]
    ) -> None:
        source = markup('<pl-integer-input answers-name="a"></pl-integer-input>')
        details = rendered_element(source, {"a": {"score": 1.0}}, panel=panel)
        assert "open" not in details.attrib

    def test_multiple_instances_need_no_ids_or_aria_state(self) -> None:
        first = collapsible_card.render(markup(header="First"), question_data())
        second = collapsible_card.render(markup(header="Second"), question_data())
        parent = lxml.html.fragment_fromstring(first + second, create_parent=True)

        details = parent.xpath(
            './/details[contains(concat(" ", normalize-space(@class), " "), " pl-collapsible-card ")]'
        )
        assert len(details) == 2
        assert all("id" not in item.attrib for item in details)
        assert all("aria-expanded" not in item[0].attrib for item in details)
        assert all("open" in item.attrib for item in details)


class TestPanelRendering:
    TRACKED_SOURCE = markup('<pl-integer-input answers-name="a"></pl-integer-input>')

    @staticmethod
    def rendered_html(
        source: str,
        panel: Literal["answer", "question", "submission"],
        **attributes: object,
    ) -> str:
        return collapsible_card.render(
            markup(source, **attributes),
            question_data(
                {"a": {"score": 1.0}},
                panel=panel,
                num_valid_submissions=1,
            ),
        )

    def test_correct_panel_is_always_expanded_without_score_badges(self) -> None:
        details = rendered_element(
            self.TRACKED_SOURCE,
            {"a": {"score": 1.0}},
            panel="answer",
            num_valid_submissions=1,
        )

        assert "open" in details.attrib
        assert not elements_with_class(details, "pl-collapsible-card__score")

    @pytest.mark.parametrize("panel", ["answer", "submission"])
    def test_auto_excludes_read_only_card_from_result_panels(
        self, panel: Literal["answer", "submission"]
    ) -> None:
        assert self.rendered_html("Read-only content", panel) == ""

    @pytest.mark.parametrize(
        ("attribute", "panel"),
        [
            ("include-in-correct-panel", "answer"),
            ("include-in-submission-panel", "submission"),
        ],
    )
    def test_true_forces_read_only_card_into_result_panel(
        self,
        attribute: str,
        panel: Literal["answer", "submission"],
    ) -> None:
        assert self.rendered_html("Read-only content", panel, **{attribute: "true"})

    @pytest.mark.parametrize(
        ("attribute", "panel"),
        [
            ("include-in-correct-panel", "answer"),
            ("include-in-submission-panel", "submission"),
        ],
    )
    def test_false_excludes_tracked_card_from_result_panel(
        self,
        attribute: str,
        panel: Literal["answer", "submission"],
    ) -> None:
        assert (
            self.rendered_html(
                '<pl-integer-input answers-name="a"></pl-integer-input>',
                panel,
                **{attribute: "false"},
            )
            == ""
        )

    def test_panel_inclusion_settings_do_not_hide_question_panel(self) -> None:
        rendered = self.rendered_html(
            "Read-only content",
            "question",
            **{
                "include-in-correct-panel": "false",
                "include-in-submission-panel": "false",
            },
        )

        assert rendered


class TestScoreDrivenState:
    def test_no_tracked_answers_open_before_grading(self) -> None:
        assert "open" in rendered_element(markup()).attrib

    def test_no_tracked_answers_close_after_grading(self) -> None:
        assert "open" not in rendered_element(markup(), num_valid_submissions=1).attrib

    def test_automatic_discovery_finds_nested_answers(self) -> None:
        source = markup(
            '<div><pl-integer-input answers-name="a"></pl-integer-input></div>'
        )
        assert "open" not in rendered_element(source, {"a": {"score": 1.0}}).attrib

    @pytest.mark.parametrize("score", [None, 0.0, 0.5, 0.999])
    def test_ungraded_or_incomplete_answer_opens(self, score: object) -> None:
        source = markup('<pl-integer-input answers-name="a"></pl-integer-input>')
        assert "open" in rendered_element(source, {"a": {"score": score}}).attrib

    def test_missing_tracked_score_opens(self) -> None:
        source = markup(
            '<pl-integer-input answers-name="a"></pl-integer-input>'
            '<pl-integer-input answers-name="b"></pl-integer-input>'
        )
        assert "open" in rendered_element(source, {"a": {"score": 1.0}}).attrib

    def test_mixed_scores_open(self) -> None:
        source = markup(
            '<pl-integer-input answers-name="a"></pl-integer-input>'
            '<pl-integer-input answers-name="b"></pl-integer-input>'
        )
        scores = {"a": {"score": 1.0}, "b": {"score": 0.5}}
        assert "open" in rendered_element(source, scores).attrib

    def test_all_scores_correct_close(self) -> None:
        source = markup(
            '<pl-integer-input answers-name="a"></pl-integer-input>'
            '<pl-integer-input answers-name="b"></pl-integer-input>'
        )
        scores = {"a": {"score": 1.0}, "b": {"score": 1.0}}
        assert "open" not in rendered_element(source, scores).attrib

    def test_irrelevant_question_scores_are_ignored(self) -> None:
        source = markup('<pl-integer-input answers-name="a"></pl-integer-input>')
        scores = {"a": {"score": 1.0}, "outside": {"score": 0.0}}
        assert "open" not in rendered_element(source, scores).attrib

    def test_explicit_score_names_replace_automatic_discovery(self) -> None:
        source = markup(
            '<pl-integer-input answers-name="automatic"></pl-integer-input>',
            **{"score-names": "custom"},
        )
        scores = {"automatic": {"score": 0.0}, "custom": {"score": 1.0}}
        assert "open" not in rendered_element(source, scores).attrib

    def test_explicit_names_are_trimmed_and_deduplicated(self) -> None:
        source = markup(**{"score-names": " a, b, a "})
        scores = {"a": {"score": 1.0}, "b": {"score": 1.0}}
        assert "open" not in rendered_element(source, scores).attrib

    def test_math_isclose_matches_prairielearn_correctness_convention(self) -> None:
        source = markup('<pl-integer-input answers-name="a"></pl-integer-input>')
        assert (
            "open" not in rendered_element(source, {"a": {"score": 1.0 + 1e-12}}).attrib
        )

    def test_non_numeric_score_is_not_fully_correct(self) -> None:
        source = markup('<pl-integer-input answers-name="a"></pl-integer-input>')
        assert "open" in rendered_element(source, {"a": {"score": "invalid"}}).attrib


class TestAggregateScoreBadge:
    SOURCE = markup(
        '<pl-integer-input answers-name="a"></pl-integer-input>'
        '<pl-integer-input answers-name="b"></pl-integer-input>'
    )

    @staticmethod
    def badge(details: lxml.html.HtmlElement) -> lxml.html.HtmlElement | None:
        badges = elements_with_class(details, "pl-collapsible-card__score")
        return badges[0] if badges else None

    def test_no_tracked_answers_have_no_badge(self) -> None:
        assert self.badge(rendered_element(markup())) is None

    def test_no_tracked_answers_have_no_badge_after_grading(self) -> None:
        assert self.badge(rendered_element(markup(), num_valid_submissions=1)) is None

    def test_ungraded_or_partly_graded_answers_have_no_badge(self) -> None:
        assert self.badge(rendered_element(self.SOURCE)) is None
        assert self.badge(rendered_element(self.SOURCE, {"a": {"score": 1.0}})) is None

    def test_zero_score_uses_standard_red_badge(self) -> None:
        details = rendered_element(
            self.SOURCE, {"a": {"score": 0.0}, "b": {"score": 0.0}}
        )
        badge = self.badge(details)

        assert badge is not None
        assert "text-bg-danger" in badge.get("class", "").split()
        assert badge.text_content().strip() == "0%"
        assert "fa-times" in badge[0].get("class", "").split()
        assert badge[0].get("aria-hidden") == "true"

    def test_partial_score_uses_standard_yellow_badge(self) -> None:
        details = rendered_element(
            self.SOURCE, {"a": {"score": 1.0}, "b": {"score": 0.0}}
        )
        badge = self.badge(details)

        assert badge is not None
        assert "text-bg-warning" in badge.get("class", "").split()
        assert badge.text_content().strip() == "50%"
        assert "fa-circle" in badge[0].get("class", "").split()

    def test_full_score_uses_standard_green_badge(self) -> None:
        details = rendered_element(
            self.SOURCE, {"a": {"score": 1.0}, "b": {"score": 1.0}}
        )
        badge = self.badge(details)

        assert badge is not None
        assert "text-bg-success" in badge.get("class", "").split()
        assert badge.text_content().strip() == "100%"
        assert "fa-check" in badge[0].get("class", "").split()

    def test_badge_is_in_the_summary_after_the_header(self) -> None:
        details = rendered_element(
            self.SOURCE, {"a": {"score": 1.0}, "b": {"score": 1.0}}
        )
        badge = self.badge(details)

        assert badge is not None
        assert badge.getparent() is details[0]
        assert details[0].text_content().strip().startswith("Work")

    def test_component_weights_determine_the_aggregate(self) -> None:
        details = rendered_element(
            self.SOURCE,
            {
                "a": {"score": 1.0, "weight": 3},
                "b": {"score": 0.0, "weight": 1},
            },
        )
        badge = self.badge(details)

        assert badge is not None
        assert badge.text_content().strip() == "75%"
        assert "text-bg-warning" in badge.get("class", "").split()

    def test_zero_weight_component_is_excluded(self) -> None:
        details = rendered_element(
            self.SOURCE,
            {
                "a": {"score": 0.0, "weight": 0},
                "b": {"score": 1.0, "weight": 2},
            },
        )
        badge = self.badge(details)

        assert badge is not None
        assert badge.text_content().strip() == "100%"

    @pytest.mark.parametrize(
        "scores",
        [
            {"a": {"score": 1.0, "weight": 0}, "b": {"score": 0.0, "weight": 0}},
            {"a": {"score": "invalid"}, "b": {"score": 1.0}},
            {"a": {"score": 1.0, "weight": -1}, "b": {"score": 1.0}},
        ],
    )
    def test_invalid_aggregate_has_no_badge(
        self, scores: Mapping[str, Mapping[str, object]]
    ) -> None:
        assert self.badge(rendered_element(self.SOURCE, scores)) is None

    def test_unrelated_question_scores_do_not_affect_the_badge(self) -> None:
        details = rendered_element(
            self.SOURCE,
            {
                "a": {"score": 1.0},
                "b": {"score": 1.0},
                "outside": {"score": 0.0, "weight": 100},
            },
        )
        badge = self.badge(details)

        assert badge is not None
        assert badge.text_content().strip() == "100%"
