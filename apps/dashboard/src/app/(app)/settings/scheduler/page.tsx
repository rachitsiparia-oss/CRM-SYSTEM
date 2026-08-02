import { PermissionGate } from "@/components/permission-gate";
import { SchedulerView } from "./scheduler-view";

export default function Page() {
  return (
    <PermissionGate permission="scheduler.view">
      <SchedulerView />
    </PermissionGate>
  );
}
