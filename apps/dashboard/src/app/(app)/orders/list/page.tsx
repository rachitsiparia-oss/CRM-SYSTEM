import { PermissionGate } from "@/components/permission-gate";
import { OrderDirectory } from "./order-directory";

export default function Page() {
  return (
    <PermissionGate permission="orders.view">
      <OrderDirectory />
    </PermissionGate>
  );
}
