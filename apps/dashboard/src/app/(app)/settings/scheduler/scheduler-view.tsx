"use client";

import { useSchedulerStatus, useSetSchedulerEnabled } from "@/lib/hooks/use-scheduler";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { PageHeader } from "@/components/page-header";
import { ErrorState } from "@/components/error-state";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
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

export function SchedulerView() {
  const { data: currentUser } = useCurrentUser();
  const canManage = hasPermission(currentUser, "scheduler.manage");
  const { data, isLoading, isError, refetch } = useSchedulerStatus();
  const setEnabled = useSetSchedulerEnabled();

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Scheduler"
        description="Every cron entry registered in the apps/worker ARQ scheduler, and the global enable/disable switch."
      />

      {isError ? (
        <ErrorState title="Could not load scheduler status" onRetry={() => void refetch()} />
      ) : (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Scheduler enabled</CardTitle>
              <CardDescription>
                When disabled, apps/worker still runs but every scheduled job checks this flag
                and skips its tick — it does not stop the worker process itself.
              </CardDescription>
            </div>
            {isLoading ? (
              <Skeleton className="h-6 w-11" />
            ) : (
              <Switch
                checked={data?.scheduler_enabled ?? false}
                disabled={!canManage || setEnabled.isPending}
                onCheckedChange={(checked) => setEnabled.mutate(checked)}
              />
            )}
          </CardHeader>
        </Card>
      )}

      <div>
        <h2 className="mb-2 text-sm font-medium">Cron catalog</h2>
        {isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : (
          <div className="overflow-hidden rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Job type</TableHead>
                  <TableHead>Queue</TableHead>
                  <TableHead>Cadence</TableHead>
                  <TableHead>Description</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(data?.jobs ?? []).map((entry) => (
                  <TableRow key={entry.job_type}>
                    <TableCell className="font-mono text-xs">{entry.job_type}</TableCell>
                    <TableCell className="text-sm">{entry.queue_name}</TableCell>
                    <TableCell className="text-sm">{entry.cadence}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {entry.description}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </div>
  );
}
