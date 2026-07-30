import { PermissionGate } from "@/components/permission-gate";
import { InboxView } from "./inbox-view";

export default function Page() {
  return (
    <PermissionGate permission="communications.view">
      <InboxView />
    </PermissionGate>
  );
}
