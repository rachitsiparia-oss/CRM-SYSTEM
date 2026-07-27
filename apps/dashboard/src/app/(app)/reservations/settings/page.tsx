import { PermissionGate } from "@/components/permission-gate";
import { ReservationSettingsEditor } from "./reservation-settings-editor";

export default function Page() {
  return (
    <PermissionGate permission="reservations.view">
      <ReservationSettingsEditor />
    </PermissionGate>
  );
}
