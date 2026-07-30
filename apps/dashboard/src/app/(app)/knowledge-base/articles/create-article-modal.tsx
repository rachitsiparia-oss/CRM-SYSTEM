"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { ArticleType } from "@rkpr/contracts";

import { useCreateArticle } from "@/lib/hooks/use-knowledge";
import { useKnowledgeCategories } from "@/lib/hooks/use-knowledge";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const ARTICLE_TYPES: ArticleType[] = [
  "sop",
  "policy",
  "procedure",
  "checklist",
  "guide",
  "troubleshooting",
  "training_material",
  "emergency_instruction",
  "announcement",
];

export function CreateArticleModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const { data: categories } = useKnowledgeCategories();
  const createArticle = useCreateArticle();

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [articleType, setArticleType] = useState<ArticleType>("sop");
  const [categoryId, setCategoryId] = useState<string>("");
  const [requiresAck, setRequiresAck] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setTitle("");
    setContent("");
    setArticleType("sop");
    setCategoryId("");
    setRequiresAck(false);
    setError(null);
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="New knowledge article"
      description="Starts as a draft — submit it for review when ready."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!title.trim() || !content.trim() || createArticle.isPending}
            onClick={() => {
              createArticle.mutate(
                {
                  title: title.trim(),
                  content: content.trim(),
                  article_type: articleType,
                  category_id: categoryId || null,
                  requires_acknowledgement: requiresAck,
                },
                {
                  onSuccess: (response) => {
                    reset();
                    onOpenChange(false);
                    router.push(`/knowledge-base/articles/${response.data.id}`);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not create the article."),
                },
              );
            }}
          >
            Create draft
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="article-title">Title</Label>
          <Input id="article-title" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>Type</Label>
            <Select value={articleType} onValueChange={(v) => setArticleType(v as ArticleType)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ARTICLE_TYPES.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type.replace(/_/g, " ")}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Category</Label>
            <Select value={categoryId} onValueChange={setCategoryId}>
              <SelectTrigger>
                <SelectValue placeholder="No category" />
              </SelectTrigger>
              <SelectContent>
                {(categories ?? []).map((category) => (
                  <SelectItem key={category.id} value={category.id}>
                    {category.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="article-content">Content</Label>
          <Textarea
            id="article-content"
            rows={8}
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={requiresAck}
            onChange={(e) => setRequiresAck(e.target.checked)}
          />
          Requires staff acknowledgement once published
        </label>
      </div>
    </Modal>
  );
}
