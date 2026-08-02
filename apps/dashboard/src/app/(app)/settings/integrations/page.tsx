import { PermissionGate } from "@/components/permission-gate";
import { IntegrationsView } from "./integrations-view";

export default function Page() {
  return (
    <PermissionGate permission="settings.integrations.view">
      <IntegrationsView />
    </PermissionGate>
  );
}
