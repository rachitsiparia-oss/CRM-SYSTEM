"use client";

import { useStaffAnalytics } from "@/lib/hooks/use-staff-operations";
import { useDepartments } from "@/lib/hooks/use-staff";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { ErrorState } from "@/components/error-state";
import { Skeleton } from "@/components/ui/skeleton";

export function StaffAnalyticsView() {
  const { data: stats, isLoading, isError, refetch } = useStaffAnalytics();
  const { data: departments } = useDepartments();

  const departmentName = (id: string | null) =>
    departments?.find((d) => d.id === id)?.name ?? "Unassigned";

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Staff analytics"
        description="Headcount distribution and completion rates for training and knowledge acknowledgement."
      />

      {isError ? (
        <ErrorState title="Could not load staff analytics" onRetry={() => void refetch()} />
      ) : isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <SectionCard title="Active staff by department">
            <ul className="flex flex-col gap-1 text-sm">
              {stats?.staff_by_department.map((row) => (
                <li
                  key={row.department_id ?? "unassigned"}
                  className="flex items-center justify-between gap-2"
                >
                  <span>{departmentName(row.department_id)}</span>
                  <span className="text-muted-foreground">{row.count}</span>
                </li>
              ))}
            </ul>
          </SectionCard>
          <SectionCard title="Completion rates">
            <div className="flex flex-col gap-3 text-sm">
              <div className="flex items-center justify-between">
                <span>Mandatory training completion</span>
                <span className="font-semibold">
                  {stats?.mandatory_training_completion_pct ?? 0}%
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Knowledge acknowledgement completion</span>
                <span className="font-semibold">
                  {stats?.knowledge_acknowledgement_completion_pct ?? 0}%
                </span>
              </div>
            </div>
          </SectionCard>
        </div>
      )}
    </div>
  );
}
