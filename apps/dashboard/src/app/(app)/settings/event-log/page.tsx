import { PermissionGate } from "@/components/permission-gate";
import { EventLogView } from "./event-log-view";

export default function Page() {
  return (
    <PermissionGate permission="event_log.view">
      <EventLogView />
    </PermissionGate>
  );
}
