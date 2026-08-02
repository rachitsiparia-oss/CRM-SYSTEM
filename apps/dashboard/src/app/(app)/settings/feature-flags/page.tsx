import { PermissionGate } from "@/components/permission-gate";
import { FeatureFlagsView } from "./feature-flags-view";

export default function Page() {
  return (
    <PermissionGate permission="settings.view">
      <FeatureFlagsView />
    </PermissionGate>
  );
}
