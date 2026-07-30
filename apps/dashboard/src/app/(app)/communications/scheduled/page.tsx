import { PermissionGate } from "@/components/permission-gate";
import { ScheduledView } from "./scheduled-view";

export default function Page() {
  return (
    <PermissionGate permission="communications.view">
      <ScheduledView />
    </PermissionGate>
  );
}
