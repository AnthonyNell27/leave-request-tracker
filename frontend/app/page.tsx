export default function Home() {
  const requests = [
    { id: 1, status: "DRAFT" },
    { id: 2, status: "APPROVED" },
  ];

  return (
    <main>
      <h1>Leave Request Tracker</h1>
      {requests.map((r) => (
        <p key={r.id}>{r.id} — {r.status}</p>
      ))}
    </main>
  );
}