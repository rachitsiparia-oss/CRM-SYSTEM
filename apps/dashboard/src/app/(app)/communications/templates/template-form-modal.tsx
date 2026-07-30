"use client";

import { useState } from "react";
import type { MessageTemplate, TemplateCategory } from "@rkpr/contracts";

import {
  useCommunicationChannels,
  useCreateMessageTemplate,
  useUpdateMessageTemplate,
} from "@/lib/hooks/use-communications";
import { humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { FormField } from "@/components/forms/form-field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const CATEGORIES: TemplateCategory[] = [
  "reservation_confirmation",
  "reservation_reminder",
  "reservation_cancellation",
  "reservation_modification",
  "waitlist_update",
  "table_ready",
  "order_confirmation",
  "order_ready",
  "order_cancellation",
  "feedback_request",
  "lead_follow_up",
  "birthday",
  "anniversary",
  "general",
];

export function TemplateFormModal({
  open,
  onOpenChange,
  template,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  template: MessageTemplate | null;
}) {
  const { data: channels } = useCommunicationChannels();
  const createTemplate = useCreateMessageTemplate();
  const updateTemplate = useUpdateMessageTemplate(template?.id ?? "");

  // Radix's Dialog unmounts its content on close (no `forceMount`), so
  // these lazy initializers re-run fresh from `template` every time the
  // modal reopens — no `useEffect`-driven state sync needed (React
  // Compiler flags synchronous setState-in-effect as cascading-render-prone).
  const [name, setName] = useState(() => template?.name ?? "");
  const [code, setCode] = useState(() => template?.code ?? "");
  const [channelId, setChannelId] = useState(() => template?.channel_id ?? "");
  const [category, setCategory] = useState<TemplateCategory>(() => template?.category ?? "general");
  const [subject, setSubject] = useState(() => template?.subject ?? "");
  const [body, setBody] = useState(() => template?.body ?? "");
  const [variables, setVariables] = useState(() => template?.variables.join(", ") ?? "");
  const [error, setError] = useState<string | null>(null);

  const isPending = createTemplate.isPending || updateTemplate.isPending;
  const variableList = variables
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);

  async function handleSubmit() {
    setError(null);
    try {
      if (template) {
        await updateTemplate.mutateAsync({
          name,
          subject: subject || null,
          body,
          variables: variableList,
          version: template.version,
        });
      } else {
        await createTemplate.mutateAsync({
          name,
          code,
          channel_id: channelId,
          category,
          subject: subject || null,
          body,
          variables: variableList,
        });
      }
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The template could not be saved.");
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title={template ? `Edit ${template.name}` : "New template"}
      description="Only declared variables may be used in the body — {variable_name} placeholders."
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!name.trim() || !body.trim() || (!template && (!code.trim() || !channelId)) || isPending}
            onClick={() => void handleSubmit()}
          >
            {isPending ? "Saving…" : "Save template"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <FormField label="Name" htmlFor="template-name">
          <Input id="template-name" value={name} onChange={(e) => setName(e.target.value)} />
        </FormField>
        {!template && (
          <FormField label="Code" htmlFor="template-code">
            <Input id="template-code" value={code} onChange={(e) => setCode(e.target.value)} />
          </FormField>
        )}
        {!template && (
          <FormField label="Channel" htmlFor="template-channel">
            <Select value={channelId} onValueChange={setChannelId}>
              <SelectTrigger id="template-channel">
                <SelectValue placeholder="Select a channel" />
              </SelectTrigger>
              <SelectContent>
                {(channels ?? []).map((channel) => (
                  <SelectItem key={channel.id} value={channel.id}>
                    {channel.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>
        )}
        {!template && (
          <FormField label="Category" htmlFor="template-category">
            <Select value={category} onValueChange={(value) => setCategory(value as TemplateCategory)}>
              <SelectTrigger id="template-category">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CATEGORIES.map((cat) => (
                  <SelectItem key={cat} value={cat}>
                    {humanize(cat)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>
        )}
        <FormField label="Subject (optional, for email)" htmlFor="template-subject">
          <Input id="template-subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
        </FormField>
        <FormField label="Body" htmlFor="template-body">
          <Textarea
            id="template-body"
            rows={5}
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
        </FormField>
        <FormField
          label="Variables (comma-separated)"
          htmlFor="template-variables"
          description="e.g. customer_name, reservation_number"
        >
          <Input
            id="template-variables"
            value={variables}
            onChange={(e) => setVariables(e.target.value)}
          />
        </FormField>
        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}
      </div>
    </Modal>
  );
}
