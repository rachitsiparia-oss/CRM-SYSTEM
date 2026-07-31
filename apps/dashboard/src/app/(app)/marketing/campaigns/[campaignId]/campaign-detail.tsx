"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import type { CampaignRecipient, CampaignStatus } from "@rkpr/contracts";
import { Rocket, RotateCw, Target } from "lucide-react";

import {
  useBuildCampaignAudience,
  useCampaignAnalytics,
  useCampaignDetail,
  useCampaignRecipients,
  useLaunchCampaign,
  useSyncCampaign,
  useTransitionCampaign,
} from "@/lib/hooks/use-campaigns";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import {
  CAMPAIGN_RECIPIENT_STATUS_TONES,
  CAMPAIGN_STATUS_TONES,
  formatDateTime,
  formatMinorUnits,
  humanize,
} from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { StatusBadge } from "@/components/status-badge";
import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/data-table/data-table";
import { SectionCard } from "@/components/section-card";
import { ErrorState } from "@/components/error-state";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const CAMPAIGN_TRANSITIONS: Record<CampaignStatus, CampaignStatus[]> = {
  draft: ["ready", "cancelled"],
  ready: ["scheduled", "draft", "cancelled"],
  scheduled: ["running", "cancelled"],
  running: ["paused", "completed", "cancelled", "failed"],
  paused: ["running", "cancelled"],
  completed: ["archived"],
  cancelled: ["archived"],
  failed: ["archived"],
  archived: [],
};

// Mirrors apps/api/app/campaigns/router.py's _TRANSITION_PERMISSION_OVERRIDES
// — every transition also requires the base campaigns.manage permission
// (the endpoint's own dependency); these targets require an additional
// permission on top of that.
const TRANSITION_PERMISSION_OVERRIDES: Partial<Record<CampaignStatus, string>> = {
  scheduled: "campaigns.approve",
  running: "campaigns.execute",
  paused: "campaigns.cancel",
  cancelled: "campaigns.cancel",
};

const PAGE_SIZE = 25;
const ALL = "__all";
const RECIPIENT_STATUSES = ["pending", "eligible", "suppressed", "sent", "failed"];

