import { PermissionGate } from "@/components/permission-gate";
import { ChannelsView } from "./channels-view";

export default function Page() {
  return (
    <PermissionGate permission="communications.channels.view">
      <ChannelsView />
    </PermissionGate>
  );
}
