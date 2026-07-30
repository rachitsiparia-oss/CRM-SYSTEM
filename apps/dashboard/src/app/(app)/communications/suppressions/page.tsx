import { PermissionGate } from "@/components/permission-gate";
import { SuppressionsView } from "./suppressions-view";

export default function Page() {
  return (
    <PermissionGate permission="communications.suppressions.view">
      <SuppressionsView />
    </PermissionGate>
  );
}
