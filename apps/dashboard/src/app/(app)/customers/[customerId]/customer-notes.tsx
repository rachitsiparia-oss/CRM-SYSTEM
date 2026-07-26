"use client";

import { useState } from "react";
import { StickyNote } from "lucide-react";

import { useAddCustomerNote, useCustomerNotes } from "@/lib/hooks/use-customers";
import { formatDateTime, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { EmptyState } from "@/components/empty-state";
import { FormField } from "@/components/forms/form-field";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const NOTE_TYPES = [
  "general",
  "service_preference",
  "complaint",
  "recovery",
  "corporate",
  "delivery",
  "reservation",
  "dietary",
];

export function CustomerNotes({
  customerId,
  canEdit,
}: {
  customerId: string;
  canEdit: boolean;
}) {
  const { data: notes, isLoading } = useCustomerNotes(customerId);
  const addNote = useAddCustomerNote(customerId);

  const [content, setContent] = useState("");
  const [noteType, setNoteType] = useState("general");
  const [isSensitive, setIsSensitive] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleAdd() {
    setFormError(null);
    try {
      await addNote.mutateAsync({
        note_type: noteType,
        content: content.trim(),
        is_sensitive: isSensitive,
      });
      setContent("");
      setNoteType("general");
      setIsSensitive(false);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "The note could not be saved.");
    }
  }

  return (
    <SectionCard
      title="Notes"
      description="Sensitive notes are only visible to staff with the sensitive-notes permission."
    >
      <div className="flex flex-col gap-4">
        {canEdit && (
          <div className="bg-muted/40 flex flex-col gap-3 rounded-md border p-4">
            <FormField label="Note" htmlFor="note-content" required>
              <Textarea
                id="note-content"
                rows={3}
                value={content}
                onChange={(event) => setContent(event.target.value)}
                placeholder="What should the team know about this customer?"
              />
            </FormField>
            <div className="flex flex-wrap items-end gap-4">
              <FormField label="Type" htmlFor="note-type" className="w-48">
                <Select value={noteType} onValueChange={setNoteType}>
                  <SelectTrigger id="note-type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {NOTE_TYPES.map((type) => (
                      <SelectItem key={type} value={type}>
                        {humanize(type)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
              <label className="flex items-center gap-2 pb-2 text-sm">
                <Checkbox
                  checked={isSensitive}
                  onCheckedChange={(checked) => setIsSensitive(checked === true)}
                />
                Mark as sensitive
              </label>
              <Button
                size="sm"
                className="mb-1"
                disabled={!content.trim() || addNote.isPending}
                onClick={() => void handleAdd()}
              >
                {addNote.isPending ? "Saving…" : "Add note"}
              </Button>
            </div>
            {formError && (
              <p role="alert" className="text-destructive text-sm">
                {formError}
              </p>
            )}
          </div>
        )}

        {isLoading ? (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </div>
        ) : !notes || notes.length === 0 ? (
          <EmptyState
            icon={StickyNote}
            title="No notes yet"
            description="Notes capture service preferences, complaints, and anything the team should remember."
          />
        ) : (
          <ul className="flex flex-col gap-3">
            {notes.map((note) => (
              <li key={note.id} className="rounded-md border p-3">
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">{humanize(note.note_type)}</Badge>
                  {note.is_sensitive && <Badge variant="destructive">Sensitive</Badge>}
                  <span className="text-muted-foreground text-xs">
                    {formatDateTime(note.created_at)}
                    {note.updated_at ? ` · edited ${formatDateTime(note.updated_at)}` : ""}
                  </span>
                </div>
                <p className="text-sm whitespace-pre-wrap">{note.content}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </SectionCard>
  );
}
