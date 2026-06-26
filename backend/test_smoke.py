from fastapi.testclient import TestClient
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import Base, get_db
import models  # registers your tables on Base before we create them

# 1. A throwaway in-memory SQLite database
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# 2. A session factory bound to that test database
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Build the tables inside the test database
Base.metadata.create_all(bind=engine)


# 4. Make the app use the test DB instead of the real one
def override_get_db():
    """Yield a session connected to the in-memory test database."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_database():
    """Give each test a fresh, empty DB with one seeded employee."""
    Base.metadata.drop_all(bind=engine)    # wipe everything
    Base.metadata.create_all(bind=engine)  # rebuild empty tables
    db = TestingSessionLocal()
    db.add(models.Employee(name="Test Employee"))  # re-seed employee id 1
    db.commit()
    db.close()
    yield   # ← the test runs at this point

# HEALTH CHECK — list employees
def test_list_employees():
    """The /employees endpoint responds with 200 OK."""
    response = client.get("/employees")   # hit the employees endpoint your frontend uses
    assert response.status_code == 200    # 200 means "OK / success"

# HAPPY PATH — create a valid request (201)
def test_create_leave_request():
    """POSTing a valid request creates a DRAFT and returns 201."""
    response = client.post("/leave-requests", json={
        "employee_id": 1,            # the employee seeded above — a number, no quotes
        "leave_type": "Vacation",    # a real type string
        "start_date": "2026-07-01",  # future dates — the validator rejects past start dates
        "end_date": "2026-07-03",
        "reason": "Family trip",     # any short string
    })
    assert response.status_code == 201       # your create endpoint returns 201 Created (not 200)
    data = response.json()                   # parse the returned request into a Python dict
    assert data["status"] == "DRAFT"         # the server forces every new request to DRAFT
    assert data["number_of_days"] == 3       # 07-01 → 07-03 inclusive = 3 days

# REJECTION — create for a missing employee (404)
def test_create_for_nonexistent_employee():
    """Creating a request for an employee that doesn't exist returns 404."""
    response = client.post("/leave-requests", json={
        "employee_id": 999,          # nobody with this id was seeded (only id 1 exists)
        "leave_type": "Vacation",
        "start_date": "2026-07-01",
        "end_date": "2026-07-03",
        "reason": "Family trip",
    })
    assert response.status_code == 404   # 404 = "that employee was not found"

# TRANSITION GUARD — approve a draft (409)
def test_approve_draft_returns_409():
    """Approving a request that's still a DRAFT returns 409."""
    # 1. create a draft
    create = client.post("/leave-requests", json={
        "employee_id": 1,
        "leave_type": "Vacation",
        "start_date": "2026-07-01",
        "end_date": "2026-07-03",
        "reason": "Family trip",
    })
    request_id = create.json()["id"]   # pull the new request's id from the response

    # 2. try to approve it while it's still DRAFT
    response = client.post(f"/leave-requests/{request_id}/approve")

    # 3. that's an illegal jump (approve is only legal from SUBMITTED) -> rejected
    assert response.status_code == 409   # 409 Conflict = "not allowed in this state"

# VALIDATION — end date before start (422)
def test_end_before_start_returns_422():
    """Creating a request with the end date before the start date returns 422."""
    response = client.post("/leave-requests", json={
        "employee_id": 1,
        "leave_type": "Vacation",
        "start_date": "2026-07-03",  # start is AFTER end — invalid range
        "end_date": "2026-07-01",
        "reason": "Family trip",
    })
    assert response.status_code == 422   # 422 = validation failed

# VALIDATION — past start date (422)
def test_past_start_date_returns_422():
    """Creating a request with a start date in the past returns 422."""
    response = client.post("/leave-requests", json={
        "employee_id": 1,
        "leave_type": "Vacation",
        "start_date": "2020-01-01",  # well before today (2026-06-22) — invalid
        "end_date": "2020-01-03",    # kept after start so ONLY the past-date rule trips
        "reason": "Family trip",
    })
    assert response.status_code == 422

