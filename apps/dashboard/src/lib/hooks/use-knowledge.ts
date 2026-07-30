"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  DataResponse,
  KnowledgeAcknowledgement,
  KnowledgeAnalytics,
  KnowledgeArticle,
  KnowledgeArticleCreateInput,
  KnowledgeArticleTransitionInput,
  KnowledgeArticleUpdateInput,
  KnowledgeArticleVersion,
  KnowledgeAssignment,
  KnowledgeAssignmentCreateInput,
  KnowledgeAttachment,
  KnowledgeCategory,
  KnowledgeCategoryCreateInput,
  KnowledgeCategoryUpdateInput,
  KnowledgeRelation,
  KnowledgeRelationCreateInput,
  KnowledgeReview,
  KnowledgeVisibilityRule,
  KnowledgeVisibilityRuleCreateInput,
  PaginatedResponse,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/knowledge";

// --- Categories -----------------------------------------------------------

export function useKnowledgeCategories() {
  return useQuery({
    queryKey: ["knowledge", "categories"],
    queryFn: () => apiFetchClient<DataResponse<KnowledgeCategory[]>>(`${BASE}/categories`),
    select: (response) => response.data,
  });
}

export function useCreateKnowledgeCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: KnowledgeCategoryCreateInput) =>
      apiFetchClient<DataResponse<KnowledgeCategory>>(`${BASE}/categories`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["knowledge", "categories"] }),
  });
}

