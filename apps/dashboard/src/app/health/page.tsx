// Non-sensitive frontend health surface. Never expose secrets, database
// URLs, or provider credentials here — see CLAUDE.md section 19.
export default function HealthPage() {
  return (
    <div className="flex flex-1 flex-col gap-2 p-8">
      <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
        Dashboard: OK
      </h1>
      <p className="text-sm text-zinc-500 dark:text-zinc-400">
        This page confirms the dashboard process is serving requests. It does
        not reflect API, database, or worker health.
      </p>
    </div>
  );
}
