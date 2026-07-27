import { PermissionGate } from "@/components/permission-gate";
import { TransferDetail } from "./transfer-detail";

export default async function Page({ params }: { params: Promise<{ transferId: string }> }) {
  const { transferId } = await params;
  return (
    <PermissionGate permission="inventory.view">
      <TransferDetail transferId={transferId} />
    </PermissionGate>
  );
}
