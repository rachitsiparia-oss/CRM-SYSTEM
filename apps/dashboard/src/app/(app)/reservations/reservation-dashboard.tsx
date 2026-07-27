"use client";

import { useRouter } from "next/navigation";
import {
  CalendarCheck,
  CalendarClock,
  CalendarX2,
  UserX,
  Footprints,
  Users,
  Timer,
  TrendingUp,
} from "lucide-react";

import { useReservationDashboardStats } from "@/lib/hooks/use-reservations";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { SectionCard } from "@/components/section-card";
import { ErrorState } from "@/components/error-state";
import { Button } from "@/components/ui/button";

function today(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date());
}

export function ReservationDashboard() {
  const router = useRouter();
  const targetDate = today();
  const { data: stats, isLoading, isError, refetch } = useReservationDashboardStats(targetDate);

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Reservation dashboard"
        description="Today's bookings, occupancy, and conversion across every dining area."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => router.push("/reservations/list")}>
              <CalendarCheck className="size-4" />
              All reservations
            </Button>
            <Button variant="outline" onClick={() => router.push("/reservations/waitlist")}>
              <Footprints className="size-4" />
              Waitlist
            </Button>
          </div>
        }
      />

      {isError ? (
        <ErrorState
          title="Could not load dashboard stats"
          description="Reservation statistics could not be loaded right now."
          onRetry={() => void refetch()}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Today's reservations"
              value={stats?.total_count ?? 0}
              icon={CalendarCheck}
              loading={isLoading}
            />
            <StatCard
              label="Upcoming today"
              value={stats?.upcoming_count ?? 0}
              icon={CalendarClock}
              loading={isLoading}
            />
            <StatCard
              label="Completed"
              value={stats?.completed_count ?? 0}
              icon={Users}
              loading={isLoading}
            />
            <StatCard
              label="Walk-ins"
              value={stats?.walk_in_count ?? 0}
              icon={Footprints}
              loading={isLoading}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Cancelled"
              value={stats?.cancelled_count ?? 0}
              icon={CalendarX2}
              loading={isLoading}
            />
            <StatCard
              label="No-shows"
              value={stats?.no_show_count ?? 0}
              icon={UserX}
              loading={isLoading}
            />
            <StatCard
              label="Avg. party size"
              value={stats?.average_party_size ? stats.average_party_size.toFixed(1) : "—"}
              icon={Users}
              loading={isLoading}
            />
            <StatCard
              label="Conversion rate"
              value={
                stats?.conversion_rate !== null && stats?.conversion_rate !== undefined
                  ? `${Math.round(stats.conversion_rate * 100)}%`
                  : "—"
              }
              icon={TrendingUp}
              loading={isLoading}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SectionCard
              title="Average dining duration"
              description="Across today's completed reservations."
            >
              <div className="flex items-center gap-3">
                <Timer className="text-muted-foreground size-5" />
                <span className="text-xl font-semibold">
                  {stats?.average_dining_duration_minutes
                    ? `${Math.round(stats.average_dining_duration_minutes)} min`
                    : "—"}
                </span>
              </div>
            </SectionCard>
            <SectionCard title="Floor & tables" description="Live table status and floor layout.">
              <Button
                variant="ghost"
                size="sm"
                className="h-auto p-0 text-sm underline underline-offset-2"
                onClick={() => router.push("/reservations/tables")}
              >
                View tables & floor
              </Button>
            </SectionCard>
          </div>
        </>
      )}
    </div>
  );
}
