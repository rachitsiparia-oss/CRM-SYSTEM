import { PermissionGate } from "@/components/permission-gate";
import { CustomerDetail } from "./customer-detail";

export default async function Page({ params }: { params: Promise<{ customerId: string }> }) {
  const { customerId } = await params;
  return (
    <PermissionGate permission="customers.view">
      <CustomerDetail customerId={customerId} />
    </PermissionGate>
  );
}
