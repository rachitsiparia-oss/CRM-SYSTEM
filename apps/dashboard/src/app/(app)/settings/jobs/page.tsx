import { PermissionGate } from "@/components/permission-gate";
import { JobsView } from "./jobs-view";

export default function Page() {
  return (
    <PermissionGate permission="jobs.view">
      <JobsView />
    </PermissionGate>
  );
}
