import { PermissionGate } from "@/components/permission-gate";
import { ReservationCalendar } from "./reservation-calendar";

export default function Page() {
  return (
    <PermissionGate permission="reservations.view">
      <ReservationCalendar />
    </PermissionGate>
  );
}
