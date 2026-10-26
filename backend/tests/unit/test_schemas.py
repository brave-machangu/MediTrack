"""Request models mirror api/openapi.yaml: AC-02 (timezone) and unknown fields."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.schemas import PatientCreate


@pytest.mark.parametrize(
    "name",
    [
        "Mars/Base",
        "europe/london",
        "Europe/London ",
        "",
        "../../etc/passwd",
        "localtime",
        "posixrules",
    ],
)
def test_unknown_or_wrong_case_timezone_rejected_ac02(name: str) -> None:
    with pytest.raises(ValidationError) as error:
        PatientCreate(display_name="Demo Patient A", timezone=name)
    assert [detail["loc"] for detail in error.value.errors()] == [("timezone",)]


@pytest.mark.parametrize(
    "name", ["Africa/Harare", "Europe/London", "UTC", "America/Argentina/Buenos_Aires"]
)
def test_iana_timezone_accepted(name: str) -> None:
    assert PatientCreate(display_name="Demo Patient A", timezone=name).timezone == name


def test_unknown_field_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        PatientCreate.model_validate(
            {"display_name": "Demo Patient A", "timezone": "UTC", "email": "demo@example.org"}
        )
    assert [detail["loc"] for detail in error.value.errors()] == [("email",)]
