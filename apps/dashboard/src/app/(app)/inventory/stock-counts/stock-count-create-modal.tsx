"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { useCreateInventoryStockCount } from "@/lib/hooks/use-inventory-operations";
import { useInventoryLocations } from "@/lib/hooks/use-inventory-reference";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { FormField } from "@/components/forms/form-field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function StockCountCreateModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const { data: locations } = useInventoryLocations();
  const createCount = useCreateInventoryStockCount();

  const [locationId, setLocationId] = useState("");
  const [scheduledDate, setScheduledDate] = useState("");
  const [error, setError] = useState<string | null>(null);

  function resetForm() {
    setLocationId("");
    setScheduledDate("");
    setError(null);
  }

  async function handleSubmit() {
    setError(null);
    if (!locationId) {
      setError("Select a location.");
      return;
    }
    try {
      const created = await createCount.mutateAsync({
        storage_location_id: locationId,
        scheduled_date: scheduledDate || null,
      });
      resetForm();
      onOpenChange(false);
      router.push(`/inventory/stock-counts/${created.data.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The stock count could not be created.");
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) resetForm();
        onOpenChange(next);
      }}
      title="New stock count"
      description="Only one active session is allowed per location at a time."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button disabled={createCount.isPending} onClick={() => void handleSubmit()}>
            {createCount.isPending ? "Creating…" : "Create session"}
          </Button>
        </>
      }
    >
      <div className="grid gap-4">
        <FormField label="Location" htmlFor="count-location" required>
          <Select value={locationId} onValueChange={setLocationId}>
            <SelectTrigger id="count-location">
              <SelectValue placeholder="Select a location" />
            </SelectTrigger>
            <SelectContent>
              {(locations ?? []).map((location) => (
                <SelectItem key={location.id} value={location.id}>
                  {location.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Scheduled date" htmlFor="count-date">
          <Input
            id="count-date"
            type="date"
            value={scheduledDate}
            onChange={(e) => setScheduledDate(e.target.value)}
          />
        </FormField>
        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}
      </div>
    </Modal>
  );
}
