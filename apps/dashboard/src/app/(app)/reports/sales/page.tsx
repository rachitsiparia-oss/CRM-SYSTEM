import { DomainDashboardView } from "../domain-dashboard-view";

export default function Page() {
  return (
    <DomainDashboardView
      domain="sales"
      title="Sales analytics"
      description="Revenue, order volume, average ticket size, and cancellations."
    />
  );
}