# BUSINESS RULE — overlapping approval, same employee (409)
def test_overlapping_approval_returns_409():
    """Approving a leave that overlaps an already-approved one (same employee) returns 409."""
    # --- Request A: create -> submit -> approve, so it ends up APPROVED ---
    a = client.post("/leave-requests", json={
        "employee_id": 1,
        "leave_type": "Vacation",
        "start_date": "2026-08-01",
        "end_date": "2026-08-05",
        "reason": "First leave",
    })
    a_id = a.json()["id"]
    client.post(f"/leave-requests/{a_id}/submit")            # DRAFT -> SUBMITTED
    approve_a = client.post(f"/leave-requests/{a_id}/approve")  # SUBMITTED -> APPROVED
    assert approve_a.status_code == 200    # sanity: confirm A actually got approved

    # --- Request B: same employee, dates that OVERLAP A (08-01..08-05) ---
    b = client.post("/leave-requests", json={
        "employee_id": 1,            # same employee as A
        "leave_type": "Vacation",
        "start_date": "2026-08-03",  # 08-03 falls inside A's 08-01..08-05 → overlap
        "end_date": "2026-08-07",
        "reason": "Second leave",
    })
    b_id = b.json()["id"]                              # grab B's id
    client.post(f"/leave-requests/{b_id}/submit")      # DRAFT -> SUBMITTED
    approve_b = client.post(f"/leave-requests/{b_id}/approve")  # this is the one that should fail

    # B overlaps an already-APPROVED leave → the rule blocks it
    assert approve_b.status_code == 409   # 409 Conflict

# BUSINESS RULE — boundary overlap: B ends exactly on A's start (409) [BUG-3 regression]
def test_boundary_overlap_approval_returns_409():
    """Approving a leave that ends exactly on an approved leave's start day returns 409."""
    # --- Request A: approved, 04-10 .. 04-15 ---
    a = client.post("/leave-requests", json={
        "employee_id": 1, "leave_type": "Vacation",
        "start_date": "2027-04-10", "end_date": "2027-04-15",
        "reason": "First leave",
    })
    a_id = a.json()["id"]
    client.post(f"/leave-requests/{a_id}/submit")
    approve_a = client.post(f"/leave-requests/{a_id}/approve")
    assert approve_a.status_code == 200   # sanity: A is actually approved

    # --- Request B: ends ON A's start date (04-10) — the exact boundary that BUG-3 missed ---
    b = client.post("/leave-requests", json={
        "employee_id": 1, "leave_type": "Vacation",
        "start_date": "2027-04-06", "end_date": "2027-04-10",  # touches A's start, doesn't go past it
        "reason": "Second leave",
    })
    b_id = b.json()["id"]
    client.post(f"/leave-requests/{b_id}/submit")
    approve_b = client.post(f"/leave-requests/{b_id}/approve")

    # the single shared day (04-10) is still an overlap -> blocked
    assert approve_b.status_code == 409

# VALIDATION — submit without a reason (422)
def test_submit_without_reason_returns_422():
    """Submitting a request that has no reason returns 422."""
    # create a draft with an EMPTY reason — allowed at create, but submit requires one
    create = client.post("/leave-requests", json={
        "employee_id": 1,
        "leave_type": "Vacation",
        "start_date": "2026-07-01",
        "end_date": "2026-07-03",
        "reason": "",
    })
    request_id = create.json()["id"]

    # submit should be rejected because there's no reason
    response = client.post(f"/leave-requests/{request_id}/submit")
    assert response.status_code == 422

