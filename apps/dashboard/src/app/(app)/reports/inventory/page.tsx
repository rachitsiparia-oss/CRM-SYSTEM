import { DomainDashboardView } from "../domain-dashboard-view";

export default function Page() {
  return (
    <DomainDashboardView
      domain="inventory_suppliers"
      title="Inventory & supplier analytics"
      description="Stock health, wastage, and supplier performance."
    />
  );
}
