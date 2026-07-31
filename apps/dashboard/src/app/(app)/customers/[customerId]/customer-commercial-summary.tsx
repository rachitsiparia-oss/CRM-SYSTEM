"use client";

import Link from "next/link";

import { useLoyaltyAccountForCustomer, useLoyaltyTiers } from "@/lib/hooks/use-loyalty";
import { useGiftCardList } from "@/lib/hooks/use-gift-cards";
import { useCustomerCreditAccount } from "@/lib/hooks/use-customer-credit";
import { useCommercialRiskFlagList } from "@/lib/hooks/use-commercial-risk";
import {
  COMMERCIAL_RISK_FLAG_STATUS_TONES,
  formatMinorUnits,
  GIFT_CARD_STATUS_TONES,
  humanize,
  LOYALTY_ACCOUNT_STATUS_TONES,
} from "@/lib/crm-display";
import { SectionCard } from "@/components/section-card";
import { StatCard } from "@/components/stat-card";
import { StatusBadge } from "@/components/status-badge";

const PAGE_SIZE = 5;

export function CustomerCommercialSummary({ customerId }: { customerId: string }) {
  const { data: loyaltyAccount, isLoading: loyaltyLoading } =
    useLoyaltyAccountForCustomer(customerId);
  const { data: tiers } = useLoyaltyTiers(loyaltyAccount?.program_id);
  const { data: giftCards, isLoading: giftCardsLoading } = useGiftCardList({
    page: 1,
    pageSize: PAGE_SIZE,
    customerId,
  });
  const { data: creditAccount, isLoading: creditLoading } = useCustomerCreditAccount(customerId);
  const { data: riskFlags, isLoading: riskLoading } = useCommercialRiskFlagList({
    page: 1,
    pageSize: PAGE_SIZE,
    customerId,
  });

  const currentTier = tiers?.find((tier) => tier.id === loyaltyAccount?.current_tier_id);
  const openRiskFlags = riskFlags?.data.filter((flag) => flag.status === "open").length ?? 0;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Loyalty points"
          value={loyaltyAccount ? String(loyaltyAccount.points_balance) : "—"}
          loading={loyaltyLoading}
        />
        <StatCard
          label="Gift cards"
          value={giftCards ? String(giftCards.pagination.total) : "—"}
          loading={giftCardsLoading}
        />
        <StatCard
          label="Customer credit balance"
          value={formatMinorUnits(creditAccount?.current_balance_minor)}
          loading={creditLoading}
        />
        <StatCard
          label="Open risk flags"
          value={String(openRiskFlags)}
          loading={riskLoading}
        />
      </div>

      <SectionCard
        title="Loyalty"
        description="Points balance, tier, and account status."
        actions={
          <Link
            href="/marketing/loyalty/accounts"
            className="text-muted-foreground text-sm hover:underline"
          >
            Open loyalty
          </Link>
        }
      >
        {loyaltyAccount ? (
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <dt className="text-muted-foreground text-xs">Status</dt>
              <dd className="text-sm">
                <StatusBadge
                  label={humanize(loyaltyAccount.status)}
                  tone={LOYALTY_ACCOUNT_STATUS_TONES[loyaltyAccount.status]}
                />
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground text-xs">Current tier</dt>
              <dd className="text-sm">{currentTier?.name ?? "Unassigned"}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground text-xs">Lifetime points earned</dt>
              <dd className="text-sm">{loyaltyAccount.lifetime_points_earned}</dd>
            </div>
          </dl>
        ) : (
          <p className="text-muted-foreground text-sm">Not enrolled in a loyalty program.</p>
        )}
      </SectionCard>

      <SectionCard
        title="Gift cards"
        description="Gift cards purchased by or issued to this customer."
        actions={
          <Link
            href="/marketing/gift-cards"
            className="text-muted-foreground text-sm hover:underline"
          >
            Open gift cards
          </Link>
        }
      >
        {giftCards && giftCards.data.length > 0 ? (
          <ul className="flex flex-col gap-2 text-sm">
            {giftCards.data.map((card) => (
              <li key={card.id} className="flex items-center justify-between gap-2">
                <Link href={`/marketing/gift-cards/${card.id}`} className="hover:underline">
                  {card.masked_display}
                </Link>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">
                    {formatMinorUnits(card.current_balance_minor)}
                  </span>
                  <StatusBadge
                    label={humanize(card.status)}
                    tone={GIFT_CARD_STATUS_TONES[card.status]}
                  />
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted-foreground text-sm">No gift cards on file.</p>
        )}
      </SectionCard>

      <SectionCard
        title="Commercial risk"
        description="Flags raised against this customer's account activity."
        actions={
          <Link
            href="/marketing/commercial-risk"
            className="text-muted-foreground text-sm hover:underline"
          >
            Open risk queue
          </Link>
        }
      >
        {riskFlags && riskFlags.data.length > 0 ? (
          <ul className="flex flex-col gap-2 text-sm">
            {riskFlags.data.map((flag) => (
              <li key={flag.id} className="flex items-center justify-between gap-2">
                <span className="truncate">{humanize(flag.flag_type)}</span>
                <StatusBadge
                  label={humanize(flag.status)}
                  tone={COMMERCIAL_RISK_FLAG_STATUS_TONES[flag.status]}
                />
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted-foreground text-sm">No risk flags on file.</p>
        )}
      </SectionCard>
    </div>
  );
}
