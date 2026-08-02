import { PermissionGate } from "@/components/permission-gate";
import { DeadLetterView } from "./dead-letter-view";

export default function Page() {
  return (
    <PermissionGate permission="dead_letter.view">
      <DeadLetterView />
    </PermissionGate>
  );
}
