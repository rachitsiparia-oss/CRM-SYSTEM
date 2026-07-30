"use client";

import { useState } from "react";
import type { MessageTemplate } from "@rkpr/contracts";

import { usePreviewMessageTemplate } from "@/lib/hooks/use-communications";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { FormField } from "@/components/forms/form-field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

function TemplatePreviewContents({
  template,
  onOpenChange,
}: {
  template: MessageTemplate;
  onOpenChange: (open: boolean) => void;
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<{ subject: string | null; body: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const preview = usePreviewMessageTemplate(template.id);

  async function handlePreview() {
    setError(null);
    try {
      const response = await preview.mutateAsync({ variables: values });
      setResult(response.data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The template could not be rendered.");
    }
  }

  return (
    <Modal
      open
      onOpenChange={onOpenChange}
      title={`Preview: ${template.name}`}
      description="Fill in sample values for each declared variable."
      footer={
        <Button disabled={preview.isPending} onClick={() => void handlePreview()}>
          {preview.isPending ? "Rendering…" : "Render preview"}
        </Button>
      }
    >
      <div className="flex flex-col gap-3">
        {template.variables.map((variable) => (
          <FormField key={variable} label={variable} htmlFor={`preview-${variable}`}>
            <Input
              id={`preview-${variable}`}
              value={values[variable] ?? ""}
              onChange={(e) => setValues((prev) => ({ ...prev, [variable]: e.target.value }))}
            />
          </FormField>
        ))}
        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}
        {result && (
          <div className="rounded-md border p-3">
            {result.subject && <p className="text-sm font-medium">{result.subject}</p>}
            <p className="mt-1 text-sm whitespace-pre-wrap">{result.body}</p>
          </div>
        )}
      </div>
    </Modal>
  );
}

/** Keyed by `template.id` so a fresh instance — with fresh preview-input
 * state — mounts each time a different template is previewed, instead of
 * syncing state from a prop in a `useEffect`. */
export function TemplatePreviewModal({
  template,
  onOpenChange,
}: {
  template: MessageTemplate | null;
  onOpenChange: (open: boolean) => void;
}) {
  if (!template) return null;
  return (
    <TemplatePreviewContents key={template.id} template={template} onOpenChange={onOpenChange} />
  );
}
