import { PermissionGate } from "@/components/permission-gate";
import { LeadPipeline } from "./lead-pipeline";

export default function Page() {
  return (
    <PermissionGate permission="leads.view">
      <LeadPipeline />
    </PermissionGate>
  );
}
