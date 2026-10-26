from __future__ import annotations

import pytest

from app.domain.errors import DomainError
from app.errors import DOMAIN_PROBLEMS, _field_path


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


def test_every_domain_error_has_a_problem_mapping() -> None:
    def subclasses(cls: type[DomainError]) -> set[type[DomainError]]:
        direct = set(cls.__subclasses__())
        return direct.union(*(subclasses(sub) for sub in direct))

    assert subclasses(DomainError) <= set(DOMAIN_PROBLEMS)
