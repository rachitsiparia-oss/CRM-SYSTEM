"use client";

import { useState } from "react";
import { Plus } from "lucide-react";

import {
  useCreateFeatureFlag,
  useFeatureFlagList,
  useSetFeatureFlagEnabled,
} from "@/lib/hooks/use-feature-flags";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export function FeatureFlagsView() {
  const { data: currentUser } = useCurrentUser();
  const canManage = hasPermission(currentUser, "settings.manage");
  const [showCreate, setShowCreate] = useState(false);
  const { data: flags, isLoading } = useFeatureFlagList();
  const setEnabled = useSetFeatureFlagEnabled();

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Feature Flags"
        description="Runtime on/off switches for optional capabilities — a stable per-code toggle, not a targeting or rollout engine."
        actions={
          canManage ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New flag
            </Button>
          ) : null
        }
      />

      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : !flags || flags.length === 0 ? (
        <EmptyState
          title="No feature flags yet"
          action={canManage ? <Button onClick={() => setShowCreate(true)}>New flag</Button> : undefined}
        />
      ) : (
        <div className="overflow-hidden rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Description</TableHead>
                <TableHead className="text-right">Enabled</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {flags.map((flag) => (
                <TableRow key={flag.id}>
                  <TableCell className="font-mono text-xs">{flag.code}</TableCell>
                  <TableCell className="text-sm">{flag.name}</TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {flag.description ?? "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    <Switch
                      checked={flag.is_enabled}
                      disabled={!canManage || setEnabled.isPending}
                      onCheckedChange={(checked) =>
                        setEnabled.mutate({ flagId: flag.id, isEnabled: checked })
                      }
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <CreateFlagModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}

function CreateFlagModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const createFlag = useCreateFeatureFlag();

  const reset = () => {
    setCode("");
    setName("");
    setDescription("");
    setError(null);
  };

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="New feature flag"
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!code.trim() || !name.trim() || createFlag.isPending}
            onClick={() => {
              setError(null);
              createFlag.mutate(
                { code: code.trim(), name: name.trim(), description: description.trim() || null },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not create this flag."),
                },
              );
            }}
          >
            {createFlag.isPending ? "Creating…" : "Create flag"}
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
          <Label htmlFor="flag-code">Code</Label>
          <Input
            id="flag-code"
            placeholder="domain.capability"
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="flag-name">Name</Label>
          <Input id="flag-name" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="flag-description">Description</Label>
          <Textarea
            id="flag-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
          />
        </div>
      </div>
    </Modal>
  );
}
