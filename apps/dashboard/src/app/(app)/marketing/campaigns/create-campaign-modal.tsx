"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, X } from "lucide-react";

import { useCreateCampaign } from "@/lib/hooks/use-campaigns";
import { useSegmentList } from "@/lib/hooks/use-segments";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MultiSelect } from "@/components/forms/multi-select";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const CHANNELS = ["whatsapp", "email", "sms"];

interface ChannelTemplateRow {
  key: string;
  channel: string;
  templateCode: string;
}

function emptyRow(): ChannelTemplateRow {
  return { key: crypto.randomUUID(), channel: "whatsapp", templateCode: "" };
}

export function CreateCampaignModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const createCampaign = useCreateCampaign();
  const { data: segments } = useSegmentList({ page: 1, pageSize: 100, status: "active" });

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [objective, setObjective] = useState("");
  const [targetSegmentIds, setTargetSegmentIds] = useState<string[]>([]);
  const [rows, setRows] = useState<ChannelTemplateRow[]>([emptyRow()]);
  const [error, setError] = useState<string | null>(null);

  const segmentOptions = useMemo(
    () => (segments?.data ?? []).map((s) => ({ label: s.name, value: s.id })),
    [segments],
  );

  const channelTemplates = useMemo(() => {
    const entries: Record<string, string> = {};
    for (const row of rows) {
      if (row.channel && row.templateCode.trim()) entries[row.channel] = row.templateCode.trim();
    }
    return entries;
  }, [rows]);

  const isValid =
    code.trim() && name.trim() && targetSegmentIds.length > 0 && Object.keys(channelTemplates).length > 0;

  function reset() {
    setCode("");
    setName("");
    setObjective("");
    setTargetSegmentIds([]);
    setRows([emptyRow()]);
    setError(null);
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="New campaign"
      size="lg"
      description="Starts as a draft — build the audience and get approval before scheduling."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!isValid || createCampaign.isPending}
            onClick={() => {
              setError(null);
              createCampaign.mutate(
                {
                  code: code.trim(),
                  name: name.trim(),
                  objective: objective.trim() || null,
                  channel_templates: channelTemplates,
                  target_segment_ids: targetSegmentIds,
                },
                {
                  onSuccess: (response) => {
                    reset();
                    onOpenChange(false);
                    router.push(`/marketing/campaigns/${response.data.id}`);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not create the campaign."),
                },
              );
            }}
          >
            Create draft
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="campaign-code">Code</Label>
            <Input id="campaign-code" value={code} onChange={(e) => setCode(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="campaign-name">Name</Label>
            <Input id="campaign-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="campaign-objective">Objective</Label>
          <Input id="campaign-objective" value={objective} onChange={(e) => setObjective(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label>Target segments</Label>
          <MultiSelect
            options={segmentOptions}
            value={targetSegmentIds}
            onChange={setTargetSegmentIds}
            placeholder="Select one or more segments…"
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label>Channel templates</Label>
          {rows.map((row, index) => (
            <div key={row.key} className="flex items-center gap-2">
              <Select
                value={row.channel}
                onValueChange={(value) =>
                  setRows((prev) => prev.map((r, i) => (i === index ? { ...r, channel: value } : r)))
                }
              >
                <SelectTrigger className="w-36">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CHANNELS.map((channel) => (
                    <SelectItem key={channel} value={channel}>
                      {channel}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                placeholder="Template code"
                value={row.templateCode}
                onChange={(e) =>
                  setRows((prev) =>
                    prev.map((r, i) => (i === index ? { ...r, templateCode: e.target.value } : r)),
                  )
                }
              />
              <Button
                type="button"
                size="icon"
                variant="ghost"
                disabled={rows.length === 1}
                aria-label="Remove channel template row"
                onClick={() => setRows((prev) => prev.filter((_, i) => i !== index))}
              >
                <X className="size-4" />
              </Button>
            </div>
          ))}
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="w-fit"
            onClick={() => setRows((prev) => [...prev, emptyRow()])}
          >
            <Plus className="size-4" />
            Add channel
          </Button>
        </div>
      </div>
    </Modal>
  );
}
