import { PermissionGate } from "@/components/permission-gate";
import { PreferencesView } from "./preferences-view";

export default function Page() {
  return (
    <PermissionGate permission="communications.preferences.view">
      <PreferencesView />
    </PermissionGate>
  );
}
