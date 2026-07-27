import { PermissionGate } from "@/components/permission-gate";
import { TableFloorOverview } from "./table-floor-overview";

export default function Page() {
  return (
    <PermissionGate permission="reservations.view">
      <TableFloorOverview />
    </PermissionGate>
  );
}