# TRANSITION GUARD — cancel an approved request (409)
def test_cancel_approved_returns_409():
    """Cancelling a request that's already APPROVED returns 409."""
    # create -> submit -> approve, so it ends up APPROVED
    create = client.post("/leave-requests", json={
        "employee_id": 1,
        "leave_type": "Vacation",
        "start_date": "2026-09-01",   # NOTE: away from the overlap test's 08-01..08-05
        "end_date": "2026-09-03",
        "reason": "Approved leave",
    })
    request_id = create.json()["id"]
    client.post(f"/leave-requests/{request_id}/submit")    # DRAFT -> SUBMITTED
    client.post(f"/leave-requests/{request_id}/approve")   # SUBMITTED -> APPROVED

    # cancel is only legal from DRAFT/SUBMITTED, so an APPROVED one is rejected
    response = client.post(f"/leave-requests/{request_id}/cancel")
    assert response.status_code == 409

# TRANSITION GUARD — edit a non-draft (409)
def test_edit_non_draft_returns_409():
    """Editing a request that's no longer a DRAFT returns 409."""
    # create -> submit, so it's SUBMITTED (no longer editable)
    create = client.post("/leave-requests", json={
        "employee_id": 1,
        "leave_type": "Vacation",
        "start_date": "2026-10-01",
        "end_date": "2026-10-03",
        "reason": "To submit",
    })
    request_id = create.json()["id"]
    client.post(f"/leave-requests/{request_id}/submit")   # DRAFT -> SUBMITTED

    # editing is only allowed on DRAFT, so a PATCH now should be rejected
    response = client.patch(f"/leave-requests/{request_id}", json={"reason": "Changed reason"})
    assert response.status_code == 409

# HAPPY TRANSITION — submit a draft (200 / SUBMITTED)
def test_submit_draft_returns_200():
    """Submitting a draft that has a reason returns 200 and status SUBMITTED."""
    create = client.post("/leave-requests", json={
        "employee_id": 1, "leave_type": "Vacation",
        "start_date": "2026-07-10", "end_date": "2026-07-12",
        "reason": "Family trip",   # has a reason, so submit is allowed
    })
    request_id = create.json()["id"]
    response = client.post(f"/leave-requests/{request_id}/submit")
    assert response.status_code == 200
    assert response.json()["status"] == "SUBMITTED"

# HAPPY TRANSITION — approve a submitted request (200 / APPROVED)
def test_approve_submitted_returns_200():
    """Approving a submitted request returns 200 and status APPROVED."""
    create = client.post("/leave-requests", json={
        "employee_id": 1, "leave_type": "Vacation",
        "start_date": "2026-11-01", "end_date": "2026-11-03",  # November — clear of earlier approved leaves
        "reason": "Approved leave",
    })
    request_id = create.json()["id"]
    client.post(f"/leave-requests/{request_id}/submit")
    response = client.post(f"/leave-requests/{request_id}/approve")
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"

# HAPPY TRANSITION — reject a submitted request (200 / REJECTED)
def test_reject_submitted_returns_200():
    """Rejecting a submitted request returns 200 and status REJECTED."""
    create = client.post("/leave-requests", json={
        "employee_id": 1, "leave_type": "Vacation",
        "start_date": "2026-07-20", "end_date": "2026-07-22",
        "reason": "To reject",
    })
    request_id = create.json()["id"]
    client.post(f"/leave-requests/{request_id}/submit")
    response = client.post(f"/leave-requests/{request_id}/reject")
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"

