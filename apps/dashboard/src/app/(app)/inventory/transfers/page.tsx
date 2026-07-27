import { PermissionGate } from "@/components/permission-gate";
import { TransferDirectory } from "./transfer-directory";

export default function Page() {
  return (
    <PermissionGate permission="inventory.view">
      <TransferDirectory />
    </PermissionGate>
  );
}
