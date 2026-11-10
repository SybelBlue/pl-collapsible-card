# `pl-collapsible-card`

`pl-collapsible-card` presents PrairieLearn content in a Bootstrap card whose
header is a native HTML disclosure control. The card is open before grading and
whenever any answer it tracks is not fully correct. It is closed after every
tracked answer receives a score of `1.0`. Once every tracked answer has a score,
the header displays their weighted aggregate using PrairieLearn's standard
red, yellow, and green score badge. A read-only card with no tracked answers
also starts open, then closes without a badge after the first valid grading
reload.

```html
<pl-collapsible-card header="Part 1" title="Set up the integral" width="75%">
  <pl-symbolic-input
    answers-name="integrand"
    label="$f(x) =$"
    formula-editor="false"
  ></pl-symbolic-input>
</pl-collapsible-card>
```

## Install in a PrairieLearn course

Vendor the generated `release` branch at `elements/pl-collapsible-card`. With
[`pl-vendor`](https://pypi.org/project/pl-vendor/), configure the package to use:

```toml
[tool.pl-vendor.packages.pl-collapsible-card]
path = "elements/pl-collapsible-card"
url = "https://github.com/SybelBlue/pl-collapsible-card.git"
branch = "release"
```

The exact published commit is recorded in `plvendor.lock` alongside the
checked-in element tree.

The `main` branch is a complete PrairieLearn development course. The generated
`release` branch contains only the installable element, its tests, this guide,
the license, and the repository ignore rules.

## Develop and test

Install Python 3.13+, uv, pnpm 11.19+, GNU Make, and Docker Desktop. Then run:

```sh
make deps
make check
make dev
```

`make check` verifies vendored tooling, PrairieLearn compatibility, unit and
question lifecycle tests, schemas, formatting, Python types, and assessment
links. The QA course is under `questions/qa/pl-collapsible-card` and is listed
in the Collapsible Card QA gallery assessment.

The initial element and QA question were imported from
`SybelBlue/pl-oer-openstax-calcIII` commit
`d40fc04329f4ee79de4d4a7dbcccb9aacc681a8d`.

## Attributes

| Attribute | Default | Description |
| --- | --- | --- |
| `header` | required | Visible toggle label. It may contain display markup, but must contain meaningful visible text and no interactive controls. |
| `title` | empty | Card-body title. |
| `subtitle` | empty | Muted card-body subtitle. |
| `footer` | empty | Card footer content. |
| `img-top-src`, `img-top-alt` | empty | Image displayed below the disclosure header. Use meaningful alt text for an informative image or an empty alt for a decorative image. |
| `img-bottom-src`, `img-bottom-alt` | empty | Image displayed below the card body. |
| `width` | `auto` | Bootstrap width: `25%`, `50%`, `75%`, or `auto`. The default fills the available horizontal width. |
| `centered` | `true` | Horizontally centers cards whose width is `25%`, `50%`, or `75%`. It has no effect when `width="auto"`. |
| `include-in-correct-panel` | `auto` | Controls inclusion in the correct-answer panel. `auto` omits read-only cards; `true` or `false` forces inclusion or exclusion. |
| `include-in-submission-panel` | `auto` | Controls inclusion in the submission panel. `auto` omits read-only cards; `true` or `false` forces inclusion or exclusion. |
| `score-names` | automatic | Comma-separated grading names that replace automatic discovery. |

Without `score-names`, the element tracks every descendant `answers-name`.
With `score-names`, it tracks exactly the listed names, which supports custom
graders that do not expose `answers-name` in their markup.

Before grading, the card opens when there are no tracked names, a tracked score
is absent, or a tracked score is not fully correct. A grading render closes a
read-only card after the first valid submission. A card with tracked answers
closes only when every tracked name has a score numerically equal to `1.0`. The
browser owns the open/closed state between renders, so multiple cards on one
page toggle independently without JavaScript or shared IDs.

When all tracked scores are available, the header badge displays
`sum(score * weight) / sum(weight)`, with a missing weight treated as `1`.
An aggregate of 0% is red, a score strictly between 0% and 100% is yellow, and
100% is green. No aggregate badge is shown before grading, while a tracked score
is missing, when the combined weight is zero, or for read-only cards.

The correct-answer panel always expands included cards and never displays score
badges. By default, both the correct-answer and submission panels omit
read-only cards, since those cards have no result to display. Set the matching
`include-in-*-panel` attribute to `true` to include one anyway, or to `false` to
exclude a tracked card explicitly. These attributes do not affect the question
panel.
