"use client";

import { useState } from "react";
import Link from "next/link";

import {
  useAssignRole,
  useRemoveRole,
  useSetAccountStatus,
  useStaffDetail,
} from "@/lib/hooks/use-staff";
import { useRoles } from "@/lib/hooks/use-roles";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import {
  useAttendanceList,
  useCertifications,
  useEmploymentProfile,
  useLeaveRequests,
  usePerformanceReviews,
  useShiftList,
  useStaffDocuments,
  useStaffSkills,
  useTrainingAssignments,
} from "@/lib/hooks/use-staff-operations";
import {
  ATTENDANCE_STATUS_TONES,
  LEAVE_STATUS_TONES,
  LIFECYCLE_STATUS_TONES,
  PERFORMANCE_REVIEW_STATUS_TONES,
  SHIFT_STATUS_TONES,
  TRAINING_ASSIGNMENT_STATUS_TONES,
  VERIFICATION_STATUS_TONES,
  formatDate,
  formatDateTime,
  humanize,
} from "@/lib/crm-display";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/errors";

function ReasonPrompt({
  label,
  onConfirm,
  disabled,
}: {
  label: string;
  onConfirm: (reason: string) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");

  if (!open) {
    return (
      <Button variant="outline" size="sm" disabled={disabled} onClick={() => setOpen(true)}>
        {label}
      </Button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <input
        className="h-8 rounded-md border border-zinc-300 bg-transparent px-2 text-sm dark:border-zinc-700"
        placeholder="Reason (required)"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      <Button
        size="sm"
        disabled={!reason.trim() || disabled}
        onClick={() => {
          onConfirm(reason.trim());
          setOpen(false);
          setReason("");
        }}
      >
        Confirm
      </Button>
      <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>
        Cancel
      </Button>
    </div>
  );
}

export function StaffDetail({ staffId }: { staffId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: staff, isLoading, isError } = useStaffDetail(staffId);
  const { data: roles } = useRoles();
  const [actionError, setActionError] = useState<string | null>(null);

  const assignRole = useAssignRole(staffId);
  const removeRole = useRemoveRole(staffId);
  const setAccountStatus = useSetAccountStatus(staffId);

  const [selectedRoleCode, setSelectedRoleCode] = useState("");

  const canManageStaff = hasPermission(currentUser, "staff.manage");
  const canManageRoles = hasPermission(currentUser, "roles.manage");
  const isSelf = currentUser?.id === staffId;

  const canViewProfile = isSelf || hasPermission(currentUser, "staff.profile.view");
  const canViewDocuments = isSelf || hasPermission(currentUser, "staff.documents.view");
  const canViewShifts = isSelf || hasPermission(currentUser, "staff.shifts.view");
  const canViewAttendance = isSelf || hasPermission(currentUser, "staff.attendance.view");
  const canViewLeave = isSelf || hasPermission(currentUser, "staff.leave.view");
  const canViewTraining = isSelf || hasPermission(currentUser, "staff.training.view");
  const canViewCertifications = isSelf || hasPermission(currentUser, "staff.certifications.view");
  const canViewSkills = isSelf || hasPermission(currentUser, "staff.skills.view");
  const canViewReviews = isSelf || hasPermission(currentUser, "staff.reviews.view");

  const { data: profile } = useEmploymentProfile(canViewProfile ? staffId : undefined);
  const { data: documents } = useStaffDocuments(canViewDocuments ? staffId : undefined);
  const { data: shifts } = useShiftList(canViewShifts ? { staffUserId: staffId } : {});
  const { data: attendance } = useAttendanceList(canViewAttendance ? { staffUserId: staffId } : {});
  const { data: leaveRequests } = useLeaveRequests(canViewLeave ? { staffUserId: staffId } : {});
  const { data: trainingAssignments } = useTrainingAssignments(
    canViewTraining ? { staffUserId: staffId } : {},
  );
  const { data: certifications } = useCertifications(canViewCertifications ? staffId : undefined);
  const { data: skills } = useStaffSkills(canViewSkills ? staffId : undefined);
  const { data: reviews } = usePerformanceReviews(canViewReviews ? staffId : undefined);

  function handleError(error: unknown) {
    setActionError(error instanceof ApiError ? error.message : "That action could not be completed.");
  }

  if (isLoading) {
    return <div className="p-6 text-sm text-zinc-500">Loading…</div>;
  }
  if (isError || !staff) {
    return <div className="p-6 text-sm text-red-600">Could not load this staff member.</div>;
  }

  const assignedRoleCodes = new Set(staff.roles.map((role) => role.code));
  const availableRoles = (roles ?? []).filter((role) => !assignedRoleCodes.has(role.code));

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link href="/staff" className="text-sm text-zinc-500 hover:underline">
          ← Staff & HR
        </Link>
        <h1 className="mt-2 text-lg font-semibold">{staff.display_name}</h1>
        <p className="text-sm text-zinc-500">
          {staff.employee_code} · {staff.email}
          {staff.job_title ? ` · ${staff.job_title}` : ""}
        </p>
      </div>

      <div className="grid gap-1 text-sm sm:grid-cols-2">
        <div>
          <span className="text-zinc-500">Account status: </span>
          <span className="capitalize">{staff.account_status}</span>
        </div>
        <div>
          <span className="text-zinc-500">Employment status: </span>
          <span className="capitalize">{staff.employment_status.replace("_", " ")}</span>
        </div>
        <div>
          <span className="text-zinc-500">Phone: </span>
          <span>{staff.phone_e164 ?? "Not visible or not set"}</span>
        </div>
        <div>
          <span className="text-zinc-500">Timezone: </span>
          <span>{staff.timezone}</span>
        </div>
      </div>

      {actionError && <p className="text-sm text-red-600">{actionError}</p>}

      {canManageStaff && !isSelf && (
        <div className="flex gap-2">
          {staff.account_status !== "active" ? (
            <ReasonPrompt
              label="Activate account"
              disabled={setAccountStatus.isPending}
              onConfirm={(reason) =>
                setAccountStatus.mutate(
                  { action: "activate", reason },
                  { onError: handleError },
                )
              }
            />
          ) : (
            <ReasonPrompt
              label="Deactivate account"
              disabled={setAccountStatus.isPending}
              onConfirm={(reason) =>
                setAccountStatus.mutate(
                  { action: "deactivate", reason },
                  { onError: handleError },
                )
              }
            />
          )}
        </div>
      )}
      {isSelf && (
        <p className="text-sm text-zinc-500">
          You cannot change your own account status or roles — ask another privileged staff
          member.
        </p>
      )}

      <div>
        <h2 className="mb-2 text-sm font-semibold">Roles</h2>
        <ul className="mb-3 flex flex-wrap gap-2">
          {staff.roles.map((role) => (
            <li
              key={role.id}
              className="flex items-center gap-2 rounded-full bg-zinc-100 px-3 py-1 text-sm dark:bg-zinc-800"
            >
              {role.name}
              {canManageRoles && !isSelf && (
                <button
                  type="button"
                  aria-label={`Remove ${role.name}`}
                  className="text-zinc-500 hover:text-red-600"
                  disabled={removeRole.isPending}
                  onClick={() => {
                    const reason = window.prompt(`Reason for removing ${role.name}?`);
                    if (reason) {
                      removeRole.mutate({ roleCode: role.code, reason }, { onError: handleError });
                    }
                  }}
                >
                  ×
                </button>
              )}
            </li>
          ))}
          {staff.roles.length === 0 && <li className="text-sm text-zinc-500">No roles assigned.</li>}
        </ul>

        {canManageRoles && !isSelf && availableRoles.length > 0 && (
          <div className="flex items-center gap-2">
            <select
              className="h-9 rounded-md border border-zinc-300 bg-transparent px-2 text-sm dark:border-zinc-700"
              value={selectedRoleCode}
              onChange={(e) => setSelectedRoleCode(e.target.value)}
            >
              <option value="">Add a role…</option>
              {availableRoles.map((role) => (
                <option key={role.id} value={role.code}>
                  {role.name}
                </option>
              ))}
            </select>
            <Button
              size="sm"
              disabled={!selectedRoleCode || assignRole.isPending}
              onClick={() => {
                const reason = window.prompt(`Reason for assigning this role?`);
                if (reason) {
                  assignRole.mutate(
                    { roleCode: selectedRoleCode, reason },
                    { onError: handleError, onSuccess: () => setSelectedRoleCode("") },
                  );
                }
              }}
            >
              Assign
            </Button>
          </div>
        )}
      </div>

      <Tabs defaultValue="employment">
        <TabsList>
          {canViewProfile && <TabsTrigger value="employment">Employment</TabsTrigger>}
          {canViewShifts && <TabsTrigger value="schedule">Schedule</TabsTrigger>}
          {canViewAttendance && <TabsTrigger value="attendance">Attendance</TabsTrigger>}
          {canViewLeave && <TabsTrigger value="leave">Leave</TabsTrigger>}
          {canViewTraining && <TabsTrigger value="training">Training</TabsTrigger>}
          {canViewCertifications && <TabsTrigger value="certifications">Certifications</TabsTrigger>}
          {canViewSkills && <TabsTrigger value="skills">Skills</TabsTrigger>}
          {canViewDocuments && <TabsTrigger value="documents">Documents</TabsTrigger>}
          {canViewReviews && <TabsTrigger value="reviews">Reviews</TabsTrigger>}
        </TabsList>

        {canViewProfile && (
          <TabsContent value="employment" className="pt-4">
            <SectionCard title="Employment profile">
              {profile ? (
                <div className="grid gap-1 text-sm sm:grid-cols-2">
                  <div>
                    <span className="text-zinc-500">Lifecycle status: </span>
                    <StatusBadge
                      label={humanize(profile.lifecycle_status)}
                      tone={LIFECYCLE_STATUS_TONES[profile.lifecycle_status]}
                    />
                  </div>
                  <div>
                    <span className="text-zinc-500">Joining date: </span>
                    <span>{formatDate(profile.joining_date)}</span>
                  </div>
                  <div>
                    <span className="text-zinc-500">Work location: </span>
                    <span>{profile.work_location ?? "Not set"}</span>
                  </div>
                  <div>
                    <span className="text-zinc-500">Probation end: </span>
                    <span>{profile.probation_end_date ? formatDate(profile.probation_end_date) : "N/A"}</span>
                  </div>
                </div>
              ) : (
                <p className="text-muted-foreground text-sm">No employment profile on record.</p>
              )}
            </SectionCard>
          </TabsContent>
        )}

        {canViewShifts && (
          <TabsContent value="schedule" className="pt-4">
            <SectionCard title="Shifts">
              <ul className="flex flex-col gap-2 text-sm">
                {(shifts ?? []).map((shift) => (
                  <li key={shift.id} className="flex items-center justify-between gap-2">
                    <span>
                      {formatDate(shift.shift_date)} · {formatDateTime(shift.start_at)} –{" "}
                      {formatDateTime(shift.end_at)}
                    </span>
                    <StatusBadge label={humanize(shift.status)} tone={SHIFT_STATUS_TONES[shift.status]} />
                  </li>
                ))}
                {!shifts?.length && <li className="text-muted-foreground">No shifts scheduled.</li>}
              </ul>
            </SectionCard>
          </TabsContent>
        )}

        {canViewAttendance && (
          <TabsContent value="attendance" className="pt-4">
            <SectionCard title="Attendance">
              <ul className="flex flex-col gap-2 text-sm">
                {(attendance ?? []).map((record) => (
                  <li key={record.id} className="flex items-center justify-between gap-2">
                    <span>{formatDate(record.attendance_date)}</span>
                    <StatusBadge
                      label={humanize(record.status)}
                      tone={ATTENDANCE_STATUS_TONES[record.status]}
                    />
                  </li>
                ))}
                {!attendance?.length && (
                  <li className="text-muted-foreground">No attendance records.</li>
                )}
              </ul>
            </SectionCard>
          </TabsContent>
        )}

        {canViewLeave && (
          <TabsContent value="leave" className="pt-4">
            <SectionCard title="Leave requests">
              <ul className="flex flex-col gap-2 text-sm">
                {(leaveRequests ?? []).map((request) => (
                  <li key={request.id} className="flex items-center justify-between gap-2">
                    <span>
                      {formatDate(request.start_date)} – {formatDate(request.end_date)}
                    </span>
                    <StatusBadge
                      label={humanize(request.status)}
                      tone={LEAVE_STATUS_TONES[request.status]}
                    />
                  </li>
                ))}
                {!leaveRequests?.length && (
                  <li className="text-muted-foreground">No leave requests.</li>
                )}
              </ul>
            </SectionCard>
          </TabsContent>
        )}

        {canViewTraining && (
          <TabsContent value="training" className="pt-4">
            <SectionCard title="Training assignments">
              <ul className="flex flex-col gap-2 text-sm">
                {(trainingAssignments ?? []).map((assignment) => (
                  <li key={assignment.id} className="flex items-center justify-between gap-2">
                    <span>
                      {assignment.due_at ? `Due ${formatDate(assignment.due_at)}` : "No due date"}
                    </span>
                    <StatusBadge
                      label={humanize(assignment.status)}
                      tone={TRAINING_ASSIGNMENT_STATUS_TONES[assignment.status]}
                    />
                  </li>
                ))}
                {!trainingAssignments?.length && (
                  <li className="text-muted-foreground">No training assigned.</li>
                )}
              </ul>
            </SectionCard>
          </TabsContent>
        )}

        {canViewCertifications && (
          <TabsContent value="certifications" className="pt-4">
            <SectionCard title="Certifications">
              <ul className="flex flex-col gap-2 text-sm">
                {(certifications ?? []).map((cert) => (
                  <li key={cert.id} className="flex items-center justify-between gap-2">
                    <span>
                      {cert.certification_type} · issued {formatDate(cert.issue_date)}
                    </span>
                    <StatusBadge
                      label={humanize(cert.verification_status)}
                      tone={VERIFICATION_STATUS_TONES[cert.verification_status]}
                    />
                  </li>
                ))}
                {!certifications?.length && (
                  <li className="text-muted-foreground">No certifications recorded.</li>
                )}
              </ul>
            </SectionCard>
          </TabsContent>
        )}

        {canViewSkills && (
          <TabsContent value="skills" className="pt-4">
            <SectionCard title="Skills">
              <ul className="flex flex-col gap-2 text-sm">
                {(skills ?? []).map((skill) => (
                  <li key={skill.id} className="flex items-center justify-between gap-2">
                    <span>{humanize(skill.proficiency_level)}</span>
                    {skill.is_verified && <StatusBadge label="Verified" tone="success" />}
                  </li>
                ))}
                {!skills?.length && <li className="text-muted-foreground">No skills recorded.</li>}
              </ul>
            </SectionCard>
          </TabsContent>
        )}

        {canViewDocuments && (
          <TabsContent value="documents" className="pt-4">
            <SectionCard title="Documents">
              <ul className="flex flex-col gap-2 text-sm">
                {(documents ?? []).map((doc) => (
                  <li key={doc.id} className="flex items-center justify-between gap-2">
                    <span>
                      {humanize(doc.document_type)} · {doc.file_name}
                    </span>
                    <StatusBadge
                      label={humanize(doc.verification_status)}
                      tone={VERIFICATION_STATUS_TONES[doc.verification_status]}
                    />
                  </li>
                ))}
                {!documents?.length && <li className="text-muted-foreground">No documents uploaded.</li>}
              </ul>
            </SectionCard>
          </TabsContent>
        )}

        {canViewReviews && (
          <TabsContent value="reviews" className="pt-4">
            <SectionCard title="Performance reviews">
              <ul className="flex flex-col gap-2 text-sm">
                {(reviews ?? []).map((review) => (
                  <li key={review.id} className="flex items-center justify-between gap-2">
                    <span>
                      {review.cycle_label} · {formatDate(review.period_start_date)} –{" "}
                      {formatDate(review.period_end_date)}
                    </span>
                    <StatusBadge
                      label={humanize(review.status)}
                      tone={PERFORMANCE_REVIEW_STATUS_TONES[review.status]}
                    />
                  </li>
                ))}
                {!reviews?.length && <li className="text-muted-foreground">No reviews on record.</li>}
              </ul>
            </SectionCard>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
