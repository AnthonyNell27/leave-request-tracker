# Leave Request Tracker — Stage 0 Plan

## Data Model Table 

| Column      | Type       | Required? | Notes                                                              |
|-------------|------------|-----------|--------------------------------------------------------------------|
| id          | int        | yes       | the request's own ID                                               |
| employee    | int        | yes       | the employee's ID — points to the Directory (foreign key)          |                          
| leave_type  | fixed set  | yes       | Vacation / Sick / Emergency                                        |
| start_date  | date       | yes       |                                                                    |
| end_date    | date       | yes       |                                                                    |
| reason      | text       | no        |required to submit, optional for draft                              |
| status      | fixed set  | yes       |DRAFT / SUBMITTED / APPROVED / REJECTED / CANCELLED — default: DRAFT|

Note: number_of_days is intentionally not stored — it's computed from start_date and end_date.


## Endpoints

| Method | Path                         | What it does               | Notes / guard                                |
|--------|------------------------------|----------------------------|----------------------------------------------|
| GET    | /leave-requests              | read                       |filters (by employee + status) and paginate   |
| POST   | /leave-requests              | create                     |create a new DRAFT                            |
| PATCH  | /leave-requests/{id}         | update                     |edit only while DRAFT                         |
| POST   | /leave-requests/{id}/submit  | moves request to SUBMITTED |only when DRAFT                               |
| POST   | /leave-requests/{id}/approve | moves request to APPROVED  |only when SUBMITTED                           |
| POST   | /leave-requests/{id}/reject  | moves request to REJECTED  |only when SUBMITTED                           |
| POST   | /leave-requests/{id}/cancel  | moves request to CANCELLED |only when DRAFT/SUBMITTED                     |

Note: No DELETE endpoint — requests are cancelled, not deleted.


## State Transitions

| Action | Allowed when status is | Resulting status | 
|--------|------------------------|------------------|
|submit  | DRAFT                  | SUBMITTED        |
|approve | SUBMITTED              | APPROVED         |
|reject  | SUBMITTED              | REJECTED         |
|cancel  | DRAFT or SUBMITTED     | CANCELLED        |

Note: APPROVED / REJECTED / CANCELLED are final, with no moves out of them.


## Validation & Business Rules 

1. End date must be on or after the start date
2. A new request can't start in the past
3. A reason is required to submit (not to save a draft)
4. An employee can't have two APPROVED leaves that overlap in dates.
   - a partial overlap → blocked
   - the exact same dates → blocked
   - back-to-back (one ends, next starts the next day) → allowed