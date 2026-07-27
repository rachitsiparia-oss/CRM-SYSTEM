import { PermissionGate } from "@/components/permission-gate";
import { AdjustmentsAndWastage } from "./adjustments-and-wastage";

export default function Page() {
  return (
    <PermissionGate permission="inventory.view">
      <AdjustmentsAndWastage />
    </PermissionGate>
  );
}
