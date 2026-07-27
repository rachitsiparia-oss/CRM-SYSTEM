"use client";

import { useRouter } from "next/navigation";
import {
  Boxes,
  IndianRupee,
  AlertTriangle,
  OctagonAlert,
  PackageX,
  CalendarClock,
  CalendarX2,
  Trash2,
  Truck,
  ArrowRightLeft,
  ClipboardList,
} from "lucide-react";

import { useInventoryDashboardStats } from "@/lib/hooks/use-inventory-items";
import { formatMinorUnits } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { SectionCard } from "@/components/section-card";
import { ErrorState } from "@/components/error-state";
import { Button } from "@/components/ui/button";

export function InventoryDashboard() {
  const router = useRouter();
  const { data: stats, isLoading, isError, refetch } = useInventoryDashboardStats();

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Inventory dashboard"
        description="Stock health, value, and operational activity across every location."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => router.push("/inventory/items")}>
              <Boxes className="size-4" />
              All items
            </Button>
            <Button variant="outline" onClick={() => router.push("/inventory/movements")}>
              <ClipboardList className="size-4" />
              Movement ledger
            </Button>
          </div>
        }
      />

      {isError ? (
        <ErrorState
          title="Could not load dashboard stats"
          description="Inventory statistics could not be loaded right now."
          onRetry={() => void refetch()}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Active items"
              value={stats?.total_active_items ?? 0}
              icon={Boxes}
              loading={isLoading}
            />
            <StatCard
              label="Total stock value"
              value={formatMinorUnits(stats?.total_stock_value_minor ?? 0)}
              icon={IndianRupee}
              loading={isLoading}
            />
            <StatCard
              label="Low stock"
              value={stats?.low_stock_count ?? 0}
              icon={AlertTriangle}
              loading={isLoading}
            />
            <StatCard
              label="Critical stock"
              value={stats?.critical_stock_count ?? 0}
              icon={OctagonAlert}
              loading={isLoading}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Out of stock"
              value={stats?.out_of_stock_count ?? 0}
              icon={PackageX}
              loading={isLoading}
            />
            <StatCard
              label="Expiring within 7 days"
              value={stats?.expiring_batches_7d ?? 0}
              icon={CalendarClock}
              loading={isLoading}
            />
            <StatCard
              label="Expired batches"
              value={stats?.expired_batches ?? 0}
              icon={CalendarX2}
              loading={isLoading}
            />
            <StatCard
              label="Wastage value today"
              value={formatMinorUnits(stats?.wastage_today_value_minor ?? 0)}
              icon={Trash2}
              loading={isLoading}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <SectionCard title="Receipts today">
              <div className="flex items-center gap-3">
                <Truck className="text-muted-foreground size-5" />
                <span className="text-xl font-semibold">{stats?.receipts_today_count ?? 0}</span>
                <span className="text-muted-foreground text-sm">posted</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-auto p-0 text-sm underline underline-offset-2"
                onClick={() => router.push("/inventory/receipts")}
              >
                View receipts
              </Button>
            </SectionCard>
            <SectionCard title="Transfers in progress">
              <div className="flex items-center gap-3">
                <ArrowRightLeft className="text-muted-foreground size-5" />
                <span className="text-xl font-semibold">{stats?.transfers_in_progress ?? 0}</span>
                <span className="text-muted-foreground text-sm">draft</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-auto p-0 text-sm underline underline-offset-2"
                onClick={() => router.push("/inventory/transfers")}
              >
                View transfers
              </Button>
            </SectionCard>
            <SectionCard title="Pending stock counts">
              <div className="flex items-center gap-3">
                <ClipboardList className="text-muted-foreground size-5" />
                <span className="text-xl font-semibold">{stats?.pending_stock_counts ?? 0}</span>
                <span className="text-muted-foreground text-sm">open sessions</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-auto p-0 text-sm underline underline-offset-2"
                onClick={() => router.push("/inventory/stock-counts")}
              >
                View stock counts
              </Button>
            </SectionCard>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SectionCard
              title="Low & critical stock"
              description="Items at or below their reorder level."
            >
              <Button
                variant="outline"
                onClick={() => router.push("/inventory/items?low_stock=true")}
              >
                View {stats?.low_stock_count ?? 0} low-stock items
              </Button>
            </SectionCard>
            <SectionCard title="Out of stock" description="Items with zero available quantity.">
              <Button
                variant="outline"
                onClick={() => router.push("/inventory/items?out_of_stock=true")}
              >
                View {stats?.out_of_stock_count ?? 0} out-of-stock items
              </Button>
            </SectionCard>
          </div>
        </>
      )}
    </div>
  );
}
