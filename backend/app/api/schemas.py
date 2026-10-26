"""Request and response models that mirror the schemas in api/openapi.yaml.

Request models reject unknown fields (`additionalProperties: false`). The contract test
(MT-018) checks the responses against the contract itself.
"""

from __future__ import annotations

from datetime import datetime
from functools import cache
from typing import Annotated, Self
from uuid import UUID
from zoneinfo import available_timezones

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator


@cache
def _iana_timezones() -> frozenset[str]:
    return frozenset(available_timezones())


def _check_timezone(name: str) -> str:
    # Exact, case-sensitive match. ZoneInfo() alone would accept "europe/london" on a
    # case-insensitive file system and reject it on Linux.
    if name not in _iana_timezones():
        raise ValueError("must be an IANA timezone name, such as Africa/Harare")
    return name


Timezone = Annotated[str, AfterValidator(_check_timezone)]
DisplayName = Annotated[str, Field(min_length=1, max_length=80)]


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PartialUpdate(RequestModel):
    """A PATCH body: at least one field (`minProperties: 1`). A field that wasn't sent is None,
    so subclasses reject an explicit null for fields the contract doesn't mark nullable.
    """

    @model_validator(mode="after")
    def _at_least_one_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("send at least one field")
        return self


class PatientCreate(RequestModel):
    display_name: DisplayName
    timezone: Timezone


class PatientUpdate(PartialUpdate):
    display_name: DisplayName | None = None
    timezone: Timezone | None = None

    @field_validator("display_name", "timezone", mode="before")
    @classmethod
    def _not_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("can't be null")
        return value


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    timezone: str
    created_at: datetime
