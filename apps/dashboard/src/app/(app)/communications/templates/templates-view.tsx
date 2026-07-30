"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import type { MessageTemplate } from "@rkpr/contracts";

import { useMessageTemplates, useCommunicationChannels } from "@/lib/hooks/use-communications";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { formatDateTime, humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { CardSkeleton } from "@/components/skeletons/card-skeleton";
import { Button } from "@/components/ui/button";
import { TemplateFormModal } from "./template-form-modal";
import { TemplatePreviewModal } from "./template-preview-modal";

export function TemplatesView() {
  const { data: currentUser } = useCurrentUser();
  const { data: templates, isLoading } = useMessageTemplates();
  const { data: channels } = useCommunicationChannels();
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<MessageTemplate | null>(null);
  const [previewing, setPreviewing] = useState<MessageTemplate | null>(null);

  const canManage = hasPermission(currentUser, "communications.templates.manage");
  const channelName = new Map((channels ?? []).map((c) => [c.id, c.name]));

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Message templates"
        description="Reusable, variable-driven message content for reservations, orders, and marketing."
        actions={
          canManage ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New template
            </Button>
          ) : null
        }
      />

      {isLoading ? (
        <CardSkeleton />
      ) : !templates || templates.length === 0 ? (
        <EmptyState title="No templates yet" description="Create the first message template." />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {templates.map((template) => (
            <SectionCard
              key={template.id}
              title={template.name}
              description={`${channelName.get(template.channel_id) ?? "—"} · ${humanize(template.category)}`}
              actions={
                <StatusBadge
                  label={humanize(template.status)}
                  tone={
                    template.status === "active"
                      ? "success"
                      : template.status === "archived"
                        ? "neutral"
                        : "warning"
                  }
                />
              }
            >
              <p className="text-sm whitespace-pre-wrap">{template.body}</p>
              <p className="text-muted-foreground mt-2 text-xs">
                Variables: {template.variables.length > 0 ? template.variables.join(", ") : "none"}
              </p>
              <p className="text-muted-foreground mt-1 text-xs">
                Updated {formatDateTime(template.updated_at)}
              </p>
              <div className="mt-3 flex gap-2">
                <Button size="sm" variant="outline" onClick={() => setPreviewing(template)}>
                  Preview
                </Button>
                {canManage && (
                  <Button size="sm" variant="outline" onClick={() => setEditing(template)}>
                    Edit
                  </Button>
                )}
              </div>
            </SectionCard>
          ))}
        </div>
      )}

      <TemplateFormModal open={showCreate} onOpenChange={setShowCreate} template={null} />
      <TemplateFormModal
        open={editing !== null}
        onOpenChange={(open) => !open && setEditing(null)}
        template={editing}
      />
      <TemplatePreviewModal
        template={previewing}
        onOpenChange={(open) => !open && setPreviewing(null)}
      />
    </div>
  );
}
