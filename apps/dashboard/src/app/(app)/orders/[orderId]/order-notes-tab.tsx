"use client";

import { useState } from "react";
import { StickyNote } from "lucide-react";

import { useAddOrderNote, useOrderNotes } from "@/lib/hooks/use-orders";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { formatDateTime } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { FormField } from "@/components/forms/form-field";
import { EmptyState } from "@/components/empty-state";
import { CardSkeleton } from "@/components/skeletons/card-skeleton";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";

export function OrderNotesTab({ orderId }: { orderId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: notes, isLoading } = useOrderNotes(orderId);
  const addNote = useAddOrderNote(orderId);

  const [content, setContent] = useState("");
  const [isInternal, setIsInternal] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const canManage = hasPermission(currentUser, "orders.notes.manage");

  async function handleAdd() {
    setError(null);
    try {
      await addNote.mutateAsync({ content: content.trim(), isInternal });
      setContent("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The note could not be added.");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {canManage && (
        <SectionCard title="Add a note">
          <FormField label="Note" htmlFor="order-note-content">
            <Textarea
              id="order-note-content"
              rows={3}
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
          </FormField>
          <div className="mt-3 flex items-center justify-between">
            <label className="flex items-center gap-2 text-sm">
              <Checkbox checked={isInternal} onCheckedChange={(checked) => setIsInternal(checked === true)} />
              Internal only (not shown to the customer)
            </label>
            <Button disabled={!content.trim() || addNote.isPending} onClick={() => void handleAdd()}>
              {addNote.isPending ? "Adding…" : "Add note"}
            </Button>
          </div>
          {error && (
            <p role="alert" className="text-destructive mt-3 text-sm">
              {error}
            </p>
          )}
        </SectionCard>
      )}

      <SectionCard title="Notes">
        {isLoading ? (
          <CardSkeleton />
        ) : !notes || notes.length === 0 ? (
          <EmptyState icon={StickyNote} title="No notes yet" description="Notes about this order will appear here." />
        ) : (
          <ul className="flex flex-col gap-3">
            {notes.map((note) => (
              <li key={note.id} className="rounded-md border p-3">
                <p className="text-sm whitespace-pre-wrap">{note.content}</p>
                <p className="text-muted-foreground mt-1 text-xs">
                  {note.is_internal ? "Internal" : "Customer-facing"} · {formatDateTime(note.created_at)}
                </p>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}
