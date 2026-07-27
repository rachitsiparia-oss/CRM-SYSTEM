"use client";

import { useState } from "react";
import type { AdjustmentReason, WastageReason } from "@rkpr/contracts";

import {
  useCreateInventoryAdjustment,
  useCreateInventoryWastage,
  useInventoryAdjustments,
  useInventoryWastage,
} from "@/lib/hooks/use-inventory-operations";
import { useInventoryItemList } from "@/lib/hooks/use-inventory-items";
import { useInventoryLocations } from "@/lib/hooks/use-inventory-reference";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import {
  ADJUSTMENT_DIRECTION_TONES,
  formatDateTime,
  formatMinorUnits,
  formatQuantity,
  humanize,
} from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { FormField } from "@/components/forms/form-field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const ADJUSTMENT_REASONS: AdjustmentReason[] = [
  "count_difference",
  "data_correction",
  "damaged",
  "spoiled",
  "missing",
  "found",
  "unit_conversion_correction",
];

const WASTAGE_REASONS: WastageReason[] = [
  "preparation_waste",
  "overproduction",
  "spoilage",
  "expiry",
  "customer_return",
  "quality_failure",
  "accidental_damage",
  "staff_error",
  "other",
];

function AdjustmentForm() {
  const { data: items } = useInventoryItemList({ page: 1, pageSize: 100, sort: "name" });
  const { data: locations } = useInventoryLocations();
  const createAdjustment = useCreateInventoryAdjustment();

  const [itemId, setItemId] = useState("");
  const [locationId, setLocationId] = useState("");
  const [direction, setDirection] = useState<"increase" | "decrease">("decrease");
  const [quantity, setQuantity] = useState("");
  const [reasonCategory, setReasonCategory] = useState<AdjustmentReason>("count_difference");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleSubmit() {
    setError(null);
    setSuccess(false);
    if (!itemId || !locationId || !quantity || !reason.trim()) {
      setError("Item, location, quantity, and reason are required.");
      return;
    }
    try {
      await createAdjustment.mutateAsync({
        inventory_item_id: itemId,
        storage_location_id: locationId,
        direction,
        quantity,
        reason_category: reasonCategory,
        reason,
      });
      setQuantity("");
      setReason("");
      setSuccess(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The adjustment could not be posted.");
    }
  }

  return (
    <SectionCard title="Record a manual adjustment" description="A single-step, immediately-posted correction.">
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Item" htmlFor="adj-item" required>
          <Select value={itemId} onValueChange={setItemId}>
            <SelectTrigger id="adj-item">
              <SelectValue placeholder="Select an item" />
            </SelectTrigger>
            <SelectContent>
              {(items?.data ?? []).map((item) => (
                <SelectItem key={item.id} value={item.id}>
                  {item.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Location" htmlFor="adj-location" required>
          <Select value={locationId} onValueChange={setLocationId}>
            <SelectTrigger id="adj-location">
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
        <FormField label="Direction" htmlFor="adj-direction" required>
          <Select value={direction} onValueChange={(v) => setDirection(v as typeof direction)}>
            <SelectTrigger id="adj-direction">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="increase">Increase</SelectItem>
              <SelectItem value="decrease">Decrease</SelectItem>
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Quantity" htmlFor="adj-quantity" required>
          <Input
            id="adj-quantity"
            inputMode="decimal"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
          />
        </FormField>
        <FormField label="Reason category" htmlFor="adj-reason-category" required>
          <Select value={reasonCategory} onValueChange={(v) => setReasonCategory(v as AdjustmentReason)}>
            <SelectTrigger id="adj-reason-category">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ADJUSTMENT_REASONS.map((r) => (
                <SelectItem key={r} value={r}>
                  {humanize(r)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Reason" htmlFor="adj-reason" required className="sm:col-span-2">
          <Textarea id="adj-reason" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
        </FormField>
      </div>
      {error && (
        <p role="alert" className="text-destructive mt-3 text-sm">
          {error}
        </p>
      )}
      {success && <p className="text-success mt-3 text-sm">Adjustment posted.</p>}
      <div className="mt-4">
        <Button disabled={createAdjustment.isPending} onClick={() => void handleSubmit()}>
          {createAdjustment.isPending ? "Posting…" : "Post adjustment"}
        </Button>
      </div>
    </SectionCard>
  );
}

function AdjustmentHistory() {
  const { data: items } = useInventoryItemList({ page: 1, pageSize: 100, sort: "name" });
  const { data } = useInventoryAdjustments(1, 25);
  const itemName = new Map((items?.data ?? []).map((i) => [i.id, i.name]));

  return (
    <SectionCard title="Recent adjustments">
      {!data || data.data.length === 0 ? (
        <EmptyState title="No adjustments yet" />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Item</TableHead>
              <TableHead>Direction</TableHead>
              <TableHead>Quantity</TableHead>
              <TableHead>Value impact</TableHead>
              <TableHead>Reason</TableHead>
              <TableHead>Recorded</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.data.map((adjustment) => (
              <TableRow key={adjustment.id}>
                <TableCell>{itemName.get(adjustment.inventory_item_id) ?? "—"}</TableCell>
                <TableCell>
                  <StatusBadge
                    label={humanize(adjustment.direction)}
                    tone={ADJUSTMENT_DIRECTION_TONES[adjustment.direction]}
                  />
                </TableCell>
                <TableCell>{formatQuantity(adjustment.quantity)}</TableCell>
                <TableCell>
                  {adjustment.value_impact_minor !== null
                    ? formatMinorUnits(adjustment.value_impact_minor)
                    : "—"}
                </TableCell>
                <TableCell className="max-w-xs truncate">{adjustment.reason}</TableCell>
                <TableCell>{formatDateTime(adjustment.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </SectionCard>
  );
}

function WastageForm() {
  const { data: items } = useInventoryItemList({ page: 1, pageSize: 100, sort: "name" });
  const { data: locations } = useInventoryLocations();
  const createWastage = useCreateInventoryWastage();

  const [itemId, setItemId] = useState("");
  const [locationId, setLocationId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [reasonCategory, setReasonCategory] = useState<WastageReason>("spoilage");
  const [reason, setReason] = useState("");
  const [station, setStation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleSubmit() {
    setError(null);
    setSuccess(false);
    if (!itemId || !locationId || !quantity || !reason.trim()) {
      setError("Item, location, quantity, and reason are required.");
      return;
    }
    try {
      await createWastage.mutateAsync({
        inventory_item_id: itemId,
        storage_location_id: locationId,
        quantity,
        reason_category: reasonCategory,
        reason,
        station: station || null,
      });
      setQuantity("");
      setReason("");
      setStation("");
      setSuccess(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The wastage could not be recorded.");
    }
  }

  return (
    <SectionCard title="Record wastage" description="Always posts a negative stock movement.">
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Item" htmlFor="waste-item" required>
          <Select value={itemId} onValueChange={setItemId}>
            <SelectTrigger id="waste-item">
              <SelectValue placeholder="Select an item" />
            </SelectTrigger>
            <SelectContent>
              {(items?.data ?? []).map((item) => (
                <SelectItem key={item.id} value={item.id}>
                  {item.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Location" htmlFor="waste-location" required>
          <Select value={locationId} onValueChange={setLocationId}>
            <SelectTrigger id="waste-location">
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
        <FormField label="Quantity" htmlFor="waste-quantity" required>
          <Input
            id="waste-quantity"
            inputMode="decimal"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
          />
        </FormField>
        <FormField label="Reason category" htmlFor="waste-reason-category" required>
          <Select value={reasonCategory} onValueChange={(v) => setReasonCategory(v as WastageReason)}>
            <SelectTrigger id="waste-reason-category">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {WASTAGE_REASONS.map((r) => (
                <SelectItem key={r} value={r}>
                  {humanize(r)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Station" htmlFor="waste-station">
          <Input id="waste-station" value={station} onChange={(e) => setStation(e.target.value)} />
        </FormField>
        <FormField label="Reason" htmlFor="waste-reason" required className="sm:col-span-2">
          <Textarea
            id="waste-reason"
            rows={2}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </FormField>
      </div>
      {error && (
        <p role="alert" className="text-destructive mt-3 text-sm">
          {error}
        </p>
      )}
      {success && <p className="text-success mt-3 text-sm">Wastage recorded.</p>}
      <div className="mt-4">
        <Button disabled={createWastage.isPending} onClick={() => void handleSubmit()}>
          {createWastage.isPending ? "Recording…" : "Record wastage"}
        </Button>
      </div>
    </SectionCard>
  );
}

function WastageHistory() {
  const { data: items } = useInventoryItemList({ page: 1, pageSize: 100, sort: "name" });
  const { data } = useInventoryWastage(1, 25);
  const itemName = new Map((items?.data ?? []).map((i) => [i.id, i.name]));

  return (
    <SectionCard title="Recent wastage">
      {!data || data.data.length === 0 ? (
        <EmptyState title="No wastage recorded yet" />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Item</TableHead>
              <TableHead>Quantity</TableHead>
              <TableHead>Value impact</TableHead>
              <TableHead>Reason</TableHead>
              <TableHead>Recorded</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.data.map((record) => (
              <TableRow key={record.id}>
                <TableCell>{itemName.get(record.inventory_item_id) ?? "—"}</TableCell>
                <TableCell>{formatQuantity(record.quantity)}</TableCell>
                <TableCell>
                  {record.value_impact_minor !== null
                    ? formatMinorUnits(record.value_impact_minor)
                    : "—"}
                </TableCell>
                <TableCell className="max-w-xs truncate">{record.reason}</TableCell>
                <TableCell>{formatDateTime(record.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </SectionCard>
  );
}

export function AdjustmentsAndWastage() {
  const { data: currentUser } = useCurrentUser();
  const canAdjust = hasPermission(currentUser, "inventory.adjustments.create");
  const canWaste = hasPermission(currentUser, "inventory.wastage.create");

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Adjustments & Wastage"
        description="Manual stock corrections and recorded waste, spoilage, or damage."
      />

      <Tabs defaultValue="adjustments">
        <TabsList>
          <TabsTrigger value="adjustments">Adjustments</TabsTrigger>
          <TabsTrigger value="wastage">Wastage</TabsTrigger>
        </TabsList>
        <TabsContent value="adjustments" className="mt-4 flex flex-col gap-4">
          {canAdjust && <AdjustmentForm />}
          <AdjustmentHistory />
        </TabsContent>
        <TabsContent value="wastage" className="mt-4 flex flex-col gap-4">
          {canWaste && <WastageForm />}
          <WastageHistory />
        </TabsContent>
      </Tabs>
    </div>
  );
}
