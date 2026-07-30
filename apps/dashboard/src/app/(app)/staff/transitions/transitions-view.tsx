"use client";

import { useState } from "react";
import type { TransitionType } from "@rkpr/contracts";

import {
  useCompleteTransitionStep,
  useCreateTransitionPlan,
  useCreateTransitionTemplate,
  useTransitionPlanSteps,
  useTransitionTemplates,
} from "@/lib/hooks/use-staff-operations";
import { useStaffList } from "@/lib/hooks/use-staff";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function TransitionsView() {
  const { data: currentUser } = useCurrentUser();
  const canManageOnboarding = hasPermission(currentUser, "staff.onboarding.manage");
  const canManageOffboarding = hasPermission(currentUser, "staff.offboarding.manage");

  const [error, setError] = useState<string | null>(null);

  const { data: staffPage } = useStaffList({ page: 1, pageSize: 100 });
  const staffOptions = staffPage?.data ?? [];

  const { data: onboardingTemplates } = useTransitionTemplates("onboarding");
  const { data: offboardingTemplates } = useTransitionTemplates("offboarding");

  const createTemplate = useCreateTransitionTemplate();
  const createPlan = useCreateTransitionPlan();

  const [templateType, setTemplateType] = useState<TransitionType>("onboarding");
  const [templateName, setTemplateName] = useState("");

  const [planStaffId, setPlanStaffId] = useState("");
  const [planType, setPlanType] = useState<TransitionType>("onboarding");
  const [planTemplateId, setPlanTemplateId] = useState("");
  const [activePlanId, setActivePlanId] = useState<string | null>(null);

  const { data: steps } = useTransitionPlanSteps(activePlanId ?? undefined);
  const completeStep = useCompleteTransitionStep(activePlanId ?? "");

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader title="Onboarding & offboarding" description="Transition templates and staff plans." />

      {error && <p className="text-sm text-red-600">{error}</p>}

      <Tabs defaultValue="plans">
        <TabsList>
          <TabsTrigger value="plans">Plans</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
        </TabsList>

        <TabsContent value="plans" className="flex flex-col gap-4 pt-4">
          {(canManageOnboarding || canManageOffboarding) && (
            <SectionCard title="Start a plan">
              <div className="flex flex-wrap items-end gap-2">
                <Select value={planStaffId} onValueChange={setPlanStaffId}>
                  <SelectTrigger className="w-48" aria-label="Staff member">
                    <SelectValue placeholder="Staff member" />
                  </SelectTrigger>
                  <SelectContent>
                    {staffOptions.map((s) => (
                      <SelectItem key={s.id} value={s.id}>
                        {s.display_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={planType} onValueChange={(v) => setPlanType(v as TransitionType)}>
                  <SelectTrigger className="w-40" aria-label="Type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="onboarding">Onboarding</SelectItem>
                    <SelectItem value="offboarding">Offboarding</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={planTemplateId} onValueChange={setPlanTemplateId}>
                  <SelectTrigger className="w-48" aria-label="Template">
                    <SelectValue placeholder="Template (optional)" />
                  </SelectTrigger>
                  <SelectContent>
                    {(planType === "onboarding" ? onboardingTemplates : offboardingTemplates)?.map(
                      (template) => (
                        <SelectItem key={template.id} value={template.id}>
                          {template.name}
                        </SelectItem>
                      ),
                    )}
                  </SelectContent>
                </Select>
                <Button
                  size="sm"
                  disabled={!planStaffId || createPlan.isPending}
                  onClick={() =>
                    createPlan.mutate(
                      {
                        staff_user_id: planStaffId,
                        transition_type: planType,
                        template_id: planTemplateId || null,
                      },
                      {
                        onSuccess: (response) => setActivePlanId(response.data.id),
                        onError: (err) =>
                          setError(err instanceof ApiError ? err.message : "Could not start plan."),
                      },
                    )
                  }
                >
                  Start plan
                </Button>
              </div>
            </SectionCard>
          )}

          {activePlanId && (
            <SectionCard title="Plan steps">
              <ul className="flex flex-col gap-2 text-sm">
                {(steps ?? []).map((step) => (
                  <li key={step.id} className="flex items-center justify-between gap-2">
                    <span>
                      {step.step_order}. {step.title}
                    </span>
                    <div className="flex items-center gap-2">
                      <StatusBadge label={humanize(step.status)} tone="neutral" />
                      {step.status !== "completed" && step.status !== "skipped" && (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={completeStep.isPending}
                          onClick={() =>
                            completeStep.mutate(
                              { stepId: step.id },
                              {
                                onError: (err) =>
                                  setError(err instanceof ApiError ? err.message : "Could not complete step."),
                              },
                            )
                          }
                        >
                          Complete
                        </Button>
                      )}
                    </div>
                  </li>
                ))}
                {!steps?.length && <li className="text-muted-foreground">No steps on this plan.</li>}
              </ul>
            </SectionCard>
          )}
        </TabsContent>

        <TabsContent value="templates" className="flex flex-col gap-4 pt-4">
          {(canManageOnboarding || canManageOffboarding) && (
            <SectionCard title="Create template">
              <div className="flex flex-wrap items-end gap-2">
                <Select value={templateType} onValueChange={(v) => setTemplateType(v as TransitionType)}>
                  <SelectTrigger className="w-40" aria-label="Type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="onboarding">Onboarding</SelectItem>
                    <SelectItem value="offboarding">Offboarding</SelectItem>
                  </SelectContent>
                </Select>
                <Input
                  placeholder="Template name"
                  value={templateName}
                  onChange={(e) => setTemplateName(e.target.value)}
                  className="w-64"
                />
                <Button
                  size="sm"
                  disabled={!templateName || createTemplate.isPending}
                  onClick={() =>
                    createTemplate.mutate(
                      { transition_type: templateType, name: templateName },
                      {
                        onSuccess: () => setTemplateName(""),
                        onError: (err) =>
                          setError(err instanceof ApiError ? err.message : "Could not create template."),
                      },
                    )
                  }
                >
                  Add template
                </Button>
              </div>
            </SectionCard>
          )}

          <SectionCard title="Onboarding templates">
            <ul className="flex flex-col gap-2 text-sm">
              {(onboardingTemplates ?? []).map((template) => (
                <li key={template.id}>{template.name}</li>
              ))}
              {!onboardingTemplates?.length && (
                <li className="text-muted-foreground">No onboarding templates yet.</li>
              )}
            </ul>
          </SectionCard>

          <SectionCard title="Offboarding templates">
            <ul className="flex flex-col gap-2 text-sm">
              {(offboardingTemplates ?? []).map((template) => (
                <li key={template.id}>{template.name}</li>
              ))}
              {!offboardingTemplates?.length && (
                <li className="text-muted-foreground">No offboarding templates yet.</li>
              )}
            </ul>
          </SectionCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}
