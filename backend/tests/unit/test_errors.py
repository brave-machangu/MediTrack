from __future__ import annotations

import pytest

from app.errors import _field_path


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        (("body", "times_of_day", 0), "times_of_day[0]"),
        (("body", "schedule", "end_date"), "schedule.end_date"),
        (("query", "date"), "date"),
        (("path", "patient_id"), "patient_id"),
        (("body",), "request"),
    ],
)
def test_field_path_matches_contract_style(location: tuple[object, ...], expected: str) -> None:
    assert _field_path(location) == expected
