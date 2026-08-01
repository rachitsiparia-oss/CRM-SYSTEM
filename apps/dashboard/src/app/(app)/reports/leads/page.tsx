import { DomainDashboardView } from "../domain-dashboard-view";

export default function Page() {
  return (
    <DomainDashboardView
      domain="leads"
      title="Lead analytics"
      description="Pipeline volume, source performance, and conversion."
    />
  );
}
