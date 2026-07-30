import { PermissionGate } from "@/components/permission-gate";
import { TemplatesView } from "./templates-view";

export default function Page() {
  return (
    <PermissionGate permission="communications.templates.view">
      <TemplatesView />
    </PermissionGate>
  );
}
