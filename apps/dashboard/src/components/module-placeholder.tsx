export function ModulePlaceholder({ title }: { title: string }) {
  return (
    <div className="flex flex-1 flex-col items-start gap-2 p-8">
      <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">{title}</h1>
      <p className="text-sm text-zinc-500 dark:text-zinc-400">
        This module is not implemented yet. It will be built in its scheduled
        phase per ROADMAP.md.
      </p>
    </div>
  );
}
