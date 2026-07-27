import { PermissionGate } from "@/components/permission-gate";
import { StockCountDetail } from "./stock-count-detail";

export default async function Page({ params }: { params: Promise<{ countId: string }> }) {
  const { countId } = await params;
  return (
    <PermissionGate permission="inventory.view">
      <StockCountDetail countId={countId} />
    </PermissionGate>
  );
}
