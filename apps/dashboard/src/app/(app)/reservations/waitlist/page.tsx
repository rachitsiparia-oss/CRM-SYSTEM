import { PermissionGate } from "@/components/permission-gate";
import { WaitlistBoard } from "./waitlist-board";

export default function Page() {
  return (
    <PermissionGate permission="reservations.view">
      <WaitlistBoard />
    </PermissionGate>
  );
}
