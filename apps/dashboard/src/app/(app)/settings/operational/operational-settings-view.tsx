"use client";

import { useState } from "react";
import type { OperationalSettings } from "@rkpr/contracts";

import {
  useOperationalSettings,
  useUpdateOperationalSettings,
} from "@/lib/hooks/use-operational-settings";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { ErrorState } from "@/components/error-state";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";

export function OperationalSettingsView() {
  const { data: currentUser } = useCurrentUser();
  const canManage = hasPermission(currentUser, "settings.manage");
  const { data: settings, isLoading, isError, refetch } = useOperationalSettings();

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Operational Settings"
        description="Tunable knobs for the job/scheduler infrastructure — never a business-rule or permission override."
      />

      {isError ? (
        <ErrorState title="Could not load operational settings" onRetry={() => void refetch()} />
      ) : isLoading || !settings ? (
        <Skeleton className="h-96 w-full" />
      ) : (
        // Keyed by `version` so a change saved elsewhere (or a refetch after
        // this form's own save) remounts the form with fresh initial state,
        // without an effect re-syncing local state on every render.
        <OperationalSettingsForm key={settings.version} settings={settings} canManage={canManage} />
      )}
    </div>
  );
}

function OperationalSettingsForm({
  settings,
  canManage,
}: {
  settings: OperationalSettings;
  canManage: boolean;
}) {
  const updateSettings = useUpdateOperationalSettings();
  const [maintenanceModeEnabled, setMaintenanceModeEnabled] = useState(
    settings.maintenance_mode_enabled,
  );
  const [maintenanceMessage, setMaintenanceMessage] = useState(settings.maintenance_message ?? "");
  const [defaultMaxAttempts, setDefaultMaxAttempts] = useState(
    String(settings.default_max_attempts),
  );
  const [retryBackoffSeconds, setRetryBackoffSeconds] = useState(
    String(settings.default_retry_backoff_seconds),
  );
  const [retryBackoffCapSeconds, setRetryBackoffCapSeconds] = useState(
    String(settings.default_retry_backoff_cap_seconds),
  );
  const [workerMaxJobs, setWorkerMaxJobs] = useState(String(settings.worker_max_jobs));
  const [workerJobTimeoutSeconds, setWorkerJobTimeoutSeconds] = useState(
    String(settings.worker_job_timeout_seconds),
  );
  const [error, setError] = useState<string | null>(null);

  return (
    <>
      {error && (
        <p role="alert" className="text-destructive text-sm">
          {error}
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Maintenance mode</CardTitle>
          <CardDescription>
            Shown to staff when the system is temporarily unavailable for maintenance.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <Label htmlFor="maintenance-toggle">Maintenance mode enabled</Label>
            <Switch
              id="maintenance-toggle"
              checked={maintenanceModeEnabled}
              disabled={!canManage}
              onCheckedChange={setMaintenanceModeEnabled}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="maintenance-message">Maintenance message</Label>
            <Textarea
              id="maintenance-message"
              value={maintenanceMessage}
              disabled={!canManage}
              onChange={(e) => setMaintenanceMessage(e.target.value)}
              rows={2}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Retry and worker defaults</CardTitle>
          <CardDescription>
            Defaults a job uses when it doesn&apos;t specify its own retry/timeout policy.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="default-max-attempts">Default max attempts</Label>
            <Input
              id="default-max-attempts"
              type="number"
              min={1}
              value={defaultMaxAttempts}
              disabled={!canManage}
              onChange={(e) => setDefaultMaxAttempts(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="retry-backoff-seconds">Retry backoff base (seconds)</Label>
            <Input
              id="retry-backoff-seconds"
              type="number"
              min={1}
              value={retryBackoffSeconds}
              disabled={!canManage}
              onChange={(e) => setRetryBackoffSeconds(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="retry-backoff-cap-seconds">Retry backoff cap (seconds)</Label>
            <Input
              id="retry-backoff-cap-seconds"
              type="number"
              min={1}
              value={retryBackoffCapSeconds}
              disabled={!canManage}
              onChange={(e) => setRetryBackoffCapSeconds(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="worker-max-jobs">Worker max concurrent jobs</Label>
            <Input
              id="worker-max-jobs"
              type="number"
              min={1}
              value={workerMaxJobs}
              disabled={!canManage}
              onChange={(e) => setWorkerMaxJobs(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="worker-job-timeout-seconds">Worker job timeout (seconds)</Label>
            <Input
              id="worker-job-timeout-seconds"
              type="number"
              min={1}
              value={workerJobTimeoutSeconds}
              disabled={!canManage}
              onChange={(e) => setWorkerJobTimeoutSeconds(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {canManage && (
        <div>
          <Button
            disabled={updateSettings.isPending}
            onClick={() => {
              setError(null);
              updateSettings.mutate(
                {
                  maintenance_mode_enabled: maintenanceModeEnabled,
                  maintenance_message: maintenanceMessage.trim() || null,
                  default_max_attempts: Number(defaultMaxAttempts),
                  default_retry_backoff_seconds: Number(retryBackoffSeconds),
                  default_retry_backoff_cap_seconds: Number(retryBackoffCapSeconds),
                  worker_max_jobs: Number(workerMaxJobs),
                  worker_job_timeout_seconds: Number(workerJobTimeoutSeconds),
                },
                {
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not save these settings."),
                },
              );
            }}
          >
            {updateSettings.isPending ? "Saving…" : "Save changes"}
          </Button>
        </div>
      )}
    </>
  );
}
