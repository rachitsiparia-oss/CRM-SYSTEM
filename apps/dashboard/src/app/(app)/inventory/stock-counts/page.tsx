import { PermissionGate } from "@/components/permission-gate";
import { StockCountDirectory } from "./stock-count-directory";

export default function Page() {
  return (
    <PermissionGate permission="inventory.view">
      <StockCountDirectory />
    </PermissionGate>
  );
}