export function useUpdateKnowledgeCategory(categoryId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: KnowledgeCategoryUpdateInput) =>
      apiFetchClient<DataResponse<KnowledgeCategory>>(`${BASE}/categories/${categoryId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["knowledge", "categories"] }),
  });
}

// --- Articles -----------------------------------------------------------

export interface KnowledgeArticleListParams {
  page: number;
  pageSize: number;
  status?: string;
  categoryId?: string;
  articleType?: string;
  ownerStaffId?: string;
}

export function useArticleList(params: KnowledgeArticleListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.status) query.set("status", params.status);
  if (params.categoryId) query.set("category_id", params.categoryId);
  if (params.articleType) query.set("article_type", params.articleType);
  if (params.ownerStaffId) query.set("owner_staff_id", params.ownerStaffId);

  return useQuery({
    queryKey: ["knowledge", "articles", "list", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<KnowledgeArticle>>(`${BASE}/articles?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export interface KnowledgeSearchParams {
  page: number;
  pageSize: number;
  q?: string;
  categoryId?: string;
  articleType?: string;
  publishedOnly?: boolean;
}

export function useKnowledgeSearch(params: KnowledgeSearchParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.q) query.set("q", params.q);
  if (params.categoryId) query.set("category_id", params.categoryId);
  if (params.articleType) query.set("article_type", params.articleType);
  query.set("published_only", String(params.publishedOnly ?? true));

  return useQuery({
    queryKey: ["knowledge", "search", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<KnowledgeArticle>>(`${BASE}/search?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useArticleDetail(articleId: string | undefined) {
  return useQuery({
    queryKey: ["knowledge", "articles", articleId],
    queryFn: () => apiFetchClient<DataResponse<KnowledgeArticle>>(`${BASE}/articles/${articleId}`),
    select: (response) => response.data,
    enabled: !!articleId,
  });
}

export function useArticleVersions(articleId: string | undefined) {
  return useQuery({
    queryKey: ["knowledge", "articles", articleId, "versions"],
    queryFn: () =>
      apiFetchClient<DataResponse<KnowledgeArticleVersion[]>>(`${BASE}/articles/${articleId}/versions`),
    select: (response) => response.data,
    enabled: !!articleId,
  });
}

export function useArticleTimeline(articleId: string | undefined) {
  return useQuery({
    queryKey: ["knowledge", "articles", articleId, "timeline"],
    queryFn: () =>
      apiFetchClient<DataResponse<KnowledgeReview[]>>(`${BASE}/articles/${articleId}/timeline`),
    select: (response) => response.data,
    enabled: !!articleId,
  });
}

function useInvalidateArticle(articleId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["knowledge", "articles"] });
    if (articleId) queryClient.invalidateQueries({ queryKey: ["knowledge", "articles", articleId] });
  };
}

export function useCreateArticle() {
  const invalidate = useInvalidateArticle();
  return useMutation({
    mutationFn: (input: KnowledgeArticleCreateInput) =>
      apiFetchClient<DataResponse<KnowledgeArticle>>(`${BASE}/articles`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateArticle(articleId: string) {
  const invalidate = useInvalidateArticle(articleId);
  return useMutation({
    mutationFn: (input: KnowledgeArticleUpdateInput) =>
      apiFetchClient<DataResponse<KnowledgeArticle>>(`${BASE}/articles/${articleId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useSubmitArticle(articleId: string) {
  const invalidate = useInvalidateArticle(articleId);
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<KnowledgeArticle>>(`${BASE}/articles/${articleId}/submit`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}

export function useReviewArticle(articleId: string) {
  const invalidate = useInvalidateArticle(articleId);
  return useMutation({
    mutationFn: (input: KnowledgeArticleTransitionInput) =>
      apiFetchClient<DataResponse<KnowledgeArticle>>(`${BASE}/articles/${articleId}/review`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function usePublishArticle(articleId: string) {
  const invalidate = useInvalidateArticle(articleId);
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<KnowledgeArticle>>(`${BASE}/articles/${articleId}/publish`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}

export function useTransitionArticle(articleId: string) {
  const invalidate = useInvalidateArticle(articleId);
  return useMutation({
    mutationFn: (input: KnowledgeArticleTransitionInput) =>
      apiFetchClient<DataResponse<KnowledgeArticle>>(`${BASE}/articles/${articleId}/transition`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

// --- Tags and relations ---------------------------------------------------

export function useAssignArticleTags(articleId: string) {
  const invalidate = useInvalidateArticle(articleId);
  return useMutation({
    mutationFn: (tagIds: string[]) =>
      apiFetchClient<DataResponse<{ status: string }>>(`${BASE}/articles/${articleId}/tags`, {
        method: "POST",
        body: { tag_ids: tagIds },
      }),
    onSuccess: invalidate,
  });
}

export function useArticleRelations(articleId: string | undefined) {
  return useQuery({
    queryKey: ["knowledge", "articles", articleId, "relations"],
    queryFn: () =>
      apiFetchClient<DataResponse<KnowledgeRelation[]>>(`${BASE}/articles/${articleId}/relations`),
    select: (response) => response.data,
    enabled: !!articleId,
  });
}

export function useCreateArticleRelation(articleId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: KnowledgeRelationCreateInput) =>
      apiFetchClient<DataResponse<KnowledgeRelation>>(`${BASE}/articles/${articleId}/relations`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["knowledge", "articles", articleId, "relations"] }),
  });
}

// --- Visibility rules ------------------------------------------------------

export function useVisibilityRules(articleId: string | undefined) {
  return useQuery({
    queryKey: ["knowledge", "articles", articleId, "visibility-rules"],
    queryFn: () =>
      apiFetchClient<DataResponse<KnowledgeVisibilityRule[]>>(
        `${BASE}/articles/${articleId}/visibility-rules`,
      ),
    select: (response) => response.data,
    enabled: !!articleId,
  });
}

export function useAddVisibilityRule(articleId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: KnowledgeVisibilityRuleCreateInput) =>
      apiFetchClient<DataResponse<KnowledgeVisibilityRule>>(
        `${BASE}/articles/${articleId}/visibility-rules`,
        { method: "POST", body: input },
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["knowledge", "articles", articleId, "visibility-rules"],
      }),
  });
}

// --- Attachments ------------------------------------------------------

export function useArticleAttachments(articleId: string | undefined) {
  return useQuery({
    queryKey: ["knowledge", "articles", articleId, "attachments"],
    queryFn: () =>
      apiFetchClient<DataResponse<KnowledgeAttachment[]>>(`${BASE}/articles/${articleId}/attachments`),
    select: (response) => response.data,
    enabled: !!articleId,
  });
}

export function useUploadAttachment(articleId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return apiFetchClient<DataResponse<KnowledgeAttachment>>(
        `${BASE}/articles/${articleId}/attachments`,
        { method: "POST", body: formData },
      );
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["knowledge", "articles", articleId, "attachments"] }),
  });
}

// --- Assignments and acknowledgements ---------------------------------------

export function useArticleAssignments(articleId: string | undefined) {
  return useQuery({
    queryKey: ["knowledge", "articles", articleId, "assignments"],
    queryFn: () =>
      apiFetchClient<DataResponse<KnowledgeAssignment[]>>(`${BASE}/articles/${articleId}/assignments`),
    select: (response) => response.data,
    enabled: !!articleId,
  });
}

export function useCreateAssignment(articleId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: KnowledgeAssignmentCreateInput) =>
      apiFetchClient<DataResponse<KnowledgeAssignment>>(`${BASE}/articles/${articleId}/assignments`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["knowledge", "articles", articleId, "assignments"] }),
  });
}

export function useAcknowledgeArticle(articleId: string) {
  const invalidate = useInvalidateArticle(articleId);
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<KnowledgeAcknowledgement>>(
        `${BASE}/articles/${articleId}/acknowledge`,
        { method: "POST" },
      ),
    onSuccess: invalidate,
  });
}

export function useMyAcknowledgements() {
  return useQuery({
    queryKey: ["knowledge", "acknowledgements", "mine"],
    queryFn: () =>
      apiFetchClient<DataResponse<KnowledgeAcknowledgement[]>>(`${BASE}/acknowledgements/mine`),
    select: (response) => response.data,
  });
}

// --- Analytics -----------------------------------------------------------

export function useKnowledgeAnalytics() {
  return useQuery({
    queryKey: ["knowledge", "analytics"],
    queryFn: () => apiFetchClient<DataResponse<KnowledgeAnalytics>>(`${BASE}/analytics`),
    select: (response) => response.data,
  });
}
