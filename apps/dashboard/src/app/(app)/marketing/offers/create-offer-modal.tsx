"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { BenefitRule, OfferType } from "@rkpr/contracts";

import { useCreateOffer } from "@/lib/hooks/use-offers";
import { ApiError } from "@/lib/api/errors";
import { humanize } from "@/lib/crm-display";
import {
  DEFAULT_RULE_CONDITION_DRAFT,
  RuleConditionInput,
  buildRuleCondition,
  type RuleConditionDraft,
} from "@/components/forms/rule-condition-input";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type BenefitKind = BenefitRule["kind"];

const OFFER_TYPES: OfferType[] = [
  "percentage_discount",
  "fixed_discount",
  "item_discount",
  "category_discount",
  "buy_x_get_y",
  "combo_price",
  "free_item",
  "delivery_fee_discount",
  "loyalty_bonus",
  "internal_credit",
  "service_recovery",
];

// Mirrors apps/api/app/offers/benefit.py's _ALLOWED_BENEFIT_KINDS — the
// backend is the authority; this only drives which benefit fields the
// create form shows so staff aren't offered a combination it will reject.
const ALLOWED_BENEFIT_KINDS: Record<OfferType, BenefitKind[]> = {
  percentage_discount: ["percentage"],
  fixed_discount: ["fixed_amount"],
  item_discount: ["percentage", "fixed_amount"],
  category_discount: ["percentage", "fixed_amount"],
  buy_x_get_y: ["buy_x_get_y"],
  combo_price: ["combo_price"],
  free_item: ["fixed_amount"],
  delivery_fee_discount: ["percentage", "fixed_amount"],
  loyalty_bonus: ["loyalty_bonus"],
  internal_credit: ["internal_credit"],
  service_recovery: ["percentage", "fixed_amount"],
};

function toMinorUnits(rupees: string): number {
  const parsed = Number(rupees);
  if (!Number.isFinite(parsed) || parsed < 0) return 0;
  return Math.round(parsed * 100);
}

function todayLocalDatetime(): string {
  const now = new Date();
  now.setSeconds(0, 0);
  const offset = now.getTimezoneOffset();
  const local = new Date(now.getTime() - offset * 60_000);
  return local.toISOString().slice(0, 16);
}

