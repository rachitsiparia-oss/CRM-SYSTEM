"use client";

import { useState } from "react";

import {
  useCertifications,
  useCreateCertification,
  useCreateSkill,
  useSkills,
  useVerifyCertification,
} from "@/lib/hooks/use-staff-operations";
import { useStaffList } from "@/lib/hooks/use-staff";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { VERIFICATION_STATUS_TONES, formatDate, humanize } from "@/lib/crm-display";
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

export function CertificationsView() {
  const { data: currentUser } = useCurrentUser();
  const canManage = hasPermission(currentUser, "staff.certifications.manage");
  const canManageSkills = hasPermission(currentUser, "staff.skills.manage");

  const [error, setError] = useState<string | null>(null);

  const { data: staffPage } = useStaffList({ page: 1, pageSize: 100 });
  const staffOptions = staffPage?.data ?? [];

  const { data: certifications, isLoading } = useCertifications();
  const { data: skills } = useSkills();

  const createCertification = useCreateCertification();
  const verifyCertification = useVerifyCertification();
  const createSkill = useCreateSkill();

  const [certStaffId, setCertStaffId] = useState("");
  const [certType, setCertType] = useState("");
  const [certIssueDate, setCertIssueDate] = useState("");

  const [skillName, setSkillName] = useState("");

  const staffName = (id: string) =>
    staffOptions.find((s) => s.id === id)?.display_name ?? "Unknown staff";

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader title="Certifications & skills" description="Staff certifications and the skills matrix." />

      {error && <p className="text-sm text-red-600">{error}</p>}

      <Tabs defaultValue="certifications">
        <TabsList>
          <TabsTrigger value="certifications">Certifications</TabsTrigger>
          <TabsTrigger value="skills">Skills catalogue</TabsTrigger>
        </TabsList>

        <TabsContent value="certifications" className="flex flex-col gap-4 pt-4">
          {canManage && (
            <SectionCard title="Record certification">
              <div className="flex flex-wrap items-end gap-2">
                <Select value={certStaffId} onValueChange={setCertStaffId}>
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
                <Input
                  placeholder="Certification type"
                  value={certType}
                  onChange={(e) => setCertType(e.target.value)}
                  className="w-48"
                />
                <Input
                  type="date"
                  value={certIssueDate}
                  onChange={(e) => setCertIssueDate(e.target.value)}
                />
                <Button
                  size="sm"
                  disabled={!certStaffId || !certType || !certIssueDate || createCertification.isPending}
                  onClick={() =>
                    createCertification.mutate(
                      {
                        staff_user_id: certStaffId,
                        certification_type: certType,
                        issue_date: certIssueDate,
                      },
                      {
                        onSuccess: () => setCertType(""),
                        onError: (err) =>
                          setError(err instanceof ApiError ? err.message : "Could not record certification."),
                      },
                    )
                  }
                >
                  Add
                </Button>
              </div>
            </SectionCard>
          )}

          <SectionCard title="Certifications">
            <ul className="flex flex-col gap-2 text-sm">
              {isLoading && <li className="text-muted-foreground">Loading…</li>}
              {(certifications ?? []).map((cert) => (
                <li key={cert.id} className="flex items-center justify-between gap-2">
                  <span>
                    {staffName(cert.staff_user_id)} · {cert.certification_type} · issued{" "}
                    {formatDate(cert.issue_date)}
                    {cert.expiry_date ? ` · expires ${formatDate(cert.expiry_date)}` : ""}
                  </span>
                  <div className="flex items-center gap-2">
                    <StatusBadge
                      label={humanize(cert.verification_status)}
                      tone={VERIFICATION_STATUS_TONES[cert.verification_status]}
                    />
                    {canManage && cert.verification_status === "pending" && (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={verifyCertification.isPending}
                        onClick={() =>
                          verifyCertification.mutate(
                            { certificationId: cert.id, status: "verified" },
                            {
                              onError: (err) =>
                                setError(err instanceof ApiError ? err.message : "Could not verify."),
                            },
                          )
                        }
                      >
                        Verify
                      </Button>
                    )}
                  </div>
                </li>
              ))}
              {!isLoading && !certifications?.length && (
                <li className="text-muted-foreground">No certifications recorded.</li>
              )}
            </ul>
          </SectionCard>
        </TabsContent>

        <TabsContent value="skills" className="flex flex-col gap-4 pt-4">
          <SectionCard title="Skills catalogue">
            {canManageSkills && (
              <div className="mb-3 flex items-end gap-2">
                <Input
                  placeholder="Skill name"
                  value={skillName}
                  onChange={(e) => setSkillName(e.target.value)}
                  className="w-64"
                />
                <Button
                  size="sm"
                  disabled={!skillName || createSkill.isPending}
                  onClick={() =>
                    createSkill.mutate(
                      { name: skillName },
                      {
                        onSuccess: () => setSkillName(""),
                        onError: (err) =>
                          setError(err instanceof ApiError ? err.message : "Could not create skill."),
                      },
                    )
                  }
                >
                  Add skill
                </Button>
              </div>
            )}
            <ul className="flex flex-col gap-2 text-sm">
              {(skills ?? []).map((skill) => (
                <li key={skill.id} className="flex items-center justify-between gap-2">
                  <span>{skill.name}</span>
                  {skill.category && <span className="text-muted-foreground text-xs">{skill.category}</span>}
                </li>
              ))}
              {!skills?.length && <li className="text-muted-foreground">No skills defined yet.</li>}
            </ul>
          </SectionCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}
