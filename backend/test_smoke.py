from fastapi.testclient import TestClient
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

# Seed one employee so create tests have a valid employee_id (the test DB starts empty)
seed_db = TestingSessionLocal()
seed_db.add(models.Employee(name="Test Employee"))
seed_db.commit()
seed_db.close()

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


def test_list_employees():
    """The /employees endpoint responds with 200 OK."""
    response = client.get("/employees")   # hit the employees endpoint your frontend uses
    assert response.status_code == 200    # 200 means "OK / success"


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