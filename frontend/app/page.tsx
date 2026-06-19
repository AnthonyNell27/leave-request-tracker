"use client";

import { useState, useEffect } from "react";

import LeaveRequestCard from "./components/LeaveRequestCard";
import { LeaveRequest } from "./components/types";

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


  return (
    <main>
      <h1>Leave Request Tracker</h1>
      {requests.map((r) => (
      <LeaveRequestCard key={r.id} request={r} onAction={doAction} />
      ))}
    </main>
  );
}