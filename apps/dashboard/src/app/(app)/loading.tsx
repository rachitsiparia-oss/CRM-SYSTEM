export default function Loading() {
  return (
    <div
      role="status"
      aria-label="Loading"
      className="flex flex-1 flex-col gap-3 p-8"
    >
      <div className="h-6 w-48 animate-pulse rounded bg-muted" />
      <div className="h-4 w-full max-w-md animate-pulse rounded bg-muted" />
    </div>
  );
}
