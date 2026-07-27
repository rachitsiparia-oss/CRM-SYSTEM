import { PermissionGate } from "@/components/permission-gate";
import { BusinessHoursEditor } from "./business-hours-editor";

export default function Page() {
  return (
    <PermissionGate permission="reservations.view">
      <BusinessHoursEditor />
    </PermissionGate>
  );
}