export function CreateOfferModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const createOffer = useCreateOffer();

  const [offerCode, setOfferCode] = useState("");
  const [internalName, setInternalName] = useState("");
  const [customerFacingName, setCustomerFacingName] = useState("");
  const [offerType, setOfferType] = useState<OfferType>("percentage_discount");
  const [requiresCode, setRequiresCode] = useState(false);
  const [validFrom, setValidFrom] = useState(todayLocalDatetime());

  const [benefitKind, setBenefitKind] = useState<BenefitKind>("percentage");
  const [percent, setPercent] = useState("10");
  const [amountRupees, setAmountRupees] = useState("50");
  const [buyQuantity, setBuyQuantity] = useState("2");
  const [getQuantity, setGetQuantity] = useState("1");
  const [getDiscountPercent, setGetDiscountPercent] = useState("100");
  const [comboPriceRupees, setComboPriceRupees] = useState("199");
  const [grantPoints, setGrantPoints] = useState("100");
  const [grantAmountRupees, setGrantAmountRupees] = useState("50");

  const [ruleDraft, setRuleDraft] = useState<RuleConditionDraft>(DEFAULT_RULE_CONDITION_DRAFT);
  const [error, setError] = useState<string | null>(null);

  const allowedKinds = ALLOWED_BENEFIT_KINDS[offerType];
  const effectiveKind = allowedKinds.includes(benefitKind) ? benefitKind : allowedKinds[0];

  function selectOfferType(next: OfferType) {
    setOfferType(next);
    const kinds = ALLOWED_BENEFIT_KINDS[next];
    if (!kinds.includes(benefitKind)) setBenefitKind(kinds[0]);
  }

  function reset() {
    setOfferCode("");
    setInternalName("");
    setCustomerFacingName("");
    setOfferType("percentage_discount");
    setRequiresCode(false);
    setValidFrom(todayLocalDatetime());
    setBenefitKind("percentage");
    setPercent("10");
    setAmountRupees("50");
    setBuyQuantity("2");
    setGetQuantity("1");
    setGetDiscountPercent("100");
    setComboPriceRupees("199");
    setGrantPoints("100");
    setGrantAmountRupees("50");
    setRuleDraft(DEFAULT_RULE_CONDITION_DRAFT);
    setError(null);
  }

  const benefitRule = useMemo<BenefitRule>(() => {
    switch (effectiveKind) {
      case "percentage":
        return { kind: "percentage", percent };
      case "fixed_amount":
        return { kind: "fixed_amount", amount_minor: toMinorUnits(amountRupees) };
      case "buy_x_get_y":
        return {
          kind: "buy_x_get_y",
          buy_quantity: Number(buyQuantity) || 0,
          get_quantity: Number(getQuantity) || 0,
          get_discount_percent: getDiscountPercent,
        };
      case "combo_price":
        return { kind: "combo_price", fixed_price_minor: toMinorUnits(comboPriceRupees) };
      case "loyalty_bonus":
        return { kind: "loyalty_bonus", grant_points: Number(grantPoints) || 0 };
      case "internal_credit":
        return { kind: "internal_credit", grant_amount_minor: toMinorUnits(grantAmountRupees) };
    }
  }, [
    effectiveKind,
    percent,
    amountRupees,
    buyQuantity,
    getQuantity,
    getDiscountPercent,
    comboPriceRupees,
    grantPoints,
    grantAmountRupees,
  ]);

  const isValid =
    offerCode.trim() && internalName.trim() && customerFacingName.trim() && validFrom.trim();

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="New offer"
      size="lg"
      description="Starts as a draft. Eligibility and benefit rules become the offer's first version."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!isValid || createOffer.isPending}
            onClick={() => {
              setError(null);
              createOffer.mutate(
                {
                  offer_code: offerCode.trim(),
                  internal_name: internalName.trim(),
                  customer_facing_name: customerFacingName.trim(),
                  offer_type: offerType,
                  requires_code: requiresCode,
                  initial_version: {
                    eligibility_rule: buildRuleCondition(ruleDraft),
                    benefit_rule: benefitRule,
                    valid_from: new Date(validFrom).toISOString(),
                  },
                },
                {
                  onSuccess: (response) => {
                    reset();
                    onOpenChange(false);
                    router.push(`/marketing/offers/${response.data.id}`);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not create the offer."),
                },
              );
            }}
          >
            Create draft
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="offer-code">Offer code</Label>
            <Input id="offer-code" value={offerCode} onChange={(e) => setOfferCode(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Offer type</Label>
            <Select value={offerType} onValueChange={(v) => selectOfferType(v as OfferType)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {OFFER_TYPES.map((type) => (
                  <SelectItem key={type} value={type}>
                    {humanize(type)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="offer-internal-name">Internal name</Label>
            <Input
              id="offer-internal-name"
              value={internalName}
              onChange={(e) => setInternalName(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="offer-customer-name">Customer-facing name</Label>
            <Input
              id="offer-customer-name"
              value={customerFacingName}
              onChange={(e) => setCustomerFacingName(e.target.value)}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="offer-valid-from">Valid from</Label>
            <Input
              id="offer-valid-from"
              type="datetime-local"
              value={validFrom}
              onChange={(e) => setValidFrom(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2 pt-6">
            <Checkbox
              id="offer-requires-code"
              checked={requiresCode}
              onCheckedChange={(checked) => setRequiresCode(checked === true)}
            />
            <Label htmlFor="offer-requires-code" className="text-sm font-normal">
              Requires a coupon code
            </Label>
          </div>
        </div>

        <div className="flex flex-col gap-2 rounded-md border p-3">
          <Label>Benefit</Label>
          {allowedKinds.length > 1 && (
            <Select value={effectiveKind} onValueChange={(v) => setBenefitKind(v as BenefitKind)}>
              <SelectTrigger className="w-56">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {allowedKinds.map((kind) => (
                  <SelectItem key={kind} value={kind}>
                    {humanize(kind)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          {effectiveKind === "percentage" && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="offer-percent">Percent off</Label>
              <Input id="offer-percent" value={percent} onChange={(e) => setPercent(e.target.value)} />
            </div>
          )}
          {effectiveKind === "fixed_amount" && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="offer-amount">Discount amount (₹)</Label>
              <Input
                id="offer-amount"
                value={amountRupees}
                onChange={(e) => setAmountRupees(e.target.value)}
              />
            </div>
          )}
          {effectiveKind === "buy_x_get_y" && (
            <div className="grid grid-cols-3 gap-3">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="offer-buy-qty">Buy quantity</Label>
                <Input
                  id="offer-buy-qty"
                  value={buyQuantity}
                  onChange={(e) => setBuyQuantity(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="offer-get-qty">Get quantity</Label>
                <Input
                  id="offer-get-qty"
                  value={getQuantity}
                  onChange={(e) => setGetQuantity(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="offer-get-discount">Get item discount %</Label>
                <Input
                  id="offer-get-discount"
                  value={getDiscountPercent}
                  onChange={(e) => setGetDiscountPercent(e.target.value)}
                />
              </div>
            </div>
          )}
          {effectiveKind === "combo_price" && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="offer-combo-price">Fixed combo price (₹)</Label>
              <Input
                id="offer-combo-price"
                value={comboPriceRupees}
                onChange={(e) => setComboPriceRupees(e.target.value)}
              />
            </div>
          )}
          {effectiveKind === "loyalty_bonus" && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="offer-grant-points">Bonus points granted</Label>
              <Input
                id="offer-grant-points"
                value={grantPoints}
                onChange={(e) => setGrantPoints(e.target.value)}
              />
            </div>
          )}
          {effectiveKind === "internal_credit" && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="offer-grant-credit">Credit granted (₹)</Label>
              <Input
                id="offer-grant-credit"
                value={grantAmountRupees}
                onChange={(e) => setGrantAmountRupees(e.target.value)}
              />
            </div>
          )}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Eligibility rule</Label>
          <p className="text-muted-foreground text-xs">
            A single condition every redeeming customer/order must satisfy.
          </p>
          <RuleConditionInput draft={ruleDraft} onChange={setRuleDraft} />
        </div>
      </div>
    </Modal>
  );
}
