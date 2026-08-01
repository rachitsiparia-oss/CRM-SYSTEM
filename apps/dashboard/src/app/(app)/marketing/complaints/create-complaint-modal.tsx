"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Search, X } from "lucide-react";
import type { ComplaintCategory, ComplaintSeverity } from "@rkpr/contracts";

import { useCreateComplaint } from "@/lib/hooks/use-complaints";
import { useCustomerList } from "@/lib/hooks/use-customers";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { humanize } from "@/lib/crm-display";
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

const CATEGORIES: ComplaintCategory[] = [
  "food_quality",
  "incorrect_item",
  "missing_item",
  "packaging",
  "delay",
  "delivery",
  "payment",
  "refund",
  "reservation",
  "staff_behavior",
  "cleanliness",
  "allergy_or_dietary",
  "promotion",
  "loyalty",
  "communication",
  "corporate_order",
  "other",
];
const SEVERITIES: ComplaintSeverity[] = ["low", "medium", "high", "critical"];

export function CreateComplaintModal({
  open,
  onOpenChange,
  customerId,
  customerName,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  customerId?: string;
  customerName?: string;
}) {
  const router = useRouter();
  const createComplaint = useCreateComplaint();

  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(customerId ?? null);
  const [selectedCustomerName, setSelectedCustomerName] = useState(customerName ?? "");
  const [searchInput, setSearchInput] = useState("");
  const [category, setCategory] = useState<ComplaintCategory>("food_quality");
  const [severity, setSeverity] = useState<ComplaintSeverity>("medium");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const search = useDebouncedValue(searchInput);
  const { data: customerResults } = useCustomerList({
    page: 1,
    pageSize: 8,
    search: search.length >= 2 ? search : undefined,
  });

  function reset() {
    setSelectedCustomerId(customerId ?? null);
    setSelectedCustomerName(customerName ?? "");
    setSearchInput("");
    setCategory("food_quality");
    setSeverity("medium");
    setTitle("");
    setDescription("");
    setError(null);
  }

  const canSubmit =
    !!selectedCustomerId && title.trim() && description.trim() && !createComplaint.isPending;

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="New complaint"
      description="Record a customer complaint for case management and SLA tracking."
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!canSubmit}
            onClick={() => {
              if (!selectedCustomerId) return;
              setError(null);
              createComplaint.mutate(
                {
                  customer_id: selectedCustomerId,
                  source_type: "direct",
                  category,
                  title: title.trim(),
                  description: description.trim(),
                  severity,
                },
                {
                  onSuccess: (response) => {
                    reset();
                    onOpenChange(false);
                    router.push(`/marketing/complaints/${response.data.id}`);
                  },
                  onError: (err) =>
                    setError(
                      err instanceof ApiError ? err.message : "Could not create the complaint.",
                    ),
                },
              );
            }}
          >
            {createComplaint.isPending ? "Creating…" : "Create complaint"}
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

        <div className="flex flex-col gap-1.5">
          <Label>Customer</Label>
          {selectedCustomerId ? (
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">{selectedCustomerName}</span>
              {!customerId && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setSelectedCustomerId(null);
                    setSelectedCustomerName("");
                  }}
                >
                  <X className="size-3.5" />
                  Change
                </Button>
              )}
            </div>
          ) : (
            <div className="relative">
              <Search className="text-muted-foreground absolute top-2.5 left-2.5 size-4" />
              <Input
                className="pl-8"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search customers…"
              />
              {search.length >= 2 && (customerResults?.data.length ?? 0) > 0 && (
                <div className="bg-background absolute z-10 mt-1 w-full rounded-md border shadow-md">
                  {customerResults?.data.map((customer) => (
                    <button
                      key={customer.id}
                      type="button"
                      className="hover:bg-muted flex w-full flex-col items-start px-3 py-2 text-left text-sm"
                      onClick={() => {
                        setSelectedCustomerId(customer.id);
                        setSelectedCustomerName(customer.display_name);
                        setSearchInput("");
                      }}
                    >
                      <span className="font-medium">{customer.display_name}</span>
                      <span className="text-muted-foreground text-xs">
                        {customer.customer_number}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>Category</Label>
            <Select value={category} onValueChange={(v) => setCategory(v as ComplaintCategory)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CATEGORIES.map((value) => (
                  <SelectItem key={value} value={value}>
                    {humanize(value)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Severity</Label>
            <Select value={severity} onValueChange={(v) => setSeverity(v as ComplaintSeverity)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SEVERITIES.map((value) => (
                  <SelectItem key={value} value={value}>
                    {humanize(value)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="complaint-title">Title</Label>
          <Input id="complaint-title" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="complaint-description">Description</Label>
          <Textarea
            id="complaint-description"
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
      </div>
    </Modal>
  );
}
