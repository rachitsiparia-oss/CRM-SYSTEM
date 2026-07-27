import { PermissionGate } from "@/components/permission-gate";
import { ReceiptDetail } from "./receipt-detail";

export default async function Page({ params }: { params: Promise<{ receiptId: string }> }) {
  const { receiptId } = await params;
  return (
    <PermissionGate permission="inventory.view">
      <ReceiptDetail receiptId={receiptId} />
    </PermissionGate>
  );
}
