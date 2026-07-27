import { PermissionGate } from "@/components/permission-gate";
import { SupplierDirectory } from "./supplier-directory";

export default function Page() {
  return (
    <PermissionGate permission="inventory.view">
      <SupplierDirectory />
    </PermissionGate>
  );
}
