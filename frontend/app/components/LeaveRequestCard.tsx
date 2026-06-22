import { LeaveRequest } from "./types";

// Props = the data this card receives from its parent (page.tsx).
// request = the leave request to show. onAction/onEdit = functions the parent passes in
// so the buttons here can tell the parent what the user clicked.
type Props = {
  request: LeaveRequest;
  onAction: (id: number, action: string) => void;
  onEdit: (request: LeaveRequest) => void;
};

// A lookup table: given a status string, get the matching Tailwind colour classes.
// statusColors["APPROVED"] returns the green classes, etc.
const statusColors: Record<string, string> = {
  DRAFT: "bg-gray-200 text-gray-800",
  SUBMITTED: "bg-blue-200 text-blue-800",
  APPROVED: "bg-green-200 text-green-800",
  REJECTED: "bg-red-200 text-red-800",
  CANCELLED: "bg-yellow-200 text-yellow-800",
};

export default function LeaveRequestCard({ request, onAction, onEdit }: Props) {
  // styling for the small action buttons, written once and reused below
  const buttonClass =
    "rounded border border-neutral-300 px-3 py-1 text-sm hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800";

  return (
    <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-4 dark:border-neutral-800 dark:bg-neutral-900">
      {/* top row: id + employee on the left, status badge on the right */}
      <div className="flex items-center justify-between">
        <p className="font-semibold">
          #{request.id} · Employee {request.employee_id}
        </p>
        {/* the badge colour is picked from the lookup table above, based on this request's status */}
        <span
          className={`rounded px-2 py-1 text-xs font-medium ${statusColors[request.status]}`}
        >
          {request.status}
        </span>
      </div>

      {/* main details line */}
      <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
        {request.leave_type}: {request.start_date} → {request.end_date} (
        {request.number_of_days} days)
      </p>

      {/* reason can be null, so only show this line when there actually is one */}
      {request.reason && (
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-500">
          Reason: {request.reason}
        </p>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        {/* Edit only makes sense on drafts, so it only shows when status is DRAFT */}
        {request.status === "DRAFT" && (
          <button onClick={() => onEdit(request)} className={buttonClass}>
            Edit
          </button>
        )}
        {/* each button calls onAction with this request's id and the action name. */}
        {/* the parent (page.tsx) sends that to the backend and refreshes the list. */}
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