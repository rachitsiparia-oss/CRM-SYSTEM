import { PermissionGate } from "@/components/permission-gate";
import { TasksView } from "./tasks-view";

export default function Page() {
  return (
    <PermissionGate permission="tasks.view">
      <TasksView />
    </PermissionGate>
  );
}
