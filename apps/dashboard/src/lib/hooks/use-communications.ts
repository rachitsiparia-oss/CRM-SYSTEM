"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  CommunicationAnalytics,
  CommunicationChannel,
  CommunicationChannelUpdateInput,
  CommunicationConsentCreateInput,
  CommunicationPreference,
  CommunicationPreferenceUpdateInput,
  CommunicationSuppression,
  CommunicationSuppressionCreateInput,
  Conversation,
  ConversationAssignInput,
  ConversationCreateInput,
  ConversationPriorityInput,
  ConversationTimelineEntry,
  ConversationTransitionInput,
  CustomerCommunicationStats,
  DataResponse,
  InternalNoteCreateInput,
  ManualCallLog,
  ManualCallLogCreateInput,
  Message,
  MessageCreateInput,
  MessageTemplate,
  MessageTemplateCreateInput,
  MessageTemplateUpdateInput,
  PaginatedResponse,
  ScheduledMessage,
  ScheduledMessageCreateInput,
  TemplatePreviewInput,
  TemplatePreviewOutput,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/communications";

// --- Channels ------------------------------------------------------------

export function useCommunicationChannels() {
  return useQuery({
    queryKey: ["communications", "channels"],
    queryFn: () => apiFetchClient<DataResponse<CommunicationChannel[]>>(`${BASE}/channels`),
    select: (response) => response.data,
  });
}

export function useUpdateCommunicationChannel(channelId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CommunicationChannelUpdateInput) =>
      apiFetchClient<DataResponse<CommunicationChannel>>(`${BASE}/channels/${channelId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["communications", "channels"] }),
  });
}

// --- Inbox / Conversations -----------------------------------------------

export interface InboxListParams {
  page: number;
  pageSize: number;
  conversationStatus?: string;
  priority?: string;
  channelId?: string;
  assignedStaffId?: string;
  unreadOnly?: boolean;
  unassignedOnly?: boolean;
  mineOnly?: boolean;
  search?: string;
}

export function useInboxList(params: InboxListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.conversationStatus) query.set("conversation_status", params.conversationStatus);
  if (params.priority) query.set("priority", params.priority);
  if (params.channelId) query.set("channel_id", params.channelId);
  if (params.assignedStaffId) query.set("assigned_staff_id", params.assignedStaffId);
  if (params.unreadOnly) query.set("unread_only", "true");
  if (params.unassignedOnly) query.set("unassigned_only", "true");
  if (params.mineOnly) query.set("mine_only", "true");
  if (params.search) query.set("search", params.search);

  return useQuery({
    queryKey: ["communications", "inbox", params],
    queryFn: () => apiFetchClient<PaginatedResponse<Conversation>>(`${BASE}/inbox?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useConversationDetail(conversationId: string | undefined) {
  return useQuery({
    queryKey: ["communications", "conversations", conversationId],
    queryFn: () =>
      apiFetchClient<DataResponse<Conversation>>(`${BASE}/conversations/${conversationId}`),
    select: (response) => response.data,
    enabled: !!conversationId,
  });
}

export function useConversationMessages(conversationId: string | undefined, page: number) {
  return useQuery({
    queryKey: ["communications", "conversations", conversationId, "messages", page],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<Message>>(
        `${BASE}/conversations/${conversationId}/messages?page=${page}&page_size=50`,
      ),
    enabled: !!conversationId,
  });
}

export function useConversationTimeline(conversationId: string | undefined) {
  return useQuery({
    queryKey: ["communications", "conversations", conversationId, "timeline"],
    queryFn: () =>
      apiFetchClient<DataResponse<ConversationTimelineEntry[]>>(
        `${BASE}/conversations/${conversationId}/timeline`,
      ),
    select: (response) => response.data,
    enabled: !!conversationId,
  });
}

function useInvalidateConversation(conversationId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["communications", "inbox"] });
    if (conversationId) {
      queryClient.invalidateQueries({ queryKey: ["communications", "conversations", conversationId] });
    }
  };
}

