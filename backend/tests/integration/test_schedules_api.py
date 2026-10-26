"""Schedules API (FR-03, requirements §4.4): AC-05, AC-06, AC-34 and Lead decisions Q2 and Q3,
on SQLite and PostgreSQL. The fixed clock is Monday 2026-11-02 07:30 in Africa/Harare."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from tests.integration.helpers import (
    Json,
    add_dose_log,
    assert_problem,
    create_medication,
    create_patient,
)

SCHEDULES = "/api/v1/schedules"
DAILY_8AM = {"times_of_day": ["08:00"], "start_date": "2026-11-01"}
OVERLAP_DETAIL = (
    "This medication already has a schedule on those days. "
    "End the current schedule first; the new one can start the next day."
)
FIRST_DOSE = datetime(2026, 11, 1, 6, tzinfo=UTC)  # 2026-11-01 08:00 in Harare


def schedules_url(medication_id: str) -> str:
    return f"/api/v1/medications/{medication_id}/schedules"


def new_medication(api: TestClient) -> str:
    return str(create_medication(api, create_patient(api)["id"])["id"])


def create_schedule(api: TestClient, medication_id: str, **fields: object) -> Json:
    response = api.post(schedules_url(medication_id), json={**DAILY_8AM, **fields})
    assert response.status_code == 201, response.text
    body: Json = response.json()
    return body


def logged_schedule(api: TestClient, engine: Engine, **fields: object) -> Json:
    """A daily 08:00 schedule from 2026-11-01 whose first dose is logged."""
    schedule = create_schedule(api, new_medication(api), **fields)
    add_dose_log(engine, schedule["id"], FIRST_DOSE)
    return schedule


def test_new_schedule_has_contract_fields_and_defaults(api: TestClient) -> None:
    medication_id = new_medication(api)
    response = api.post(
        schedules_url(medication_id),
        json={"times_of_day": ["20:00", "08:00"], "start_date": "2026-11-01"},
    )

    assert response.status_code == 201
    schedule = response.json()
    assert schedule == {
        "id": schedule["id"],
        "medication_id": medication_id,
        "times_of_day": ["08:00", "20:00"],
        "days_of_week": [1, 2, 3, 4, 5, 6, 7],
        "start_date": "2026-11-01",
        "end_date": None,
        "grace_period_minutes": 60,
        "has_dose_logs": False,
    }
    assert api.get(schedules_url(medication_id)).json() == [schedule]
    assert api.get(f"/api/v1/medications/{medication_id}").json()["schedules"] == [schedule]


@pytest.mark.parametrize(
    ("fields", "field"),
    [
        ({"times_of_day": ["25:00"]}, "times_of_day[0]"),
        ({"times_of_day": ["8:00"]}, "times_of_day[0]"),
        ({"times_of_day": ["08:00", "08:00"]}, "times_of_day"),
        ({"times_of_day": []}, "times_of_day"),
        ({"times_of_day": [f"{hour:02d}:00" for hour in range(13)]}, "times_of_day"),
        ({"days_of_week": [0]}, "days_of_week[0]"),
        ({"days_of_week": [8]}, "days_of_week[0]"),
        ({"days_of_week": [1, 1]}, "days_of_week"),
        ({"days_of_week": ["1"]}, "days_of_week[0]"),
        ({"grace_period_minutes": 241}, "grace_period_minutes"),
        ({"grace_period_minutes": -1}, "grace_period_minutes"),
        ({"end_date": "2026-10-31"}, "end_date"),
        ({"start_date": None}, "start_date"),
        ({"note": "x"}, "note"),
    ],
    ids=[
        "25:00",
        "8:00",
        "duplicate-time",
        "no-times",
        "13-times",
        "day-0",
        "day-8",
        "duplicate-day",
        "day-as-string",
        "grace-241",
        "grace-minus-1",
        "end-before-start",
        "null-start",
        "unknown-field",
    ],
)
def test_invalid_schedule_is_rejected_ac05(api: TestClient, fields: Json, field: str) -> None:
    medication_id = new_medication(api)
    response = api.post(schedules_url(medication_id), json={**DAILY_8AM, **fields})
    problem = assert_problem(response, 422, "VALIDATION_ERROR")
    assert [error["field"] for error in problem["errors"]] == [field]
    assert api.get(schedules_url(medication_id)).json() == []


def test_schedules_are_listed_by_start_date(api: TestClient) -> None:
    medication_id = new_medication(api)
    later = create_schedule(api, medication_id, start_date="2026-12-01")
    earlier = create_schedule(api, medication_id, start_date="2026-11-01", end_date="2026-11-30")
    listed = [schedule["id"] for schedule in api.get(schedules_url(medication_id)).json()]
    assert listed == [earlier["id"], later["id"]]


@pytest.mark.parametrize(
    ("change", "stored"),
    [
        (
            {"times_of_day": ["21:00", "09:00"], "grace_period_minutes": 30},
            {"times_of_day": ["09:00", "21:00"], "grace_period_minutes": 30},
        ),
        (
            {"start_date": "2026-11-03", "days_of_week": [3, 1]},
            {"start_date": "2026-11-03", "days_of_week": [1, 3]},
        ),
    ],
    ids=["times-and-grace", "dates-and-days"],
)
def test_schedule_without_logs_can_be_edited_freely(
    api: TestClient, change: Json, stored: Json
) -> None:
    schedule = create_schedule(api, new_medication(api))

    response = api.patch(f"{SCHEDULES}/{schedule['id']}", json=change)

    assert response.status_code == 200
    assert response.json() == {**schedule, **stored}
    assert api.get(schedules_url(schedule["medication_id"])).json() == [{**schedule, **stored}]


@pytest.mark.parametrize(
    "change",
    [{"times_of_day": ["09:00"]}, {"grace_period_minutes": 30}, {"start_date": "2026-10-31"}],
    ids=["times", "grace", "start"],
)
def test_change_other_than_end_date_with_logs_rejected_ac06(
    api: TestClient, engine: Engine, change: Json
) -> None:
    schedule = logged_schedule(api, engine)
    response = api.patch(f"{SCHEDULES}/{schedule['id']}", json=change)
    assert_problem(response, 409, "SCHEDULE_HAS_LOGS")
    listed = api.get(schedules_url(schedule["medication_id"])).json()
    assert listed == [{**schedule, "has_dose_logs": True}]


def test_end_date_change_with_logs_ac06(api: TestClient, engine: Engine) -> None:
    schedule = logged_schedule(api, engine)
    url = f"{SCHEDULES}/{schedule['id']}"

    too_early = api.patch(url, json={"end_date": "2026-11-01"})  # before today
    on_today = api.patch(url, json={"end_date": "2026-11-02"})

    problem = assert_problem(too_early, 422, "VALIDATION_ERROR")
    assert [error["field"] for error in problem["errors"]] == ["end_date"]
    assert on_today.status_code == 200
    assert on_today.json() == {**schedule, "end_date": "2026-11-02", "has_dose_logs": True}


def test_unchanged_fields_resent_with_new_end_date_accepted(
    api: TestClient, engine: Engine
) -> None:
    # Lead decision Q3: resending a value isn't a change.
    schedule = logged_schedule(api, engine, times_of_day=["08:00", "20:00"])
    body = {
        "times_of_day": ["20:00", "08:00"],
        "days_of_week": [7, 6, 5, 4, 3, 2, 1],
        "start_date": "2026-11-01",
        "grace_period_minutes": 60,
        "end_date": "2026-11-05",
    }
    response = api.patch(f"{SCHEDULES}/{schedule['id']}", json=body)
    assert response.status_code == 200
    assert response.json()["end_date"] == "2026-11-05"


def test_end_date_can_be_cleared_with_logs(api: TestClient, engine: Engine) -> None:
    schedule = logged_schedule(api, engine, end_date="2026-11-05")
    response = api.patch(f"{SCHEDULES}/{schedule['id']}", json={"end_date": None})
    assert response.status_code == 200
    assert response.json()["end_date"] is None


def test_delete_with_logs_rejected_ac06(api: TestClient, engine: Engine) -> None:
    schedule = logged_schedule(api, engine)
    assert_problem(api.delete(f"{SCHEDULES}/{schedule['id']}"), 409, "SCHEDULE_HAS_LOGS")
    assert len(api.get(schedules_url(schedule["medication_id"])).json()) == 1


def test_delete_without_logs_ac06(api: TestClient) -> None:
    schedule = create_schedule(api, new_medication(api))
    response = api.delete(f"{SCHEDULES}/{schedule['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert api.get(schedules_url(schedule["medication_id"])).json() == []
    assert_problem(api.delete(f"{SCHEDULES}/{schedule['id']}"), 404, "NOT_FOUND")


def test_schedule_on_inactive_medication_rejected_ac06(api: TestClient) -> None:
    medication_id = new_medication(api)
    api.patch(f"/api/v1/medications/{medication_id}", json={"active": False})
    response = api.post(schedules_url(medication_id), json=DAILY_8AM)
    assert_problem(response, 409, "MEDICATION_INACTIVE")


def test_overlap_rejected_then_allowed_after_ending_old_schedule_ac34(api: TestClient) -> None:
    medication_id = new_medication(api)
    old = create_schedule(api, medication_id, times_of_day=["08:00"], start_date="2026-11-01")
    replacement = {"times_of_day": ["09:00"], "start_date": "2026-11-05"}

    overlap = api.post(schedules_url(medication_id), json=replacement)
    ended = api.patch(f"{SCHEDULES}/{old['id']}", json={"end_date": "2026-11-05"})
    still_overlapping = api.post(schedules_url(medication_id), json=replacement)
    next_day = api.post(
        schedules_url(medication_id), json={**replacement, "start_date": "2026-11-06"}
    )

    problem = assert_problem(overlap, 409, "SCHEDULE_OVERLAP")
    assert problem["detail"] == OVERLAP_DETAIL
    assert ended.status_code == 200
    assert_problem(still_overlapping, 409, "SCHEDULE_OVERLAP")
    assert next_day.status_code == 201


@pytest.mark.parametrize(
    ("first_days", "second_days"),
    [([1, 2, 3, 4, 5], [6, 7]), ([1, 3], [2, 4])],
    ids=["weekdays-and-weekend-ac34", "mon-wed-and-tue-thu-q2"],
)
def test_schedules_on_disjoint_weekdays_are_both_accepted(
    api: TestClient, first_days: list[int], second_days: list[int]
) -> None:
    medication_id = new_medication(api)
    create_schedule(api, medication_id, days_of_week=first_days)
    create_schedule(api, medication_id, times_of_day=["10:00"], days_of_week=second_days)
    assert len(api.get(schedules_url(medication_id)).json()) == 2


def test_patch_into_overlap_rejected_ac34(api: TestClient) -> None:
    medication_id = new_medication(api)
    create_schedule(api, medication_id, days_of_week=[1, 2, 3, 4, 5])
    weekend = create_schedule(api, medication_id, times_of_day=["10:00"], days_of_week=[6, 7])

    response = api.patch(f"{SCHEDULES}/{weekend['id']}", json={"days_of_week": [5, 6, 7]})

    assert_problem(response, 409, "SCHEDULE_OVERLAP")
    # Both start on the same date, so look the schedule up by id, not by list position.
    stored = {schedule["id"]: schedule for schedule in api.get(schedules_url(medication_id)).json()}
    assert stored[weekend["id"]]["days_of_week"] == [6, 7]


@pytest.mark.parametrize("new_end", ["2026-11-10", None], ids=["extended", "cleared"])
def test_extending_or_clearing_end_date_into_a_later_schedule_returns_overlap(
    api: TestClient, engine: Engine, new_end: str | None
) -> None:
    # Lead decision Q3's condition.
    old = logged_schedule(api, engine, end_date="2026-11-05")
    create_schedule(api, old["medication_id"], times_of_day=["09:00"], start_date="2026-11-06")
    response = api.patch(f"{SCHEDULES}/{old['id']}", json={"end_date": new_end})
    assert_problem(response, 409, "SCHEDULE_OVERLAP")


def test_schedules_of_different_medications_never_conflict(api: TestClient) -> None:
    patient_id = create_patient(api)["id"]
    for name in ("Demo Med Alpha", "Demo Med Beta"):
        medication_id = create_medication(api, patient_id, name=name)["id"]
        create_schedule(api, medication_id)


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({}, "request"),
        ({"times_of_day": None}, "times_of_day"),
        ({"grace_period_minutes": None}, "grace_period_minutes"),
        ({"start_date": "2026-12-01"}, "end_date"),  # after the stored end date
    ],
    ids=["empty-body", "null-times", "null-grace", "start-after-end"],
)
def test_invalid_schedule_update_is_rejected(api: TestClient, body: Json, field: str) -> None:
    schedule = create_schedule(api, new_medication(api), end_date="2026-11-30")
    response = api.patch(f"{SCHEDULES}/{schedule['id']}", json=body)
    problem = assert_problem(response, 422, "VALIDATION_ERROR")
    assert [error["field"] for error in problem["errors"]] == [field]


@pytest.mark.parametrize("missing_id", [str(uuid4()), "not-a-uuid"], ids=["unknown", "malformed"])
def test_missing_medication_or_schedule_is_not_found(api: TestClient, missing_id: str) -> None:
    assert_problem(api.get(schedules_url(missing_id)), 404, "NOT_FOUND")
    assert_problem(api.post(schedules_url(missing_id), json=DAILY_8AM), 404, "NOT_FOUND")
    patch = api.patch(f"{SCHEDULES}/{missing_id}", json={"end_date": None})
    assert_problem(patch, 404, "NOT_FOUND")
    assert_problem(api.delete(f"{SCHEDULES}/{missing_id}"), 404, "NOT_FOUND")
