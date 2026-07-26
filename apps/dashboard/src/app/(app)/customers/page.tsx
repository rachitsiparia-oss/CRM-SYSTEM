import { PermissionGate } from "@/components/permission-gate";
import { CustomerDirectory } from "./customer-directory";

export default function Page() {
  return (
    <PermissionGate permission="customers.view">
      <CustomerDirectory />
    </PermissionGate>
  );
}
