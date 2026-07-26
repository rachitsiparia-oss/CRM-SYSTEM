import { PermissionGate } from "@/components/permission-gate";
import { ModifierGroupDirectory } from "./modifier-group-directory";

export default function Page() {
  return (
    <PermissionGate permission="menu.view">
      <ModifierGroupDirectory />
    </PermissionGate>
  );
}
