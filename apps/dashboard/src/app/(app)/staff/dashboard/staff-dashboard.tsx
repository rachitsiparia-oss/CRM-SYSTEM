"use client";

import {
  Users,
  UserPlus,
  FileWarning,
  BadgeAlert,
  CalendarClock,
  CalendarCheck,
  AlertTriangle,
  Clock3,
  GraduationCap,
  ClipboardCheck,
  ArrowLeftRight,
} from "lucide-react";

import { useStaffAnalytics } from "@/lib/hooks/use-staff-operations";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { ErrorState } from "@/components/error-state";

export function StaffDashboard() {
  const { data: stats, isLoading, isError, refetch } = useStaffAnalytics();

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Staff dashboard"
        description="Headcount, roster health, and operational readiness across departments."
      />

      {isError ? (
        <ErrorState title="Could not load staff analytics" onRetry={() => void refetch()} />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Active staff" value={stats?.active_staff ?? 0} icon={Users} loading={isLoading} />
          <StatCard
            label="Onboarding in progress"
            value={stats?.onboarding_in_progress ?? 0}
            icon={UserPlus}
            loading={isLoading}
          />
          <StatCard
            label="Documents expiring (30d)"
            value={stats?.documents_expiring_30d ?? 0}
            icon={FileWarning}
            loading={isLoading}
          />
          <StatCard
            label="Certifications expiring (30d)"
            value={stats?.certifications_expiring_30d ?? 0}
            icon={BadgeAlert}
            loading={isLoading}
          />
          <StatCard
            label="On leave today"
            value={stats?.on_leave_today ?? 0}
            icon={CalendarClock}
            loading={isLoading}
          />
          <StatCard
            label="Scheduled today"
            value={stats?.scheduled_today ?? 0}
            icon={CalendarCheck}
            loading={isLoading}
          />
          <StatCard
            label="Attendance exceptions today"
            value={stats?.attendance_exceptions_today ?? 0}
            icon={AlertTriangle}
            loading={isLoading}
          />
          <StatCard
            label="Late arrivals today"
            value={stats?.late_arrivals_today ?? 0}
            icon={Clock3}
            loading={isLoading}
          />
          <StatCard
            label="Training overdue"
            value={stats?.training_overdue ?? 0}
            icon={GraduationCap}
            loading={isLoading}
          />
          <StatCard
            label="Reviews due"
            value={stats?.reviews_due ?? 0}
            icon={ClipboardCheck}
            loading={isLoading}
          />
          <StatCard
            label="Open shift-change requests"
            value={stats?.open_shift_change_requests ?? 0}
            icon={ArrowLeftRight}
            loading={isLoading}
          />
          <StatCard
            label="Mandatory training completion"
            value={`${stats?.mandatory_training_completion_pct ?? 0}%`}
            icon={GraduationCap}
            loading={isLoading}
          />
        </div>
      )}
    </div>
  );
}