# HAPPY TRANSITION — cancel a draft (200 / CANCELLED)
def test_cancel_draft_returns_200():
    """Cancelling a draft returns 200 and status CANCELLED."""
    create = client.post("/leave-requests", json={
        "employee_id": 1, "leave_type": "Vacation",
        "start_date": "2026-07-25", "end_date": "2026-07-27",
        "reason": "To cancel",
    })
    request_id = create.json()["id"]
    response = client.post(f"/leave-requests/{request_id}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"

# HAPPY TRANSITION — edit a draft (200, field saved)
def test_edit_draft_returns_200():
    """Editing a draft returns 200 and saves the changed field."""
    create = client.post("/leave-requests", json={
        "employee_id": 1, "leave_type": "Vacation",
        "start_date": "2026-07-28", "end_date": "2026-07-30",
        "reason": "Original reason",
    })
    request_id = create.json()["id"]
    response = client.patch(f"/leave-requests/{request_id}", json={"reason": "Updated reason"})
    assert response.status_code == 200
    assert response.json()["reason"] == "Updated reason"   # confirm the change actually saved

## GROUP-A
# LIST — returns everything created
def test_list_returns_created_requests():
    """GET /leave-requests returns 200 and lists everything created."""
    # fixture gives a fresh DB, so create exactly 2 and expect exactly 2 back
    for _ in range(2):
        client.post("/leave-requests", json={
            "employee_id": 1, "leave_type": "Vacation",
            "start_date": "2026-07-10", "end_date": "2026-07-12",
            "reason": "Trip",
        })
    response = client.get("/leave-requests")
    assert response.status_code == 200
    data = response.json()        # this is a LIST of request dicts, not one object
    assert len(data) == 2

# FILTER — by status
def test_filter_by_status():
    """Filtering by status returns only requests with that status."""
    # one stays DRAFT...
    client.post("/leave-requests", json={
        "employee_id": 1, "leave_type": "Vacation",
        "start_date": "2026-07-10", "end_date": "2026-07-12",
        "reason": "Draft one",
    })
    # ...the other gets submitted
    submitted = client.post("/leave-requests", json={
        "employee_id": 1, "leave_type": "Vacation",
        "start_date": "2026-07-20", "end_date": "2026-07-22",
        "reason": "Submitted one",
    })
    client.post(f"/leave-requests/{submitted.json()['id']}/submit")

    response = client.get("/leave-requests", params={"status": "DRAFT"})  # params -> ?status=DRAFT
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1                  # only the draft comes back
    for r in data:                         # and every returned item really is DRAFT
        assert r["status"] == "DRAFT"

# FILTER — by employee
def test_filter_by_employee():
    """Filtering by employee_id returns only that employee's requests."""
    for _ in range(2):
        client.post("/leave-requests", json={
            "employee_id": 1, "leave_type": "Vacation",
            "start_date": "2026-07-10", "end_date": "2026-07-12",
            "reason": "Trip",
        })
    # employee 1 made both
    res1 = client.get("/leave-requests", params={"employee_id": 1})
    assert len(res1.json()) == 2
    # employee 2 has none -> empty list (a filter miss is len 0, not a 404)
    res2 = client.get("/leave-requests", params={"employee_id": 2})
    assert len(res2.json()) == 0

## GROUP B
# EDGE CASE — edit with bad dates (422)
def test_edit_with_bad_dates_returns_422():
    """PATCHing a draft so the end date is before the start returns 422."""
    create = client.post("/leave-requests", json={
        "employee_id": 1, "leave_type": "Vacation",
        "start_date": "2026-07-10", "end_date": "2026-07-12",
        "reason": "Trip",
    })
    request_id = create.json()["id"]      # it's a DRAFT, so editing is allowed...
    # ...but flip the dates to an invalid range -> the edit endpoint's own check rejects it
    response = client.patch(f"/leave-requests/{request_id}", json={
        "start_date": "2026-07-12",
        "end_date": "2026-07-10",
    })
    assert response.status_code == 422

# EDGE CASE — action on a missing id (404)
def test_action_on_missing_id_returns_404():
    """Acting on a request id that doesn't exist returns 404."""
    response = client.post("/leave-requests/999/submit")   # no request #999 exists
    assert response.status_code == 404

# EDGE CASE — same-day request = 1 day
def test_same_day_is_one_day():
    """A request where start and end are the same date counts as 1 day."""
    response = client.post("/leave-requests", json={
        "employee_id": 1, "leave_type": "Vacation",
        "start_date": "2026-07-15", "end_date": "2026-07-15",  # same day
        "reason": "Single day off",
    })
    assert response.status_code == 201
    assert response.json()["number_of_days"] == 1   # inclusive count: one day = 1


# PAGINATION-TEST
# PAGINATION — limit caps the count
def test_limit_caps_results():
    """The limit param caps how many requests come back."""
    for _ in range(3):
        client.post("/leave-requests", json={
            "employee_id": 1, "leave_type": "Vacation",
            "start_date": "2026-07-10", "end_date": "2026-07-12",
            "reason": "Trip",
        })
    response = client.get("/leave-requests", params={"limit": 2})
    assert response.status_code == 200
    assert len(response.json()) == 2      # 3 exist, but limit caps it at 2

# PAGINATION — skip offsets from the start
def test_skip_offsets_results():
    """The skip param skips records from the start."""
    for _ in range(3):
        client.post("/leave-requests", json={
            "employee_id": 1, "leave_type": "Vacation",
            "start_date": "2026-07-10", "end_date": "2026-07-12",
            "reason": "Trip",
        })
    response = client.get("/leave-requests", params={"skip": 2})
    assert len(response.json()) == 1      # 3 total minus 2 skipped

# PAGINATION — skip + limit page together
def test_skip_and_limit_together():
    """skip and limit work together to page through results."""
    for _ in range(3):
        client.post("/leave-requests", json={
            "employee_id": 1, "leave_type": "Vacation",
            "start_date": "2026-07-10", "end_date": "2026-07-12",
            "reason": "Trip",
        })
    response = client.get("/leave-requests", params={"skip": 1, "limit": 1})
    assert len(response.json()) == 1      # skip the first, then take only 1

# TRANSITION GUARD — submit a non-draft (409)
def test_submit_non_draft_returns_409():
    """Submitting a request that's already SUBMITTED returns 409."""
    create = client.post("/leave-requests", json={
        "employee_id": 1, "leave_type": "Vacation",
        "start_date": "2026-07-10", "end_date": "2026-07-12",
        "reason": "Trip",   # reason present so the FIRST submit succeeds
    })
    request_id = create.json()["id"]
    client.post(f"/leave-requests/{request_id}/submit")             # DRAFT -> SUBMITTED (legal)
    response = client.post(f"/leave-requests/{request_id}/submit")  # submit again (illegal)
    assert response.status_code == 409


# TRANSITION GUARD — reject a non-submitted (409)
def test_reject_non_submitted_returns_409():
    """Rejecting a request that's still a DRAFT returns 409."""
    create = client.post("/leave-requests", json={
        "employee_id": 1, "leave_type": "Vacation",
        "start_date": "2026-07-10", "end_date": "2026-07-12",
        "reason": "Trip",
    })
    request_id = create.json()["id"]
    # don't submit — reject while still DRAFT (reject is only legal from SUBMITTED)
    response = client.post(f"/leave-requests/{request_id}/reject")
    assert response.status_code == 409


# EDGE CASE — PATCH a missing id (404)
def test_patch_missing_id_returns_404():
    """PATCHing a request id that doesn't exist returns 404."""
    response = client.patch("/leave-requests/999", json={"reason": "x"})
    assert response.status_code == 404


# HAPPY TRANSITION — cancel a submitted request (200 / CANCELLED)
def test_cancel_submitted_returns_200():
    """Cancelling a SUBMITTED request returns 200 and status CANCELLED."""
    create = client.post("/leave-requests", json={
        "employee_id": 1, "leave_type": "Vacation",
        "start_date": "2026-07-10", "end_date": "2026-07-12",
        "reason": "Trip",
    })
    request_id = create.json()["id"]
    client.post(f"/leave-requests/{request_id}/submit")             # DRAFT -> SUBMITTED
    response = client.post(f"/leave-requests/{request_id}/cancel")  # SUBMITTED -> CANCELLED
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


# CONTENT CHECK — /employees returns the seeded employee
def test_employees_returns_seeded_employee():
    """GET /employees returns the one employee the fixture seeds."""
    response = client.get("/employees")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1                       # the fixture seeds exactly one
    assert data[0]["name"] == "Test Employee"   # ...and it's this one