import prairielearn as pl


def generate(data: pl.QuestionData) -> None:
    data["correct_answers"] |= {
        "single_answer": "ready",
        "first_answer": "blue",
        "second_answer": "circle",
    }


def grade(data: pl.QuestionData) -> None:
    data["partial_scores"]["single_answer"]["weight"] = 0
