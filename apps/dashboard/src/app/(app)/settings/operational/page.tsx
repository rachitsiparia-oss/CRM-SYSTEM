import { PermissionGate } from "@/components/permission-gate";
import { OperationalSettingsView } from "./operational-settings-view";

export default function Page() {
  return (
    <PermissionGate permission="settings.view">
      <OperationalSettingsView />
    </PermissionGate>
  );
}