export function CampaignDetail({ campaignId }: { campaignId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: campaign, isLoading, isError, refetch } = useCampaignDetail(campaignId);

  const [error, setError] = useState<string | null>(null);
  const [recipientPage, setRecipientPage] = useState(1);
  const [recipientStatus, setRecipientStatus] = useState(ALL);

  const transitionCampaign = useTransitionCampaign(campaignId);
  const buildAudience = useBuildCampaignAudience(campaignId);
  const launchCampaign = useLaunchCampaign(campaignId);
  const syncCampaign = useSyncCampaign(campaignId);

  const { data: recipients, isLoading: recipientsLoading } = useCampaignRecipients(campaignId, {
    page: recipientPage,
    pageSize: PAGE_SIZE,
    status: recipientStatus === ALL ? undefined : recipientStatus,
  });

  const canManage = hasPermission(currentUser, "campaigns.manage");
  const canAnalytics = hasPermission(currentUser, "campaigns.analytics.view");
  const { data: analytics, isLoading: analyticsLoading } = useCampaignAnalytics(
    canAnalytics ? campaignId : undefined,
  );

  const recipientColumns = useMemo<ColumnDef<CampaignRecipient, unknown>[]>(
    () => [
      {
        id: "customer_id",
        header: "Customer ID",
        enableSorting: false,
        cell: ({ row }) => <span className="font-mono text-sm">{row.original.customer_id}</span>,
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.status)}
            tone={CAMPAIGN_RECIPIENT_STATUS_TONES[row.original.status]}
          />
        ),
      },
      {
        id: "attempts",
        header: "Attempts",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{row.original.attempt_count}</span>,
      },
      {
        id: "sent_at",
        header: "Sent",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{formatDateTime(row.original.sent_at)}</span>,
      },
      {
        id: "failure_reason",
        header: "Failure reason",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-muted-foreground text-sm">{row.original.failure_reason ?? "—"}</span>
        ),
      },
    ],
    [],
  );

  if (isLoading) return <div className="p-6 text-sm text-zinc-500">Loading…</div>;
  if (isError || !campaign) {
    return (
      <div className="p-6">
        <ErrorState title="Could not load this campaign" onRetry={() => void refetch()} />
      </div>
    );
  }

  const availableTransitions = CAMPAIGN_TRANSITIONS[campaign.status];
  const recipientPageCount = recipients
    ? Math.max(1, Math.ceil(recipients.pagination.total / PAGE_SIZE))
    : 0;

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link href="/marketing/campaigns" className="text-sm text-zinc-500 hover:underline">
          ← Campaigns
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="text-lg font-semibold">{campaign.name}</h1>
          <StatusBadge label={humanize(campaign.status)} tone={CAMPAIGN_STATUS_TONES[campaign.status]} />
        </div>
        <p className="text-muted-foreground text-sm">
          {campaign.code}
          {campaign.objective ? ` · ${campaign.objective}` : ""}
        </p>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex flex-wrap gap-2">
        {availableTransitions.map((target) => {
          const override = TRANSITION_PERMISSION_OVERRIDES[target];
          const allowed = canManage && (!override || hasPermission(currentUser, override));
          if (!allowed) return null;
          return (
            <Button
              key={target}
              size="sm"
              variant={target === "cancelled" || target === "archived" ? "outline" : "default"}
              disabled={transitionCampaign.isPending}
              onClick={() =>
                transitionCampaign.mutate(
                  { target_status: target },
                  {
                    onError: (err) =>
                      setError(err instanceof ApiError ? err.message : "That action could not be completed."),
                  },
                )
              }
            >
              Move to {humanize(target)}
            </Button>
          );
        })}
        {canManage && (
          <Button
            size="sm"
            variant="outline"
            disabled={buildAudience.isPending}
            onClick={() =>
              buildAudience.mutate(undefined, {
                onError: (err) =>
                  setError(err instanceof ApiError ? err.message : "Could not build the audience."),
              })
            }
          >
            <Target className="size-4" />
            Build audience
          </Button>
        )}
        {hasPermission(currentUser, "campaigns.execute") && campaign.status === "running" && (
          <>
            <Button
              size="sm"
              disabled={launchCampaign.isPending}
              onClick={() =>
                launchCampaign.mutate(undefined, {
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not launch the campaign."),
                })
              }
            >
              <Rocket className="size-4" />
              Launch
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={syncCampaign.isPending}
              onClick={() =>
                syncCampaign.mutate(undefined, {
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not sync recipient statuses."),
                })
              }
            >
              <RotateCw className="size-4" />
              Sync statuses
            </Button>
          </>
        )}
      </div>

      <SectionCard title="Configuration">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div>
            <p className="text-muted-foreground text-xs">Channels</p>
            <p className="text-sm font-medium">
              {Object.keys(campaign.channel_templates).join(", ") || "—"}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Target segments</p>
            <p className="text-sm font-medium">{campaign.target_segment_ids.length}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Estimated audience</p>
            <p className="text-sm font-medium">{campaign.estimated_size ?? "—"}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Budget</p>
            <p className="text-sm font-medium">
              {campaign.budget_minor != null ? formatMinorUnits(campaign.budget_minor) : "None"}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Audience snapshot</p>
            <p className="text-sm font-medium">{formatDateTime(campaign.audience_snapshot_taken_at)}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Scheduled at</p>
            <p className="text-sm font-medium">{formatDateTime(campaign.scheduled_at)}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Started at</p>
            <p className="text-sm font-medium">{formatDateTime(campaign.started_at)}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Completed at</p>
            <p className="text-sm font-medium">{formatDateTime(campaign.completed_at)}</p>
          </div>
        </div>
      </SectionCard>

      {canAnalytics && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <StatCard label="Total recipients" value={analytics?.total_recipients ?? 0} loading={analyticsLoading} />
          <StatCard label="Pending" value={analytics?.pending ?? 0} loading={analyticsLoading} />
          <StatCard label="Eligible" value={analytics?.eligible ?? 0} loading={analyticsLoading} />
          <StatCard label="Suppressed" value={analytics?.suppressed ?? 0} loading={analyticsLoading} />
          <StatCard label="Sent" value={analytics?.sent ?? 0} loading={analyticsLoading} />
        </div>
      )}

      <SectionCard
        title="Recipients"
        description="Every customer targeted by this campaign and their delivery status."
        actions={
          <Select
            value={recipientStatus}
            onValueChange={(value) => {
              setRecipientStatus(value);
              setRecipientPage(1);
            }}
          >
            <SelectTrigger className="w-40" aria-label="Filter by status">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All statuses</SelectItem>
              {RECIPIENT_STATUSES.map((s) => (
                <SelectItem key={s} value={s}>
                  {humanize(s)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        }
      >
        <DataTable
          columns={recipientColumns}
          data={recipients?.data ?? []}
          getRowId={(row) => row.id}
          loading={recipientsLoading}
          emptyTitle="No recipients yet"
          emptyDescription="Build the audience to populate this campaign's recipient list."
          pagination={{
            pageIndex: recipientPage - 1,
            pageCount: recipientPageCount,
            total: recipients?.pagination.total ?? 0,
            pageSize: PAGE_SIZE,
            onPageChange: (pageIndex) => setRecipientPage(pageIndex + 1),
          }}
        />
      </SectionCard>
    </div>
  );
}
