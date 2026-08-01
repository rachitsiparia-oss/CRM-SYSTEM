"use client";

import { useState } from "react";
import type { FeedbackSource, SentimentLabel } from "@rkpr/contracts";

import { useCreateFeedback } from "@/lib/hooks/use-feedback";
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

const SOURCES: FeedbackSource[] = [
  "website",
  "whatsapp",
  "email",
  "manual_entry",
  "public_review_reference",
];
const SENTIMENTS: SentimentLabel[] = ["positive", "neutral", "negative", "mixed"];

export function CreateFeedbackModal({
  open,
  onOpenChange,
  customerId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  customerId?: string;
}) {
  const createFeedback = useCreateFeedback();

  const [guestName, setGuestName] = useState("");
  const [source, setSource] = useState<FeedbackSource>("manual_entry");
  const [comment, setComment] = useState("");
  const [sentiment, setSentiment] = useState<SentimentLabel | "">("");
  const [overallRating, setOverallRating] = useState("");
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setGuestName("");
    setSource("manual_entry");
    setComment("");
    setSentiment("");
    setOverallRating("");
    setError(null);
  }

  const canSubmit = (!!customerId || guestName.trim().length > 0) && !createFeedback.isPending;

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="Log feedback"
      description="Record feedback received directly from a customer or guest."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!canSubmit}
            onClick={() => {
              setError(null);
              createFeedback.mutate(
                {
                  customer_id: customerId ?? null,
                  guest_name: customerId ? null : guestName.trim() || null,
                  source,
                  comment: comment.trim() || null,
                  sentiment: sentiment || null,
                  consent_for_follow_up: false,
                  ratings: overallRating.trim()
                    ? [{ dimension: "overall", rating: Math.round(Number(overallRating)) }]
                    : [],
                },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not log feedback."),
                },
              );
            }}
          >
            {createFeedback.isPending ? "Saving…" : "Log feedback"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}

        {!customerId && (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="feedback-guest-name">Guest name</Label>
            <Input
              id="feedback-guest-name"
              value={guestName}
              onChange={(e) => setGuestName(e.target.value)}
              placeholder="Required when no customer record is linked"
            />
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>Source</Label>
            <Select value={source} onValueChange={(v) => setSource(v as FeedbackSource)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SOURCES.map((value) => (
                  <SelectItem key={value} value={value}>
                    {value.replace(/_/g, " ")}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Sentiment</Label>
            <Select
              value={sentiment}
              onValueChange={(v) => setSentiment(v as SentimentLabel)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Unset" />
              </SelectTrigger>
              <SelectContent>
                {SENTIMENTS.map((value) => (
                  <SelectItem key={value} value={value}>
                    {value}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="feedback-overall-rating">Overall rating (1-5)</Label>
          <Input
            id="feedback-overall-rating"
            type="number"
            min={1}
            max={5}
            value={overallRating}
            onChange={(e) => setOverallRating(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="feedback-comment">Comment</Label>
          <Textarea
            id="feedback-comment"
            rows={3}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
        </div>
      </div>
    </Modal>
  );
}
