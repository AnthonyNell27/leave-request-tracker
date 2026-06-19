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

  useEffect(() => {
    fetch("http://localhost:8000/leave-requests")
      .then((res) => res.json())
      .then((data) => setRequests(data));
  }, []);

  return (
    <main>
      <h1>Leave Request Tracker</h1>
      {requests.map((r) => (
       <div key={r.id}>
         <p>#{r.id} — Employee {r.employee_id}</p>
         <p>{r.leave_type}: {r.start_date} → {r.end_date} ({r.number_of_days} days)</p>
         <p>Status: {r.status}</p>
       </div>
      ))}
    </main>
  );
}