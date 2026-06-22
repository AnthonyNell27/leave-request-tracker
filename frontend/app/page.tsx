"use client";

import { useState, useEffect } from "react";

import LeaveRequestCard from "./components/LeaveRequestCard";
import { LeaveRequest, Employee } from "./components/types";

export default function Home() {
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [employeeId, setEmployeeId] = useState("");
  const [reason, setReason] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [leaveType, setLeaveType] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);

  const loadEmployees = () => {
    fetch("http://localhost:8000/employees")
      .then((res) => res.json())
      .then((data) => setEmployees(data));
  };

  const loadRequests = () => {
    fetch("http://localhost:8000/leave-requests")
      .then((res) => res.json())
      .then((data) => setRequests(data));
  };

  const doAction = async (id: number, action: string) => {
    const res = await fetch(
      `http://localhost:8000/leave-requests/${id}/${action}`,
      {
        method: "POST",
      }
    );

    if (!res.ok) {
      const error = await res.json();
      alert(error.detail);
      return;
    }

    loadRequests();
  };

  // Blanks every field and leaves edit mode.
  const resetForm = () => {
    setEmployeeId("");
    setReason("");
    setStartDate("");
    setEndDate("");
    setLeaveType("");
    setEditingId(null);
  };

  // Fills the form with an existing request's values and enters edit mode.
  const startEdit = (request: LeaveRequest) => {
    setEditingId(request.id);
    setEmployeeId(String(request.employee_id));
    setReason(request.reason ?? "");
    setStartDate(request.start_date);
    setEndDate(request.end_date);
    setLeaveType(request.leave_type);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const payload = {
      leave_type: leaveType,
      start_date: startDate,
      end_date: endDate,
      reason: reason,
      // employee_id only applies on create; the backend's update contract ignores it
      ...(editingId === null && { employee_id: Number(employeeId) }),
    };

    // Create when not editing; update when we have an editingId.
    const url =
      editingId === null
        ? "http://localhost:8000/leave-requests"
        : `http://localhost:8000/leave-requests/${editingId}`;
    const method = editingId === null ? "POST" : "PATCH";

    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const error = await res.json();
      alert(error.detail);
      return;
    }

    loadRequests();
    resetForm();
  };

  useEffect(() => {
    loadRequests();
    loadEmployees();
  }, []);

  const fieldClass =
    "rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-3 py-2 text-sm outline-none focus:border-blue-500";

  const isEditing = editingId !== null;

  return (
    <main className="mx-auto max-w-2xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold">Leave Request Tracker</h1>

      <form
        onSubmit={handleSubmit}
        className="mb-8 rounded-lg border border-neutral-200 bg-neutral-50 p-6 dark:border-neutral-800 dark:bg-neutral-900"
      >
        <h2 className="mb-4 text-lg font-semibold">
          {isEditing ? `Edit request #${editingId}` : "New request"}
        </h2>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-1 sm:col-span-2">
            <span className="text-sm font-medium">Employee</span>
            <select
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value)}
              disabled={isEditing}
              className={`${fieldClass} disabled:cursor-not-allowed disabled:opacity-60`}
            >
              <option value="">Select an employee…</option>
              {employees.map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.name}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1 sm:col-span-2">
            <span className="text-sm font-medium">Reason</span>
            <input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Family trip"
              className={fieldClass}
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium">Start date</span>
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
          <button
            type="submit"
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            {isEditing ? "Save changes" : "Create request"}
          </button>

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

      <div className="space-y-3">
        {requests.map((r) => (
          <LeaveRequestCard
            key={r.id}
            request={r}
            onAction={doAction}
            onEdit={startEdit}
          />
        ))}
      </div>
    </main>
  );
}