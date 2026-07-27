import { PermissionGate } from "@/components/permission-gate";
import { ReceiptDirectory } from "./receipt-directory";

export default function Page() {
  return (
    <PermissionGate permission="inventory.view">
      <ReceiptDirectory />
    </PermissionGate>
  );
}
