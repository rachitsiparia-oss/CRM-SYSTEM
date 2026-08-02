"use client";

import type { Integration, IntegrationHealthState } from "@rkpr/contracts";
import { RefreshCw } from "lucide-react";

import {
  useDisableIntegration,
  useIntegrationList,
  usePauseIntegration,
  useResumeIntegration,
  useRunIntegrationHealthChecks,
} from "@/lib/hooks/use-integrations";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { humanize, formatDateTime } from "@/lib/crm-display";
import type { StatusTone } from "@/components/status-badge";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const HEALTH_TONE: Record<IntegrationHealthState, StatusTone> = {
  unknown: "neutral",
  healthy: "success",
  degraded: "warning",
  unhealthy: "danger",
  disabled: "neutral",
};

export function IntegrationsView() {
  const { data: currentUser } = useCurrentUser();
  const canUpdate = hasPermission(currentUser, "settings.integrations.update");
  const { data: integrations, isLoading } = useIntegrationList();
  const runHealthChecks = useRunIntegrationHealthChecks();

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Integrations"
        description="Status and health across every known integration point — a read-mostly registry, not a second place that owns provider credentials."
        actions={
          canUpdate ? (
            <Button
              variant="outline"
              disabled={runHealthChecks.isPending}
              onClick={() => runHealthChecks.mutate()}
            >
              <RefreshCw className="size-4" />
              {runHealthChecks.isPending ? "Checking…" : "Run health checks"}
            </Button>
          ) : null
        }
      />

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      ) : !integrations || integrations.length === 0 ? (
        <EmptyState title="No integrations registered" />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {integrations.map((integration) => (
            <IntegrationCard key={integration.id} integration={integration} canUpdate={canUpdate} />
          ))}
        </div>
      )}
    </div>
  );
}

function IntegrationCard({
  integration,
  canUpdate,
}: {
  integration: Integration;
  canUpdate: boolean;
}) {
  const pause = usePauseIntegration();
  const resume = useResumeIntegration();
  const disable = useDisableIntegration();
  const pending = pause.isPending || resume.isPending || disable.isPending;

  return (
    <SectionCard
      title={integration.display_name}
      description={`${humanize(integration.category)} · ${integration.provider_code}`}
      actions={
        <StatusBadge label={humanize(integration.health_state)} tone={HEALTH_TONE[integration.health_state]} />
      }
    >
      <div className="flex flex-col gap-2 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Status</span>
          <span>{humanize(integration.status)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Credential</span>
          <span>{integration.credential_reference ?? "Not configured"}</span>
        </div>
        {integration.last_failure_at && (
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Last failure</span>
            <span>{formatDateTime(integration.last_failure_at)}</span>
          </div>
        )}
      </div>
      {canUpdate && (
        <div className="mt-3 flex gap-2">
          {integration.is_enabled ? (
            <Button
              size="sm"
              variant="outline"
              disabled={pending}
              onClick={() => pause.mutate(integration.id)}
            >
              Pause
            </Button>
          ) : (
            <Button
              size="sm"
              variant="outline"
              disabled={pending || integration.status === "disabled"}
              onClick={() => resume.mutate(integration.id)}
            >
              Resume
            </Button>
          )}
          {integration.status !== "disabled" && (
            <Button
              size="sm"
              variant="ghost"
              disabled={pending}
              onClick={() => disable.mutate(integration.id)}
            >
              Disable
            </Button>
          )}
        </div>
      )}
    </SectionCard>
  );
}
