import { DomainDashboardView } from "../domain-dashboard-view";

export default function Page() {
  return (
    <DomainDashboardView
      domain="reservations"
      title="Reservation analytics"
      description="Covers, no-shows, and table utilization."
    />
  );
}
