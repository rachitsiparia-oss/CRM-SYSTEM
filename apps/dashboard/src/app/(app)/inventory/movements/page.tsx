import { PermissionGate } from "@/components/permission-gate";
import { MovementLedger } from "./movement-ledger";

export default function Page() {
  return (
    <PermissionGate permission="inventory.view">
      <MovementLedger />
    </PermissionGate>
  );
}
