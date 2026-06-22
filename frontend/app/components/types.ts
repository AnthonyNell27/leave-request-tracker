// A "type" describes the shape of an object — what fields it has and what kind of value each holds.
// TypeScript uses these to catch mistakes (e.g. a typo'd field name) before you even run the code.

// One leave request, matching what the backend sends back.
export type LeaveRequest = {
  id: number;
  employee_id: number;
  leave_type: string;
  start_date: string;      // dates arrive as text like "2026-06-25"
  end_date: string;
  reason: string | null;   // "string | null" = either some text OR empty (null). that's why we guard it before showing.
  status: string;          // e.g. "DRAFT", "APPROVED" ...
  number_of_days: number;
};

// One employee — used to fill the dropdown.
export type Employee = { id: number; name: string };