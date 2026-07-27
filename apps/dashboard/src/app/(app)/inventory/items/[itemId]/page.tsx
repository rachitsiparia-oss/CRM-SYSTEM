import { PermissionGate } from "@/components/permission-gate";
import { InventoryItemDetail } from "./item-detail";

export default async function Page({ params }: { params: Promise<{ itemId: string }> }) {
  const { itemId } = await params;
  return (
    <PermissionGate permission="inventory.view">
      <InventoryItemDetail itemId={itemId} />
    </PermissionGate>
  );
}
