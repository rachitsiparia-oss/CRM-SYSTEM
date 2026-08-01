"use client";

import Link from "next/link";
import {
  Award,
  Gift,
  HeartHandshake,
  Megaphone,
  MessageCircleWarning,
  ShieldAlert,
  Sparkles,
  Star,
  Target,
  Ticket,
  Users,
  Wallet,
} from "lucide-react";

import { useLoyaltyAnalytics } from "@/lib/hooks/use-loyalty";
import { useGiftCardAnalytics } from "@/lib/hooks/use-gift-cards";
import { useCustomerCreditAnalytics } from "@/lib/hooks/use-customer-credit";
import { useComplaintAnalytics } from "@/lib/hooks/use-complaints";
import { formatMinorUnits } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

const SECTIONS = [
  {
    href: "/marketing/loyalty",
    icon: Award,
    title: "Loyalty",
    description: "Programs, tiers, accounts, and the points ledger.",
  },
  {
    href: "/marketing/segments",
    icon: Target,
    title: "Segments",
    description: "Dynamic and static customer segments for targeting.",
  },
  {
    href: "/marketing/offers",
    icon: Ticket,
    title: "Offers & Coupons",
    description: "Discount offers, coupons, and redemption tracking.",
  },
  {
    href: "/marketing/campaigns",
    icon: Megaphone,
    title: "Campaigns",
    description: "Segment-targeted WhatsApp, email, and SMS campaigns.",
  },
  {
    href: "/marketing/referrals",
    icon: Users,
    title: "Referrals",
    description: "Referral programs, codes, and reward relationships.",
  },
  {
    href: "/marketing/achievements",
    icon: Sparkles,
    title: "Achievements",
    description: "Rule-based customer achievements and rewards.",
  },
  {
    href: "/marketing/gift-cards",
    icon: Gift,
    title: "Gift Cards",
    description: "Issue, redeem, and track gift card balances.",
  },
  {
    href: "/marketing/customer-credit",
    icon: Wallet,
    title: "Customer Credit",
    description: "Internal store-credit accounts and ledger.",
  },
  {
    href: "/marketing/commercial-risk",
    icon: ShieldAlert,
    title: "Commercial Risk",
    description: "Review queue for anomalous commercial activity.",
  },
  {
    href: "/marketing/feedback",
    icon: Star,
    title: "Feedback",
    description: "Feedback entries, ratings, and post-visit review requests.",
  },
  {
    href: "/marketing/complaints",
    icon: MessageCircleWarning,
    title: "Complaints",
    description: "Complaint case management, SLA tracking, and escalation.",
  },
  {
    href: "/marketing/service-recovery",
    icon: HeartHandshake,
    title: "Service Recovery",
    description: "Recovery actions, compensation, and approval rules.",
  },
];

export function MarketingDashboard() {
  const { data: loyalty, isLoading: loyaltyLoading } = useLoyaltyAnalytics();
  const { data: giftCards, isLoading: giftCardsLoading } = useGiftCardAnalytics();
  const { data: credit, isLoading: creditLoading } = useCustomerCreditAnalytics();
  const { data: complaints, isLoading: complaintsLoading } = useComplaintAnalytics();

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Marketing, Loyalty & Feedback"
        description="Loyalty, segments, offers, campaigns, referrals, achievements, gift cards, customer credit, commercial risk, feedback, complaints, and service recovery."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Active loyalty members"
          value={loyalty?.active_members ?? 0}
          icon={Award}
          loading={loyaltyLoading}
        />
        <StatCard
          label="Outstanding gift card liability"
          value={formatMinorUnits(giftCards?.outstanding_liability_minor)}
          icon={Gift}
          loading={giftCardsLoading}
        />
        <StatCard
          label="Outstanding customer credit"
          value={formatMinorUnits(credit?.outstanding_liability_minor)}
          icon={Wallet}
          loading={creditLoading}
        />
        <StatCard
          label="Open complaints"
          value={complaints?.open_count ?? 0}
          icon={MessageCircleWarning}
          loading={complaintsLoading}
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
