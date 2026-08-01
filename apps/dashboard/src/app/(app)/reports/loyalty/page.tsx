import { DomainDashboardView } from "../domain-dashboard-view";

export default function Page() {
  return (
    <DomainDashboardView
      domain="loyalty"
      title="Loyalty analytics"
      description="Membership, tier distribution, and redemption."
    />
  );
}
