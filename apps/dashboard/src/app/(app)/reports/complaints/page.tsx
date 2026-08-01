import { DomainDashboardView } from "../domain-dashboard-view";

export default function Page() {
  return (
    <DomainDashboardView
      domain="complaints"
      title="Complaint analytics"
      description="Case volume, SLA compliance, and severity mix."
    />
  );
}
