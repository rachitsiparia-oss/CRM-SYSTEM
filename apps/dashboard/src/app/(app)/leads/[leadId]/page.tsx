import { PermissionGate } from "@/components/permission-gate";
import { LeadDetail } from "./lead-detail";

export default async function Page({ params }: { params: Promise<{ leadId: string }> }) {
  const { leadId } = await params;
  return (
    <PermissionGate permission="leads.view">
      <LeadDetail leadId={leadId} />
    </PermissionGate>
  );
}
