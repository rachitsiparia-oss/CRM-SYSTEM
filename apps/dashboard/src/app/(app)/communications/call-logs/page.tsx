import { PermissionGate } from "@/components/permission-gate";
import { CallLogsView } from "./call-logs-view";

export default function Page() {
  return (
    <PermissionGate permission="communications.call_logs.view">
      <CallLogsView />
    </PermissionGate>
  );
}
