import { PermissionGate } from "@/components/permission-gate";
import { CreateOrderForm } from "./create-order-form";

export default function Page() {
  return (
    <PermissionGate permission="orders.create">
      <CreateOrderForm />
    </PermissionGate>
  );
}
