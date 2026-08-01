import { DomainDashboardView } from "../domain-dashboard-view";

export default function Page() {
  return (
    <DomainDashboardView
      domain="customers"
      title="Customer analytics"
      description="Growth, retention, and lifetime value."
    />
  );
}
