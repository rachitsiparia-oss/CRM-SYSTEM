"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import type { Coupon, OfferStatus } from "@rkpr/contracts";
import { Plus } from "lucide-react";

import {
  useConfirmRedemption,
  useOfferCoupons,
  useOfferDetail,
  useRedemptionDetail,
  useRejectRedemption,
  useReverseRedemption,
  useTransitionOffer,
} from "@/lib/hooks/use-offers";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import {
  OFFER_REDEMPTION_STATUS_TONES,
  OFFER_STATUS_TONES,
  formatDateTime,
  formatMinorUnits,
  humanize,
} from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/data-table/data-table";
import { SectionCard } from "@/components/section-card";
import { ErrorState } from "@/components/error-state";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CreateCouponModal } from "./create-coupon-modal";

const OFFER_TRANSITIONS: Record<OfferStatus, OfferStatus[]> = {
  draft: ["in_review", "cancelled"],
  in_review: ["approved", "draft", "cancelled"],
  approved: ["active", "cancelled"],
  active: ["paused", "expired", "cancelled", "archived"],
  paused: ["active", "cancelled", "archived"],
  expired: ["archived"],
  cancelled: ["archived"],
  archived: [],
};

export function OfferDetail({ offerId }: { offerId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: offer, isLoading, isError, refetch } = useOfferDetail(offerId);
  const { data: coupons, isLoading: couponsLoading } = useOfferCoupons(offerId);

  const transitionOffer = useTransitionOffer(offerId);

  const [error, setError] = useState<string | null>(null);
  const [showCreateCoupon, setShowCreateCoupon] = useState(false);
  const [lookupId, setLookupId] = useState("");
  const [activeLookupId, setActiveLookupId] = useState<string | undefined>(undefined);

  const canManage = hasPermission(currentUser, "offers.manage");
  const canApprove = hasPermission(currentUser, "offers.approve");
  const canRedeem = hasPermission(currentUser, "offers.redeem");
  const canReverse = hasPermission(currentUser, "offers.reverse");

  const { data: redemption, isLoading: redemptionLoading } = useRedemptionDetail(activeLookupId);
  const confirmRedemption = useConfirmRedemption(activeLookupId ?? "");
  const rejectRedemption = useRejectRedemption(activeLookupId ?? "");
  const reverseRedemption = useReverseRedemption(activeLookupId ?? "");

  const couponColumns = useMemo<ColumnDef<Coupon, unknown>[]>(
    () => [
      {
        id: "code",
        header: "Code",
        enableSorting: false,
        cell: ({ row }) => <span className="font-mono text-sm font-medium">{row.original.code}</span>,
      },
      {
        id: "reusable",
        header: "Reusable",
        enableSorting: false,
        cell: ({ row }) => (
          <Badge variant={row.original.is_reusable ? "secondary" : "outline"}>
            {row.original.is_reusable ? "Reusable" : "Single customer"}
          </Badge>
        ),
      },
      {
        id: "usage",
        header: "Redemptions",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">
            {row.original.redemption_count}
            {row.original.redemption_limit ? ` / ${row.original.redemption_limit}` : ""}
          </span>
        ),
      },
      {
        id: "expires_at",
        header: "Expires",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{formatDateTime(row.original.expires_at)}</span>,
      },
      {
        id: "active",
        header: "Active",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={row.original.is_active ? "Active" : "Inactive"}
            tone={row.original.is_active ? "success" : "neutral"}
          />
        ),
      },
    ],
    [],
  );

  if (isLoading) return <div className="p-6 text-sm text-zinc-500">Loading…</div>;
  if (isError || !offer) {
    return (
      <div className="p-6">
        <ErrorState title="Could not load this offer" onRetry={() => void refetch()} />
      </div>
    );
  }

  const availableTransitions = OFFER_TRANSITIONS[offer.status];

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link href="/marketing/offers" className="text-sm text-zinc-500 hover:underline">
          ← Offers & Coupons
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="text-lg font-semibold">{offer.internal_name}</h1>
          <StatusBadge label={humanize(offer.status)} tone={OFFER_STATUS_TONES[offer.status]} />
        </div>
        <p className="text-muted-foreground text-sm">
          {offer.offer_code} · {humanize(offer.offer_type)} · v{offer.latest_version_number}
        </p>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex flex-wrap gap-2">
        {availableTransitions.map((target) => {
          // Every transition requires offers.manage (the endpoint's base
          // permission dependency); target === "approved" additionally
          // requires offers.approve on top of that — see
          // apps/api/app/offers/router.py's transition_offer.
          const requiresApprove = target === "approved";
          const allowed = canManage && (!requiresApprove || canApprove);
          if (!allowed) return null;
          return (
            <Button
              key={target}
              size="sm"
              variant={target === "cancelled" || target === "archived" ? "outline" : "default"}
              disabled={transitionOffer.isPending}
              onClick={() =>
                transitionOffer.mutate(target, {
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "That action could not be completed."),
                })
              }
            >
              {target === "approved" ? "Approve" : `Move to ${humanize(target)}`}
            </Button>
          );
        })}
      </div>

      <SectionCard title="Configuration" description={offer.terms_and_notes ?? undefined}>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div>
            <p className="text-muted-foreground text-xs">Requires code</p>
            <p className="text-sm font-medium">{offer.requires_code ? "Yes" : "No"}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Exclusive</p>
            <p className="text-sm font-medium">{offer.is_exclusive ? "Yes" : "No"}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Budget cap</p>
            <p className="text-sm font-medium">
              {offer.budget_cap_minor != null ? formatMinorUnits(offer.budget_cap_minor) : "None"}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Redemption cap</p>
            <p className="text-sm font-medium">{offer.redemption_cap ?? "Unlimited"}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Redemptions so far</p>
            <p className="text-sm font-medium">{offer.redemption_count}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Requires approval</p>
            <p className="text-sm font-medium">{offer.requires_approval ? "Yes" : "No"}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Approved at</p>
            <p className="text-sm font-medium">{formatDateTime(offer.approved_at)}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Stackability group</p>
            <p className="text-sm font-medium">{offer.stackability_group ?? "None"}</p>
          </div>
        </div>
      </SectionCard>

      <Tabs defaultValue="coupons">
        <TabsList>
          <TabsTrigger value="coupons">Coupons</TabsTrigger>
          {(canRedeem || canReverse) && <TabsTrigger value="redemptions">Redemption lookup</TabsTrigger>}
        </TabsList>

        <TabsContent value="coupons">
          <SectionCard
            title="Coupons"
            description="Codes customers can enter to redeem this offer."
            actions={
              canManage ? (
                <Button size="sm" onClick={() => setShowCreateCoupon(true)}>
                  <Plus className="size-4" />
                  New coupon
                </Button>
              ) : undefined
            }
          >
            <DataTable
              columns={couponColumns}
              data={coupons ?? []}
              getRowId={(row) => row.id}
              loading={couponsLoading}
              emptyTitle="No coupons yet"
              emptyDescription="Create a coupon code for customers to redeem this offer."
            />
          </SectionCard>
        </TabsContent>

        {(canRedeem || canReverse) && (
          <TabsContent value="redemptions">
            <SectionCard
              title="Redemption lookup"
              description="Look up a redemption by ID to confirm, reject, or reverse it."
            >
              <div className="flex flex-col gap-4">
                <div className="flex items-center gap-2">
                  <Input
                    className="max-w-sm"
                    placeholder="Redemption ID"
                    value={lookupId}
                    onChange={(e) => setLookupId(e.target.value)}
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={!lookupId.trim()}
                    onClick={() => setActiveLookupId(lookupId.trim())}
                  >
                    Look up
                  </Button>
                </div>

                {activeLookupId && redemptionLoading && (
                  <p className="text-muted-foreground text-sm">Loading…</p>
                )}
                {activeLookupId && !redemptionLoading && !redemption && (
                  <p className="text-sm text-red-600">Redemption not found.</p>
                )}
                {redemption && (
                  <div className="flex flex-col gap-3 rounded-md border p-3">
                    <div className="flex flex-wrap items-center gap-3">
                      <StatusBadge
                        label={humanize(redemption.status)}
                        tone={OFFER_REDEMPTION_STATUS_TONES[redemption.status]}
                      />
                      <span className="text-sm">
                        Discount {formatMinorUnits(redemption.discount_amount_minor)}
                      </span>
                      <span className="text-muted-foreground text-xs">
                        Created {formatDateTime(redemption.created_at)}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {canRedeem && redemption.status === "reserved" && redemption.order_id && (
                        <Button
                          size="sm"
                          disabled={confirmRedemption.isPending}
                          onClick={() =>
                            confirmRedemption.mutate(redemption.order_id as string, {
                              onError: (err) =>
                                setError(err instanceof ApiError ? err.message : "Could not confirm."),
                            })
                          }
                        >
                          Confirm
                        </Button>
                      )}
                      {canRedeem && redemption.status === "reserved" && (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={rejectRedemption.isPending}
                          onClick={() =>
                            rejectRedemption.mutate("Rejected by staff", {
                              onError: (err) =>
                                setError(err instanceof ApiError ? err.message : "Could not reject."),
                            })
                          }
                        >
                          Reject
                        </Button>
                      )}
                      {canReverse && redemption.status === "confirmed" && (
                        <Button
                          size="sm"
                          variant="destructive"
                          disabled={reverseRedemption.isPending}
                          onClick={() =>
                            reverseRedemption.mutate("Reversed by staff", {
                              onError: (err) =>
                                setError(err instanceof ApiError ? err.message : "Could not reverse."),
                            })
                          }
                        >
                          Reverse
                        </Button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </SectionCard>
          </TabsContent>
        )}
      </Tabs>

      <CreateCouponModal offerId={offerId} open={showCreateCoupon} onOpenChange={setShowCreateCoupon} />
    </div>
  );
}
