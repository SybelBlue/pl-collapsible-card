import prairielearn as pl


def generate(data: pl.QuestionData) -> None:
    data["correct_answers"] |= {
        "single_answer": "ready",
        "first_answer": "blue",
        "second_answer": "circle",
    }
