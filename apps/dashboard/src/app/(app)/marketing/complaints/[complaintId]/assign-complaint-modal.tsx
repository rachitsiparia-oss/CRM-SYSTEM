"use client";

import { useState } from "react";
import { Search, X } from "lucide-react";

import { useAssignComplaint } from "@/lib/hooks/use-complaints";
import { useStaffList } from "@/lib/hooks/use-staff";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export function AssignComplaintModal({
  complaintId,
  open,
  onOpenChange,
}: {
  complaintId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const assignComplaint = useAssignComplaint(complaintId);
  const [searchInput, setSearchInput] = useState("");
  const [selectedStaffId, setSelectedStaffId] = useState<string | null>(null);
  const [selectedStaffName, setSelectedStaffName] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const search = useDebouncedValue(searchInput);
  const { data: staffResults } = useStaffList({
    page: 1,
    pageSize: 8,
    search: search.length >= 2 ? search : undefined,
  });

  function reset() {
    setSearchInput("");
    setSelectedStaffId(null);
    setSelectedStaffName("");
    setReason("");
    setError(null);
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="Assign complaint"
      description="Assign this complaint to a staff member."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!selectedStaffId || assignComplaint.isPending}
            onClick={() => {
              if (!selectedStaffId) return;
              setError(null);
              assignComplaint.mutate(
                {
                  assigned_staff_id: selectedStaffId,
                  reason: reason.trim() || null,
                },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not assign."),
                },
              );
            }}
          >
            {assignComplaint.isPending ? "Assigning…" : "Assign"}
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
          <Label>Staff member</Label>
          {selectedStaffId ? (
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">{selectedStaffName}</span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setSelectedStaffId(null);
                  setSelectedStaffName("");
                }}
              >
                <X className="size-3.5" />
                Change
              </Button>
            </div>
          ) : (
            <div className="relative">
              <Search className="text-muted-foreground absolute top-2.5 left-2.5 size-4" />
              <Input
                className="pl-8"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search staff…"
              />
              {search.length >= 2 && (staffResults?.data.length ?? 0) > 0 && (
                <div className="bg-background absolute z-10 mt-1 w-full rounded-md border shadow-md">
                  {staffResults?.data.map((staff) => (
                    <button
                      key={staff.id}
                      type="button"
                      className="hover:bg-muted flex w-full flex-col items-start px-3 py-2 text-left text-sm"
                      onClick={() => {
                        setSelectedStaffId(staff.id);
                        setSelectedStaffName(staff.display_name);
                        setSearchInput("");
                      }}
                    >
                      <span className="font-medium">{staff.display_name}</span>
                      <span className="text-muted-foreground text-xs">{staff.employee_code}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="assign-reason">Reason (optional)</Label>
          <Textarea
            id="assign-reason"
            rows={2}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
      </div>
    </Modal>
  );
}
