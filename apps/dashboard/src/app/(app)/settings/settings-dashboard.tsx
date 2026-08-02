"use client";

import Link from "next/link";
import {
  AlertTriangle,
  Cable,
  Clock,
  Database,
  Flag,
  ListChecks,
  ScrollText,
  Settings2,
  Workflow,
} from "lucide-react";

import { useJobQueueStats } from "@/lib/hooks/use-jobs";
import { useSchedulerStatus } from "@/lib/hooks/use-scheduler";
import { useDeadLetterList } from "@/lib/hooks/use-dead-letter";
import { useIntegrationList } from "@/lib/hooks/use-integrations";
import { PageHeader } from "@/components/page-header";
import { MetricCard } from "@/components/metric-card";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

const SECTIONS = [
  { href: "/settings/jobs", icon: ListChecks, title: "Jobs", description: "Background job execution history and retry state." },
  { href: "/settings/scheduler", icon: Clock, title: "Scheduler", description: "Cron catalog and the global scheduler on/off switch." },
  { href: "/settings/dead-letter", icon: AlertTriangle, title: "Dead Letter Queue", description: "Jobs and events that exhausted their retry budget." },
  { href: "/settings/integrations", icon: Cable, title: "Integrations", description: "Registry and health of every external integration point." },
  { href: "/settings/feature-flags", icon: Flag, title: "Feature Flags", description: "Runtime on/off switches for optional capabilities." },
  { href: "/settings/operational", icon: Settings2, title: "Operational Settings", description: "Maintenance mode, retry defaults, and worker limits." },
  { href: "/settings/event-log", icon: ScrollText, title: "Event Log", description: "The domain event / outbox publication log." },
  { href: "/settings/cache", icon: Database, title: "Cache", description: "Redis cache families, TTLs, and manual invalidation." },
];

export function SettingsDashboard() {
  const { data: queueStats, isLoading: queueStatsLoading } = useJobQueueStats();
  const { data: scheduler, isLoading: schedulerLoading } = useSchedulerStatus();
  const { data: deadLetter, isLoading: deadLetterLoading } = useDeadLetterList({
    resolutionStatus: undefined,
    page: 1,
    pageSize: 1,
  });
  const { data: integrations, isLoading: integrationsLoading } = useIntegrationList();

  const activeJobs = (queueStats ?? [])
    .filter((s) => ["pending", "queued", "running", "retry_wait"].includes(s.status))
    .reduce((sum, s) => sum + s.count, 0);
  const unhealthyIntegrations = (integrations ?? []).filter(
    (i) => i.is_enabled && i.health_state === "unhealthy",
  ).length;

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Integrations, Security & Settings"
        description="Background jobs, the scheduler, dead-letter recovery, integrations, feature flags, operational settings, the event log, and cache."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          icon={Workflow}
          label="Active jobs"
          value={activeJobs.toLocaleString()}
          loading={queueStatsLoading}
        />
        <MetricCard
          icon={Clock}
          label="Scheduler"
          value={scheduler?.scheduler_enabled ? "Running" : "Paused"}
          loading={schedulerLoading}
        />
        <MetricCard
          icon={AlertTriangle}
          label="Dead-lettered items"
          value={(deadLetter?.pagination.total ?? 0).toLocaleString()}
          loading={deadLetterLoading}
        />
        <MetricCard
          icon={Cable}
          label="Unhealthy integrations"
          value={unhealthyIntegrations.toLocaleString()}
          loading={integrationsLoading}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {SECTIONS.map((section) => (
          <Link key={section.href} href={section.href}>
            <Card className="h-full transition-colors hover:border-primary/50">
              <CardHeader className="flex flex-row items-center gap-3">
                <section.icon className="text-muted-foreground size-5" />
                <div>
                  <CardTitle className="text-base">{section.title}</CardTitle>
                  <CardDescription>{section.description}</CardDescription>
                </div>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
