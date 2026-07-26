import { PermissionGate } from "@/components/permission-gate";
import { OrderDetail } from "./order-detail";

export default async function Page({ params }: { params: Promise<{ orderId: string }> }) {
  const { orderId } = await params;
  return (
    <PermissionGate permission="orders.view">
      <OrderDetail orderId={orderId} />
    </PermissionGate>
  );
}
