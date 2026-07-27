import { PermissionGate } from "@/components/permission-gate";
import { InventoryDashboard } from "./inventory-dashboard";

export default function Page() {
  return (
    <PermissionGate permission="inventory.view">
      <InventoryDashboard />
    </PermissionGate>
  );
}
