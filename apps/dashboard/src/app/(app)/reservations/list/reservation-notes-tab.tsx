"use client";

import { useState } from "react";
import { StickyNote } from "lucide-react";
import type { ReservationNoteType } from "@rkpr/contracts";

import { useAddReservationNote, useReservationNotes } from "@/lib/hooks/use-reservations";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { formatDateTime, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { FormField } from "@/components/forms/form-field";
import { EmptyState } from "@/components/empty-state";
import { CardSkeleton } from "@/components/skeletons/card-skeleton";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const NOTE_TYPES: ReservationNoteType[] = [
  "internal",
  "kitchen",
  "guest_preference",
  "allergy",
  "special_occasion",
  "accessibility",
  "celebration",
  "vip",
];

export function ReservationNotesTab({ reservationId }: { reservationId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: notes, isLoading } = useReservationNotes(reservationId);
  const addNote = useAddReservationNote(reservationId);

  const [content, setContent] = useState("");
  const [noteType, setNoteType] = useState<ReservationNoteType>("internal");
  const [isInternal, setIsInternal] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const canManage = hasPermission(currentUser, "reservations.notes.manage");

  async function handleAdd() {
    setError(null);
    try {
      await addNote.mutateAsync({
        content: content.trim(),
        note_type: noteType,
        is_internal: isInternal,
      });
      setContent("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The note could not be added.");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {canManage && (
        <SectionCard title="Add a note">
          <div className="flex flex-col gap-3">
            <FormField label="Type" htmlFor="reservation-note-type">
              <Select
                value={noteType}
                onValueChange={(value) => setNoteType(value as ReservationNoteType)}
              >
                <SelectTrigger id="reservation-note-type">
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
            <FormField label="Note" htmlFor="reservation-note-content">
              <Textarea
                id="reservation-note-content"
                rows={3}
                value={content}
                onChange={(e) => setContent(e.target.value)}
              />
            </FormField>
          </div>
          <div className="mt-3 flex items-center justify-between">
            <label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={isInternal}
                onCheckedChange={(checked) => setIsInternal(checked === true)}
              />
              Internal only (not shown to the guest)
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
          <EmptyState
            icon={StickyNote}
            title="No notes yet"
            description="Notes about this reservation will appear here."
          />
        ) : (
          <ul className="flex flex-col gap-3">
            {notes.map((note) => (
              <li key={note.id} className="rounded-md border p-3">
                <p className="text-sm whitespace-pre-wrap">{note.content}</p>
                <p className="text-muted-foreground mt-1 text-xs">
                  {humanize(note.note_type)} · {note.is_internal ? "Internal" : "Guest-facing"} ·{" "}
                  {formatDateTime(note.created_at)}
                </p>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}
