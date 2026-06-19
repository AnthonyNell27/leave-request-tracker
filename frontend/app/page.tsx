"use client";

import { useState, useEffect } from "react";

type LeaveRequest = {
  id: number;
  employee_id: number;
  leave_type: string;
  start_date: string;
  end_date: string;
  reason: string | null;
  status: string;
  number_of_days: number;
};

export default function Home() {
  const [requests, setRequests] = useState<LeaveRequest[]>([]);

  const loadRequests = () => {
  fetch("http://localhost:8000/leave-requests")
    .then((res) => res.json())
    .then((data) => setRequests(data));
  };

  const doAction = async (id: number, action: string) => {
  const res = await fetch(`http://localhost:8000/leave-requests/${id}/${action}`, {
    method: "POST",
  });

  if (!res.ok) {
    const error = await res.json();
    alert(error.detail);
    return;
  }

  loadRequests();
  };

  useEffect(() => {
    loadRequests();
  }, []);


  const statusColors: Record<string, string> = {
  DRAFT: "bg-gray-200 text-gray-800",
  SUBMITTED: "bg-blue-200 text-blue-800",
  APPROVED: "bg-green-200 text-green-800",
  REJECTED: "bg-red-200 text-red-800",
  CANCELLED: "bg-yellow-200 text-yellow-800",
  };


  return (
    <main>
      <h1>Leave Request Tracker</h1>
      {requests.map((r) => (
       <div key={r.id}>
         <p>#{r.id} — Employee {r.employee_id}</p>
         <p>{r.leave_type}: {r.start_date} → {r.end_date} ({r.number_of_days} days)</p>
            <p>
            Status:{" "}
              <span className={`px-2 py-1 rounded text-sm ${statusColors[r.status]}`}>
              {r.status}
              </span>
            </p>
          <button onClick={() => doAction(r.id, "submit")}>Submit</button>
          <button onClick={() => doAction(r.id, "approve")}>Approve</button>
          <button onClick={() => doAction(r.id, "reject")}>Reject</button>
          <button onClick={() => doAction(r.id, "cancel")}>Cancel</button>
       </div>
      ))}
    </main>
  );
}