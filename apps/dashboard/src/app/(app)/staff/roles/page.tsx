import { PermissionGate } from "@/components/permission-gate";
import { RolesViewer } from "./roles-viewer";

export default function Page() {
  return (
    <PermissionGate permission="roles.view">
      <RolesViewer />
    </PermissionGate>
  );
}
