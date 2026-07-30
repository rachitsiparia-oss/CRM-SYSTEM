import { PermissionGate } from "@/components/permission-gate";
import { AnalyticsView } from "./analytics-view";

export default function Page() {
  return (
    <PermissionGate permission="communications.analytics.view">
      <AnalyticsView />
    </PermissionGate>
  );
}
