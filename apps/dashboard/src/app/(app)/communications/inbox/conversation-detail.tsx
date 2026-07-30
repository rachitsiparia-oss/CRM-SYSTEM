"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { useConversationDetail } from "@/lib/hooks/use-communications";
import { CONVERSATION_PRIORITY_TONES, CONVERSATION_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { PageSkeleton } from "@/components/skeletons/page-skeleton";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
import { SectionCard } from "@/components/section-card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ConversationStatusControl } from "./conversation-status-control";
import { ConversationAssignControl } from "./conversation-assign-control";
import { ConversationComposer } from "./conversation-composer";
import { ConversationTimeline } from "./conversation-timeline";

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd className="text-sm">{value}</dd>
    </div>
  );
}

export function ConversationDetail({ conversationId }: { conversationId: string }) {
  const { data: conversation, isLoading, isError, refetch } = useConversationDetail(conversationId);

  if (isLoading) {
    return (
      <div className="flex-1 p-6">
        <PageSkeleton />
      </div>
    );
  }

  if (isError || !conversation) {
    return (
      <div className="flex-1 p-6">
        <ErrorState
          variant="404"
          title="Conversation not found"
          description="This conversation may not exist, or you may not have access to it."
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link
          href="/communications/inbox"
          className="text-muted-foreground inline-flex items-center gap-1 text-sm hover:underline"
        >
          <ArrowLeft className="size-3.5" />
          Inbox
        </Link>
      </div>

      <PageHeader
        title={conversation.subject ?? conversation.guest_name ?? conversation.conversation_number}
        description={`${conversation.conversation_number} · Last activity ${formatDateTime(conversation.last_activity_at)}`}
        actions={
          <div className="flex gap-2">
            <StatusBadge
              label={humanize(conversation.priority)}
              tone={CONVERSATION_PRIORITY_TONES[conversation.priority]}
            />
            <StatusBadge
              label={humanize(conversation.status)}
              tone={CONVERSATION_STATUS_TONES[conversation.status]}
            />
          </div>
        }
      />

      <Tabs defaultValue="conversation">
        <TabsList>
          <TabsTrigger value="conversation">Conversation</TabsTrigger>
          <TabsTrigger value="details">Details</TabsTrigger>
        </TabsList>

        <TabsContent value="conversation" className="flex flex-col gap-4">
          <ConversationTimeline conversationId={conversation.id} />
          <ConversationComposer conversation={conversation} />
        </TabsContent>

        <TabsContent value="details" className="flex flex-col gap-4">
          <SectionCard title="Contact">
            <dl className="grid grid-cols-2 gap-4">
              <Field label="Guest name" value={conversation.guest_name ?? "—"} />
              <Field label="Phone" value={conversation.phone_e164 ?? "—"} />
              <Field label="Email" value={conversation.email ?? "—"} />
              <Field label="Source" value={humanize(conversation.source)} />
              <Field
                label="Unread"
                value={conversation.unread_count > 0 ? String(conversation.unread_count) : "None"}
              />
              <Field
                label="First response"
                value={formatDateTime(conversation.first_response_at)}
              />
            </dl>
          </SectionCard>
          <ConversationAssignControl conversation={conversation} />
          <ConversationStatusControl conversation={conversation} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
