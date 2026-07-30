import { PermissionGate } from "@/components/permission-gate";
import { ConversationDetail } from "../conversation-detail";

export default async function Page({
  params,
}: {
  params: Promise<{ conversationId: string }>;
}) {
  const { conversationId } = await params;
  return (
    <PermissionGate permission="communications.view">
      <ConversationDetail conversationId={conversationId} />
    </PermissionGate>
  );
}
