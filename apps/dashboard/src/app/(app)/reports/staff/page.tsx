import { DomainDashboardView } from "../domain-dashboard-view";

export default function Page() {
  return (
    <DomainDashboardView
      domain="staff_tasks"
      title="Staff & task analytics"
      description="Task completion, overdue work, and staffing metrics."
    />
  );
}
