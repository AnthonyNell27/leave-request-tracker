import { LeaveRequest } from "./types";

type Props = {
  request: LeaveRequest;
  onAction: (id: number, action: string) => void;
  onEdit: (request: LeaveRequest) => void;
};

const statusColors: Record<string, string> = {
  DRAFT: "bg-gray-200 text-gray-800",
  SUBMITTED: "bg-blue-200 text-blue-800",
  APPROVED: "bg-green-200 text-green-800",
  REJECTED: "bg-red-200 text-red-800",
  CANCELLED: "bg-yellow-200 text-yellow-800",
};

export default function LeaveRequestCard({ request, onAction, onEdit }: Props) {
  const buttonClass =
    "rounded border border-neutral-300 px-3 py-1 text-sm hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800";

  return (
    <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-4 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="flex items-center justify-between">
        <p className="font-semibold">
          #{request.id} · Employee {request.employee_id}
        </p>
        <span
          className={`rounded px-2 py-1 text-xs font-medium ${statusColors[request.status]}`}
        >
          {request.status}
        </span>
      </div>

      <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
        {request.leave_type}: {request.start_date} → {request.end_date} (
        {request.number_of_days} days)
      </p>

      {request.reason && (
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-500">
          Reason: {request.reason}
        </p>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        {request.status === "DRAFT" && (
          <button onClick={() => onEdit(request)} className={buttonClass}>
            Edit
          </button>
        )}
        <button onClick={() => onAction(request.id, "submit")} className={buttonClass}>
          Submit
        </button>
        <button onClick={() => onAction(request.id, "approve")} className={buttonClass}>
          Approve
        </button>
        <button onClick={() => onAction(request.id, "reject")} className={buttonClass}>
          Reject
        </button>
        <button onClick={() => onAction(request.id, "cancel")} className={buttonClass}>
          Cancel
        </button>
      </div>
    </div>
  );
}