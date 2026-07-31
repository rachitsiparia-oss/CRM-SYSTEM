"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import type { ReferralProgramStatus } from "@rkpr/contracts";

import {
  useIssueReferralCode,
  useReferralPrograms,
  useTransitionReferralProgram,
} from "@/lib/hooks/use-referrals";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import {
  REFERRAL_PROGRAM_STATUS_TONES,
  formatDateTime,
  formatMinorUnits,
  humanize,
} from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { PageSkeleton } from "@/components/skeletons/page-skeleton";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
import { SectionCard } from "@/components/section-card";
import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const NEXT_STATUS: Record<ReferralProgramStatus, ReferralProgramStatus[]> = {
  draft: ["active", "archived"],
  active: ["paused", "archived"],
  paused: ["active", "archived"],
  archived: [],
};

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd className="text-sm">{value}</dd>
    </div>
  );
}

export function ProgramDetail({ programId }: { programId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: programs, isLoading, isError, refetch } = useReferralPrograms();
  const program = programs?.find((p) => p.id === programId);

  const transition = useTransitionReferralProgram(programId);
  const issueCode = useIssueReferralCode(programId);

  const [referrerCustomerId, setReferrerCustomerId] = useState("");
  const [issuedCode, setIssuedCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canManage = hasPermission(currentUser, "referrals.manage");
  const isMoney = program?.reward_ledger === "internal_credit";

  if (isLoading) {
    return (
      <div className="flex-1 p-6">
        <PageSkeleton />
      </div>
    );
  }

  if (isError || !program) {
    return (
      <div className="flex-1 p-6">
        <ErrorState
          variant="404"
          title="Referral program not found"
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link
          href="/marketing/referrals"
          className="text-muted-foreground inline-flex items-center gap-1 text-sm hover:underline"
        >
          <ArrowLeft className="size-3.5" />
          Referral programs
        </Link>
      </div>

      <PageHeader
        title={program.name}
        description={program.code}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge
              label={humanize(program.status)}
              tone={REFERRAL_PROGRAM_STATUS_TONES[program.status]}
            />
            {canManage &&
              NEXT_STATUS[program.status].map((target) => (
                <Button
                  key={target}
                  size="sm"
                  variant="outline"
                  disabled={transition.isPending}
                  onClick={() => {
                    setError(null);
                    transition.mutate(target, {
                      onError: (err) =>
                        setError(err instanceof ApiError ? err.message : "That action could not be completed."),
                    });
                  }}
                >
                  {target === "active" ? "Activate" : target === "paused" ? "Pause" : "Archive"}
                </Button>
              ))}
          </div>
        }
      />

      {error && (
        <p role="alert" className="text-destructive text-sm">
          {error}
        </p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Referrer reward"
          value={isMoney ? formatMinorUnits(program.referrer_reward_amount) : `${program.referrer_reward_amount} pts`}
        />
        <StatCard
          label="Referee reward"
          value={isMoney ? formatMinorUnits(program.referee_reward_amount) : `${program.referee_reward_amount} pts`}
        />
        <StatCard label="Reward hold days" value={program.reward_hold_days} />
        <StatCard label="Max active codes / referrer" value={program.max_active_codes_per_referrer} />
      </div>

      <SectionCard title="Configuration">
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Field label="Reward ledger" value={humanize(program.reward_ledger)} />
          <Field
            label="Qualifying order minimum"
            value={formatMinorUnits(program.qualifying_order_minimum_minor)}
          />
          <Field
            label="Max rewarded referrals / window"
            value={program.max_rewarded_referrals_per_window?.toString() ?? "Unlimited"}
          />
          <Field label="Window days" value={program.window_days?.toString() ?? "—"} />
          <Field label="Starts" value={formatDateTime(program.starts_at)} />
          <Field label="Ends" value={formatDateTime(program.ends_at)} />
          <Field label="Referrer eligibility" value={program.referrer_eligibility_note ?? "—"} />
          <Field label="Referee eligibility" value={program.referee_eligibility_note ?? "—"} />
          <Field label="Updated" value={formatDateTime(program.updated_at)} />
        </dl>
      </SectionCard>

      {canManage && (
        <SectionCard
          title="Issue a referral code"
          description="Issue a new code on behalf of a referring customer."
        >
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-end gap-3">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="referrer-customer-id">Referrer customer ID</Label>
                <Input
                  id="referrer-customer-id"
                  className="w-80"
                  value={referrerCustomerId}
                  onChange={(e) => setReferrerCustomerId(e.target.value)}
                  placeholder="Customer UUID"
                />
              </div>
              <Button
                disabled={!referrerCustomerId.trim() || issueCode.isPending}
                onClick={() => {
                  setError(null);
                  setIssuedCode(null);
                  issueCode.mutate(
                    { referrer_customer_id: referrerCustomerId.trim() },
                    {
                      onSuccess: (response) => {
                        setIssuedCode(response.data.code);
                        setReferrerCustomerId("");
                      },
                      onError: (err) =>
                        setError(err instanceof ApiError ? err.message : "Could not issue a code."),
                    },
                  );
                }}
              >
                {issueCode.isPending ? "Issuing…" : "Issue code"}
              </Button>
            </div>
            {issuedCode && (
              <p className="text-success text-sm">
                Code issued: <span className="font-mono font-semibold">{issuedCode}</span>
              </p>
            )}
          </div>
        </SectionCard>
      )}

      <div>
        <Link
          href={`/marketing/referrals/relationships?programId=${program.id}`}
          className="text-sm hover:underline"
        >
          View relationships for this program →
        </Link>
      </div>
    </div>
  );
}
