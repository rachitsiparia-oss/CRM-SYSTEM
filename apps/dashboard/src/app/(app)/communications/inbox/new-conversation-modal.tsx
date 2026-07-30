"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { useCreateConversation, useCommunicationChannels } from "@/lib/hooks/use-communications";
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

const schema = z.object({
  channelId: z.string().min(1, "Select a channel."),
  phoneE164: z.string().trim().optional(),
  email: z.string().trim().optional(),
  subject: z.string().trim().optional(),
  initialMessageBody: z.string().trim().optional(),
});
type Values = z.infer<typeof schema>;

export function NewConversationModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const { data: channels } = useCommunicationChannels();
  const createConversation = useCreateConversation();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  function resetForm() {
    reset({});
    setFormError(null);
  }

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      const created = await createConversation.mutateAsync({
        channel_id: values.channelId,
        phone_e164: values.phoneE164 || null,
        email: values.email || null,
        subject: values.subject || null,
        initial_message_body: values.initialMessageBody || null,
      });
      resetForm();
      onOpenChange(false);
      router.push(`/communications/inbox/${created.data.id}`);
    } catch (error) {
      setFormError(
        error instanceof ApiError ? error.message : "The conversation could not be created.",
      );
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) resetForm();
        onOpenChange(next);
      }}
      title="New conversation"
      description="Start a conversation with a customer on any channel."
      footer={
        <>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            type="submit"
            form="new-conversation-form"
            disabled={createConversation.isPending}
          >
            {createConversation.isPending ? "Creating…" : "Start conversation"}
          </Button>
        </>
      }
    >
      <form id="new-conversation-form" onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-3">
        <FormField label="Channel" htmlFor="conversation-channel" error={errors.channelId?.message}>
          <Select value={watch("channelId")} onValueChange={(value) => setValue("channelId", value)}>
            <SelectTrigger id="conversation-channel">
              <SelectValue placeholder="Select a channel" />
            </SelectTrigger>
            <SelectContent>
              {(channels ?? [])
                .filter((channel) => channel.outbound_enabled)
                .map((channel) => (
                  <SelectItem key={channel.id} value={channel.id}>
                    {channel.name}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Phone (E.164)" htmlFor="conversation-phone" error={errors.phoneE164?.message}>
          <Input id="conversation-phone" placeholder="+91XXXXXXXXXX" {...register("phoneE164")} />
        </FormField>
        <FormField label="Email" htmlFor="conversation-email" error={errors.email?.message}>
          <Input id="conversation-email" type="email" {...register("email")} />
        </FormField>
        <FormField label="Subject" htmlFor="conversation-subject" error={errors.subject?.message}>
          <Input id="conversation-subject" {...register("subject")} />
        </FormField>
        <FormField
          label="Opening message (optional)"
          htmlFor="conversation-initial-message"
          error={errors.initialMessageBody?.message}
        >
          <Textarea id="conversation-initial-message" rows={3} {...register("initialMessageBody")} />
        </FormField>
        {formError && (
          <p role="alert" className="text-destructive text-sm">
            {formError}
          </p>
        )}
      </form>
    </Modal>
  );
}
