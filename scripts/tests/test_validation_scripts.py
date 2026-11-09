from __future__ import annotations

from pathlib import Path

from scripts import validate_json


def test_validate_json_reports_invalid_json(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"answer": NaN}', encoding="utf-8")

    assert validate_json.main([str(invalid)]) == 1
