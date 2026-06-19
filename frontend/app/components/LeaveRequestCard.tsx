import { LeaveRequest } from "./types";

type Props = {
  request: LeaveRequest;
  onAction: (id: number, action: string) => void;
};

const statusColors: Record<string, string> = {
  DRAFT: "bg-gray-200 text-gray-800",
  SUBMITTED: "bg-blue-200 text-blue-800",
  APPROVED: "bg-green-200 text-green-800",
  REJECTED: "bg-red-200 text-red-800",
  CANCELLED: "bg-yellow-200 text-yellow-800",
};

export default function LeaveRequestCard({ request, onAction }: Props) {
  return (
    <div>
      <p>#{request.id} — Employee {request.employee_id}</p>
      <p>{request.leave_type}: {request.start_date} → {request.end_date} ({request.number_of_days} days)</p>
      <p>
        Status:{" "}
        <span className={`px-2 py-1 rounded text-sm ${statusColors[request.status]}`}>
          {request.status}
        </span>
      </p>
      <button onClick={() => onAction(request.id, "submit")}>Submit</button>
      <button onClick={() => onAction(request.id, "approve")}>Approve</button>
      <button onClick={() => onAction(request.id, "reject")}>Reject</button>
      <button onClick={() => onAction(request.id, "cancel")}>Cancel</button>
    </div>
  );
}