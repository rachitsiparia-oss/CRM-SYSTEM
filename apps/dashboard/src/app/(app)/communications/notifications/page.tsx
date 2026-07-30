import { PermissionGate } from "@/components/permission-gate";
import { NotificationsView } from "./notifications-view";

export default function Page() {
  return (
    <PermissionGate permission="communications.view">
      <NotificationsView />
    </PermissionGate>
  );
}
