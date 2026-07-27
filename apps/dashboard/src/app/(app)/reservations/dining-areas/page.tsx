import { PermissionGate } from "@/components/permission-gate";
import { DiningAreaDirectory } from "./dining-area-directory";

export default function Page() {
  return (
    <PermissionGate permission="reservations.view">
      <DiningAreaDirectory />
    </PermissionGate>
  );
}