export function useCreateConversation() {
  const invalidate = useInvalidateConversation();
  return useMutation({
    mutationFn: (input: ConversationCreateInput) =>
      apiFetchClient<DataResponse<Conversation>>(`${BASE}/conversations`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useTransitionConversation(conversationId: string) {
  const invalidate = useInvalidateConversation(conversationId);
  return useMutation({
    mutationFn: (input: ConversationTransitionInput) =>
      apiFetchClient<DataResponse<Conversation>>(
        `${BASE}/conversations/${conversationId}/transition`,
        { method: "POST", body: input },
      ),
    onSuccess: invalidate,
  });
}

export function useAssignConversation(conversationId: string) {
  const invalidate = useInvalidateConversation(conversationId);
  return useMutation({
    mutationFn: (input: ConversationAssignInput) =>
      apiFetchClient<DataResponse<Conversation>>(`${BASE}/conversations/${conversationId}/assign`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useSetConversationPriority(conversationId: string) {
  const invalidate = useInvalidateConversation(conversationId);
  return useMutation({
    mutationFn: (input: ConversationPriorityInput) =>
      apiFetchClient<DataResponse<Conversation>>(`${BASE}/conversations/${conversationId}/priority`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

function useInvalidateMessages(conversationId: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({
      queryKey: ["communications", "conversations", conversationId, "messages"],
    });
    queryClient.invalidateQueries({
      queryKey: ["communications", "conversations", conversationId, "timeline"],
    });
    queryClient.invalidateQueries({ queryKey: ["communications", "conversations", conversationId] });
    queryClient.invalidateQueries({ queryKey: ["communications", "inbox"] });
  };
}

export function useReplyToConversation(conversationId: string) {
  const invalidate = useInvalidateMessages(conversationId);
  return useMutation({
    mutationFn: (input: MessageCreateInput) =>
      apiFetchClient<DataResponse<Message>>(`${BASE}/conversations/${conversationId}/messages`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useAddInternalNote(conversationId: string) {
  const invalidate = useInvalidateMessages(conversationId);
  return useMutation({
    mutationFn: (input: InternalNoteCreateInput) =>
      apiFetchClient<DataResponse<Message>>(`${BASE}/conversations/${conversationId}/notes`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

// --- Templates -------------------------------------------------------------

export function useMessageTemplates(params: { channelId?: string; category?: string } = {}) {
  const query = new URLSearchParams();
  if (params.channelId) query.set("channel_id", params.channelId);
  if (params.category) query.set("category", params.category);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return useQuery({
    queryKey: ["communications", "templates", params],
    queryFn: () => apiFetchClient<DataResponse<MessageTemplate[]>>(`${BASE}/templates${suffix}`),
    select: (response) => response.data,
  });
}

export function useCreateMessageTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: MessageTemplateCreateInput) =>
      apiFetchClient<DataResponse<MessageTemplate>>(`${BASE}/templates`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["communications", "templates"] }),
  });
}

export function useUpdateMessageTemplate(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: MessageTemplateUpdateInput) =>
      apiFetchClient<DataResponse<MessageTemplate>>(`${BASE}/templates/${templateId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["communications", "templates"] }),
  });
}

export function usePreviewMessageTemplate(templateId: string) {
  return useMutation({
    mutationFn: (input: TemplatePreviewInput) =>
      apiFetchClient<DataResponse<TemplatePreviewOutput>>(`${BASE}/templates/${templateId}/preview`, {
        method: "POST",
        body: input,
      }),
  });
}

// --- Scheduled messages ------------------------------------------------------

export function useScheduledMessages(status?: string) {
  const suffix = status ? `?scheduled_status=${status}&page=1&page_size=50` : "?page=1&page_size=50";
  return useQuery({
    queryKey: ["communications", "scheduled", status],
    queryFn: () => apiFetchClient<PaginatedResponse<ScheduledMessage>>(`${BASE}/scheduled${suffix}`),
  });
}

export function useCreateScheduledMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ScheduledMessageCreateInput) =>
      apiFetchClient<DataResponse<ScheduledMessage>>(`${BASE}/scheduled`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["communications", "scheduled"] }),
  });
}

export function useCancelScheduledMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (scheduledId: string) =>
      apiFetchClient<DataResponse<ScheduledMessage>>(`${BASE}/scheduled/${scheduledId}/cancel`, {
        method: "POST",
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["communications", "scheduled"] }),
  });
}

// --- Preferences / Consent / Suppression -------------------------------------

export function useCommunicationPreference(customerId: string | undefined) {
  return useQuery({
    queryKey: ["communications", "preferences", customerId],
    queryFn: () =>
      apiFetchClient<DataResponse<CommunicationPreference>>(`${BASE}/preferences/${customerId}`),
    select: (response) => response.data,
    enabled: !!customerId,
  });
}

export function useUpdateCommunicationPreference(customerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CommunicationPreferenceUpdateInput) =>
      apiFetchClient<DataResponse<CommunicationPreference>>(`${BASE}/preferences/${customerId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["communications", "preferences", customerId] }),
  });
}

export function useCreateCommunicationConsent() {
  return useMutation({
    mutationFn: (input: CommunicationConsentCreateInput) =>
      apiFetchClient<DataResponse<CommunicationPreference>>(`${BASE}/consents`, {
        method: "POST",
        body: input,
      }),
  });
}

export function useSuppressions(activeOnly = true) {
  return useQuery({
    queryKey: ["communications", "suppressions", activeOnly],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<CommunicationSuppression>>(
        `${BASE}/suppressions?active_only=${activeOnly}&page=1&page_size=50`,
      ),
  });
}

export function useCreateSuppression() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CommunicationSuppressionCreateInput) =>
      apiFetchClient<DataResponse<CommunicationSuppression>>(`${BASE}/suppressions`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["communications", "suppressions"] }),
  });
}

export function useLiftSuppression() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (suppressionId: string) =>
      apiFetchClient<DataResponse<CommunicationSuppression>>(
        `${BASE}/suppressions/${suppressionId}/lift`,
        { method: "POST" },
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["communications", "suppressions"] }),
  });
}

// --- Call logs ---------------------------------------------------------------

export function useCallLogs(customerId?: string) {
  const suffix = customerId ? `&customer_id=${customerId}` : "";
  return useQuery({
    queryKey: ["communications", "call-logs", customerId],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<ManualCallLog>>(
        `${BASE}/call-logs?page=1&page_size=50${suffix}`,
      ),
  });
}

export function useCreateCallLog() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ManualCallLogCreateInput) =>
      apiFetchClient<DataResponse<ManualCallLog>>(`${BASE}/call-logs`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["communications", "call-logs"] }),
  });
}

// --- Analytics -----------------------------------------------------------

export function useCommunicationAnalytics() {
  return useQuery({
    queryKey: ["communications", "analytics"],
    queryFn: () => apiFetchClient<DataResponse<CommunicationAnalytics>>(`${BASE}/analytics`),
    select: (response) => response.data,
    refetchInterval: 60_000,
  });
}

export function useCustomerCommunicationStats(customerId: string | undefined) {
  return useQuery({
    queryKey: ["communications", "customers", customerId, "stats"],
    queryFn: () =>
      apiFetchClient<DataResponse<CustomerCommunicationStats>>(`${BASE}/customers/${customerId}/stats`),
    select: (response) => response.data,
    enabled: !!customerId,
  });
}
