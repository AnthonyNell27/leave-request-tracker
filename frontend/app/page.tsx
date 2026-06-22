"use client"; // tells Next.js this component runs in the browser (needed for useState/useEffect)

import { useState, useEffect } from "react";

import LeaveRequestCard from "./components/LeaveRequestCard";
import { LeaveRequest, Employee } from "./components/types";

export default function Home() {
  // --- STATE: little "boxes" that hold data. When a box changes, the screen re-draws. ---
  const [requests, setRequests] = useState<LeaveRequest[]>([]); // the list of leave requests from the backend
  const [employees, setEmployees] = useState<Employee[]>([]);   // the list of employees (fills the dropdown)

  // one box per form field. They start empty ("") because the form starts blank.
  const [employeeId, setEmployeeId] = useState("");
  const [reason, setReason] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [leaveType, setLeaveType] = useState("");

  // null = we're creating a new request. a number = we're editing the request with that id.
  const [editingId, setEditingId] = useState<number | null>(null);

  // --- DATA LOADING: fetch = go ask the backend for data, then put it in a state box. ---
  const loadEmployees = () => {
    fetch("http://localhost:8000/employees")
      .then((res) => res.json())        // turn the response into usable data
      .then((data) => setEmployees(data)); // put that data in the employees box
  };

  const loadRequests = () => {
    fetch("http://localhost:8000/leave-requests")
      .then((res) => res.json())
      .then((data) => setRequests(data));
  };

  // runs the status buttons on each card (submit/approve/reject/cancel)
  const doAction = async (id: number, action: string) => {
    const res = await fetch(
      `http://localhost:8000/leave-requests/${id}/${action}`,
      {
        method: "POST",
      }
    );

    // if the backend says "no" (e.g. invalid action), show its message and stop
    if (!res.ok) {
      const error = await res.json();
      alert(error.detail);
      return;
    }

    loadRequests(); // refresh the list so the new status shows
  };

  // empties all the form boxes and leaves edit mode (back to "create" mode)
  const resetForm = () => {
    setEmployeeId("");
    setReason("");
    setStartDate("");
    setEndDate("");
    setLeaveType("");
    setEditingId(null);
  };

  // when "Edit" is clicked: copy that request's values into the form boxes, then enter edit mode
  const startEdit = (request: LeaveRequest) => {
    setEditingId(request.id);
    setEmployeeId(String(request.employee_id)); // dropdown values are strings, so convert the number to "1"
    setReason(request.reason ?? "");            // reason can be null; ?? "" gives "" instead of null
    setStartDate(request.start_date);
    setEndDate(request.end_date);
    setLeaveType(request.leave_type);
    window.scrollTo({ top: 0, behavior: "smooth" }); // scroll up so the user sees the filled form
  };

  // runs when the form is submitted (create OR save-edit)
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); // stop the browser's default "reload the page" behaviour

    // gather the form boxes into one object shaped the way the backend wants (snake_case names)
    const payload = {
      leave_type: leaveType,
      start_date: startDate,
      end_date: endDate,
      reason: reason,
      // only include employee_id when creating; the backend ignores it on edit
      ...(editingId === null && { employee_id: Number(employeeId) }),
    };

    // creating -> POST to the list URL. editing -> PATCH to that one request's URL.
    const url =
      editingId === null
        ? "http://localhost:8000/leave-requests"
        : `http://localhost:8000/leave-requests/${editingId}`;
    const method = editingId === null ? "POST" : "PATCH";

    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" }, // "I'm sending JSON" label
      body: JSON.stringify(payload),                   // turn the object into text to send
    });

    if (!res.ok) {
      const error = await res.json();
      alert(error.detail);
      return;
    }

    loadRequests(); // refresh the list so the change shows
    resetForm();    // clear the form for the next entry
  };

  // useEffect with [] = "run this once when the page first loads"
  useEffect(() => {
    loadRequests();
    loadEmployees();
  }, []);

  // shared styling string so every input/select looks the same (write once, reuse)
  const fieldClass =
    "rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-3 py-2 text-sm outline-none focus:border-blue-500";

  // handy true/false flag: are we currently editing? used to switch text + lock the dropdown
  const isEditing = editingId !== null;

  return (
    <main className="mx-auto max-w-2xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold">Leave Request Tracker</h1>

      {/* onSubmit runs handleSubmit when the form is sent */}
      <form
        onSubmit={handleSubmit}
        className="mb-8 rounded-lg border border-neutral-200 bg-neutral-50 p-6 dark:border-neutral-800 dark:bg-neutral-900"
      >
        {/* heading + button text change depending on create vs edit mode */}
        <h2 className="mb-4 text-lg font-semibold">
          {isEditing ? `Edit request #${editingId}` : "New request"}
        </h2>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-1 sm:col-span-2">
            <span className="text-sm font-medium">Employee</span>
            {/* controlled dropdown: value reads state, onChange writes it. disabled while editing. */}
            <select
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value)}
              disabled={isEditing}
              className={`${fieldClass} disabled:cursor-not-allowed disabled:opacity-60`}
            >
              <option value="">Select an employee…</option>
              {/* build one <option> per employee from the backend list */}
              {employees.map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.name}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1 sm:col-span-2">
            <span className="text-sm font-medium">Reason</span>
            {/* controlled text input */}
            <input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Family trip"
              className={fieldClass}
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium">Start date</span>
            {/* type="date" gives a calendar picker; the value is a "YYYY-MM-DD" string */}
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className={fieldClass}
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium">End date</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className={fieldClass}
            />
          </label>

          <label className="flex flex-col gap-1 sm:col-span-2">
            <span className="text-sm font-medium">Type</span>
            {/* fixed options (not from the backend), so they're written by hand. */}
            {/* value must match the backend's allowed words exactly. */}
            <select
              value={leaveType}
              onChange={(e) => setLeaveType(e.target.value)}
              className={fieldClass}
            >
              <option value="">Select a type…</option>
              <option value="Vacation">Vacation</option>
              <option value="Sick">Sick</option>
              <option value="Emergency">Emergency</option>
            </select>
          </label>
        </div>

        <div className="mt-5 flex gap-2">
          {/* button text depends on mode */}
          <button
            type="submit"
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            {isEditing ? "Save changes" : "Create request"}
          </button>

          {/* Cancel only shows while editing. type="button" so it doesn't submit the form. */}
          {isEditing && (
            <button
              type="button"
              onClick={resetForm}
              className="rounded-md border border-neutral-300 px-4 py-2 text-sm font-medium hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800"
            >
              Cancel
            </button>
          )}
        </div>
      </form>

      {/* loop over the requests and show a card for each one */}
      <div className="space-y-3">
        {requests.map((r) => (
          <LeaveRequestCard
            key={r.id}            // unique key so React can track each card
            request={r}
            onAction={doAction}   // pass the status-button handler down
            onEdit={startEdit}    // pass the edit handler down
          />
        ))}
      </div>
    </main>
  );
}