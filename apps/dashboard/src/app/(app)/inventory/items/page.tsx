import { PermissionGate } from "@/components/permission-gate";
import { InventoryItemDirectory } from "./inventory-item-directory";

export default function Page() {
  return (
    <PermissionGate permission="inventory.view">
      <InventoryItemDirectory />
    </PermissionGate>
  );
}
