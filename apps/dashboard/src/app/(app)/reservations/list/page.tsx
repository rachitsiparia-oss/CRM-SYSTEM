import { PermissionGate } from "@/components/permission-gate";
import { ReservationDirectory } from "./reservation-directory";

export default function Page() {
  return (
    <PermissionGate permission="reservations.view">
      <ReservationDirectory />
    </PermissionGate>
  );
}
