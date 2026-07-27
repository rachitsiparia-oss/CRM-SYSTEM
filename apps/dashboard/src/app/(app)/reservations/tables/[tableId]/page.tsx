import { PermissionGate } from "@/components/permission-gate";
import { TableDetail } from "./table-detail";

export default async function Page({ params }: { params: Promise<{ tableId: string }> }) {
  const { tableId } = await params;
  return (
    <PermissionGate permission="reservations.view">
      <TableDetail tableId={tableId} />
    </PermissionGate>
  );
}
