import { PermissionGate } from "@/components/permission-gate";
import { CacheView } from "./cache-view";

export default function Page() {
  return (
    <PermissionGate permission="cache.view">
      <CacheView />
    </PermissionGate>
  );
}
