"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  AttendanceCorrectionInput,
  AttendanceRecord,
  AttendanceRecordCreateInput,
  AvailabilityWindow,
  AvailabilityWindowCreateInput,
  CertificationCreateInput,
  DataResponse,
  DisciplinaryRecordCreateInput,
  EmploymentProfile,
  EmploymentProfileCreateInput,
  EmploymentProfileSensitive,
  EmploymentProfileUpdateInput,
  LeaveDecisionInput,
  LeaveRequest,
  LeaveRequestCreateInput,
  LeaveType,
  LeaveTypeCreateInput,
  LifecycleTransitionInput,
  PerformanceReview,
  PerformanceReviewCreateInput,
  PerformanceReviewTransitionInput,
  PerformanceReviewUpdateInput,
  ShiftChangeDecisionInput,
  ShiftChangeRequest,
  ShiftChangeRequestCreateInput,
  ShiftTemplate,
  ShiftTemplateCreateInput,
  Skill,
  SkillCreateInput,
  StaffAnalytics,
  StaffCertification,
  StaffDisciplinaryRecord,
  StaffDocument,
  StaffShift,
  StaffShiftCreateInput,
  StaffShiftUpdateInput,
  StaffSkill,
  StaffSkillSetInput,
  TrainingAssignInput,
  TrainingAssignment,
  TrainingAttempt,
  TrainingAttemptCompleteInput,
  TrainingCourse,
  TrainingCourseCreateInput,
  TransitionPlan,
  TransitionPlanCreateInput,
  TransitionStep,
  TransitionTemplate,
  TransitionTemplateCreateInput,
  TransitionTemplateStepCreateInput,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/staff-operations";

// --- Employment profiles -----------------------------------------------

export function useEmploymentProfile(staffUserId: string | undefined) {
  return useQuery({
    queryKey: ["staff-ops", "profiles", staffUserId],
    queryFn: () =>
      apiFetchClient<DataResponse<EmploymentProfile | EmploymentProfileSensitive>>(
        `${BASE}/profiles/${staffUserId}`,
      ),
    select: (response) => response.data,
    enabled: !!staffUserId,
  });
}

export function useCreateEmploymentProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: EmploymentProfileCreateInput) =>
      apiFetchClient<DataResponse<EmploymentProfile>>(`${BASE}/profiles`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "profiles"] }),
  });
}

export function useUpdateEmploymentProfile(staffUserId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: EmploymentProfileUpdateInput) =>
      apiFetchClient<DataResponse<EmploymentProfile>>(`${BASE}/profiles/${staffUserId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["staff-ops", "profiles", staffUserId] }),
  });
}

export function useTransitionEmploymentProfile(staffUserId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: LifecycleTransitionInput) =>
      apiFetchClient<DataResponse<EmploymentProfile>>(`${BASE}/profiles/${staffUserId}/transition`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["staff-ops", "profiles", staffUserId] }),
  });
}

// --- Documents --------------------------------------------------------

export function useStaffDocuments(staffUserId: string | undefined) {
  return useQuery({
    queryKey: ["staff-ops", "documents", staffUserId],
    queryFn: () =>
      apiFetchClient<DataResponse<StaffDocument[]>>(`${BASE}/documents?staff_user_id=${staffUserId}`),
    select: (response) => response.data,
    enabled: !!staffUserId,
  });
}

export function useUploadStaffDocument(staffUserId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { file: File; documentType: string; issueDate?: string; expiryDate?: string }) => {
      const formData = new FormData();
      formData.append("file", input.file);
      formData.append("staff_user_id", staffUserId);
      formData.append("document_type", input.documentType);
      if (input.issueDate) formData.append("issue_date", input.issueDate);
      if (input.expiryDate) formData.append("expiry_date", input.expiryDate);
      return apiFetchClient<DataResponse<StaffDocument>>(`${BASE}/documents`, {
        method: "POST",
        body: formData,
      });
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["staff-ops", "documents", staffUserId] }),
  });
}

export function useVerifyStaffDocument(staffUserId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ documentId, status }: { documentId: string; status: string }) =>
      apiFetchClient<DataResponse<StaffDocument>>(`${BASE}/documents/${documentId}/verify`, {
        method: "POST",
        body: { verification_status: status },
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["staff-ops", "documents", staffUserId] }),
  });
}

// --- Onboarding / offboarding --------------------------------------------

export function useTransitionTemplates(transitionType?: "onboarding" | "offboarding") {
  const query = transitionType ? `?transition_type=${transitionType}` : "";
  return useQuery({
    queryKey: ["staff-ops", "transition-templates", transitionType],
    queryFn: () =>
      apiFetchClient<DataResponse<TransitionTemplate[]>>(`${BASE}/transition-templates${query}`),
    select: (response) => response.data,
  });
}

export function useCreateTransitionTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: TransitionTemplateCreateInput) =>
      apiFetchClient<DataResponse<TransitionTemplate>>(`${BASE}/transition-templates`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "transition-templates"] }),
  });
}

export function useAddTransitionTemplateStep(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: TransitionTemplateStepCreateInput) =>
      apiFetchClient<DataResponse<{ status: string }>>(
        `${BASE}/transition-templates/${templateId}/steps`,
        { method: "POST", body: input },
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "transition-templates"] }),
  });
}

export function useCreateTransitionPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: TransitionPlanCreateInput) =>
      apiFetchClient<DataResponse<TransitionPlan>>(`${BASE}/transition-plans`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "transition-plans"] }),
  });
}

export function useTransitionPlanSteps(planId: string | undefined) {
  return useQuery({
    queryKey: ["staff-ops", "transition-plans", planId, "steps"],
    queryFn: () =>
      apiFetchClient<DataResponse<TransitionStep[]>>(`${BASE}/transition-plans/${planId}/steps`),
    select: (response) => response.data,
    enabled: !!planId,
  });
}

export function useCompleteTransitionStep(planId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ stepId, completionEvidence }: { stepId: string; completionEvidence?: string }) =>
      apiFetchClient<DataResponse<TransitionStep>>(`${BASE}/transition-steps/${stepId}/complete`, {
        method: "POST",
        body: { completion_evidence: completionEvidence ?? null },
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["staff-ops", "transition-plans", planId, "steps"] }),
  });
}

export function useApproveTransitionStep(planId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (stepId: string) =>
      apiFetchClient<DataResponse<TransitionStep>>(`${BASE}/transition-steps/${stepId}/approve`, {
        method: "POST",
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["staff-ops", "transition-plans", planId, "steps"] }),
  });
}

// --- Shifts -------------------------------------------------------------

export function useShiftTemplates() {
  return useQuery({
    queryKey: ["staff-ops", "shift-templates"],
    queryFn: () => apiFetchClient<DataResponse<ShiftTemplate[]>>(`${BASE}/shift-templates`),
    select: (response) => response.data,
  });
}

export function useCreateShiftTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ShiftTemplateCreateInput) =>
      apiFetchClient<DataResponse<ShiftTemplate>>(`${BASE}/shift-templates`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "shift-templates"] }),
  });
}

export interface ShiftListParams {
  staffUserId?: string;
  startDate?: string;
  endDate?: string;
}

export function useShiftList(params: ShiftListParams) {
  const query = new URLSearchParams();
  if (params.staffUserId) query.set("staff_user_id", params.staffUserId);
  if (params.startDate) query.set("start_date", params.startDate);
  if (params.endDate) query.set("end_date", params.endDate);

  return useQuery({
    queryKey: ["staff-ops", "shifts", params],
    queryFn: () => apiFetchClient<DataResponse<StaffShift[]>>(`${BASE}/shifts?${query.toString()}`),
    select: (response) => response.data,
  });
}

export function useCreateShift() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: StaffShiftCreateInput) =>
      apiFetchClient<DataResponse<StaffShift>>(`${BASE}/shifts`, { method: "POST", body: input }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "shifts"] }),
  });
}

export function useUpdateShift(shiftId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: StaffShiftUpdateInput) =>
      apiFetchClient<DataResponse<StaffShift>>(`${BASE}/shifts/${shiftId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "shifts"] }),
  });
}

export function usePublishShift() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (shiftId: string) =>
      apiFetchClient<DataResponse<StaffShift>>(`${BASE}/shifts/${shiftId}/publish`, {
        method: "POST",
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "shifts"] }),
  });
}

export function useCreateShiftChangeRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ShiftChangeRequestCreateInput) =>
      apiFetchClient<DataResponse<ShiftChangeRequest>>(`${BASE}/shift-change-requests`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "shift-change-requests"] }),
  });
}

export function useShiftChangeRequests(status?: string) {
  const query = status ? `?status=${status}` : "";
  return useQuery({
    queryKey: ["staff-ops", "shift-change-requests", status],
    queryFn: () =>
      apiFetchClient<DataResponse<ShiftChangeRequest[]>>(`${BASE}/shift-change-requests${query}`),
    select: (response) => response.data,
  });
}

export function useDecideShiftChangeRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ requestId, ...input }: { requestId: string } & ShiftChangeDecisionInput) =>
      apiFetchClient<DataResponse<ShiftChangeRequest>>(
        `${BASE}/shift-change-requests/${requestId}/decide`,
        { method: "POST", body: input },
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "shift-change-requests"] }),
  });
}

// --- Attendance -----------------------------------------------------------

export interface AttendanceListParams {
  staffUserId?: string;
  startDate?: string;
  endDate?: string;
}

export function useAttendanceList(params: AttendanceListParams) {
  const query = new URLSearchParams();
  if (params.staffUserId) query.set("staff_user_id", params.staffUserId);
  if (params.startDate) query.set("start_date", params.startDate);
  if (params.endDate) query.set("end_date", params.endDate);

  return useQuery({
    queryKey: ["staff-ops", "attendance", params],
    queryFn: () =>
      apiFetchClient<DataResponse<AttendanceRecord[]>>(`${BASE}/attendance?${query.toString()}`),
    select: (response) => response.data,
  });
}

export function useRecordAttendance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: AttendanceRecordCreateInput) =>
      apiFetchClient<DataResponse<AttendanceRecord>>(`${BASE}/attendance`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "attendance"] }),
  });
}

export function useCorrectAttendance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ recordId, ...input }: { recordId: string } & AttendanceCorrectionInput) =>
      apiFetchClient<DataResponse<AttendanceRecord>>(`${BASE}/attendance/${recordId}/correct`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "attendance"] }),
  });
}

// --- Leave ---------------------------------------------------------------

export function useLeaveTypes() {
  return useQuery({
    queryKey: ["staff-ops", "leave-types"],
    queryFn: () => apiFetchClient<DataResponse<LeaveType[]>>(`${BASE}/leave-types`),
    select: (response) => response.data,
  });
}

export function useCreateLeaveType() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: LeaveTypeCreateInput) =>
      apiFetchClient<DataResponse<LeaveType>>(`${BASE}/leave-types`, { method: "POST", body: input }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "leave-types"] }),
  });
}

export function useLeaveRequests(params: { staffUserId?: string; status?: string } = {}) {
  const query = new URLSearchParams();
  if (params.staffUserId) query.set("staff_user_id", params.staffUserId);
  if (params.status) query.set("status", params.status);

  return useQuery({
    queryKey: ["staff-ops", "leave-requests", params],
    queryFn: () =>
      apiFetchClient<DataResponse<LeaveRequest[]>>(`${BASE}/leave-requests?${query.toString()}`),
    select: (response) => response.data,
  });
}

export function useSubmitLeaveRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: LeaveRequestCreateInput) =>
      apiFetchClient<DataResponse<LeaveRequest>>(`${BASE}/leave-requests`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "leave-requests"] }),
  });
}

export function useDecideLeaveRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ requestId, ...input }: { requestId: string } & LeaveDecisionInput) =>
      apiFetchClient<DataResponse<LeaveRequest>>(`${BASE}/leave-requests/${requestId}/decide`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "leave-requests"] }),
  });
}

export function useWithdrawLeaveRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (requestId: string) =>
      apiFetchClient<DataResponse<LeaveRequest>>(`${BASE}/leave-requests/${requestId}/withdraw`, {
        method: "POST",
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "leave-requests"] }),
  });
}

// --- Training --------------------------------------------------------------

export function useTrainingCourses() {
  return useQuery({
    queryKey: ["staff-ops", "training-courses"],
    queryFn: () => apiFetchClient<DataResponse<TrainingCourse[]>>(`${BASE}/training/courses`),
    select: (response) => response.data,
  });
}

export function useCreateTrainingCourse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: TrainingCourseCreateInput) =>
      apiFetchClient<DataResponse<TrainingCourse>>(`${BASE}/training/courses`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "training-courses"] }),
  });
}

export function useTrainingAssignments(params: { staffUserId?: string; courseId?: string } = {}) {
  const query = new URLSearchParams();
  if (params.staffUserId) query.set("staff_user_id", params.staffUserId);
  if (params.courseId) query.set("course_id", params.courseId);

  return useQuery({
    queryKey: ["staff-ops", "training-assignments", params],
    queryFn: () =>
      apiFetchClient<DataResponse<TrainingAssignment[]>>(
        `${BASE}/training/assignments?${query.toString()}`,
      ),
    select: (response) => response.data,
  });
}

export function useAssignTraining() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: TrainingAssignInput) =>
      apiFetchClient<DataResponse<TrainingAssignment>>(`${BASE}/training/assignments`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "training-assignments"] }),
  });
}

export function useTrainingAttempts(assignmentId: string | undefined) {
  return useQuery({
    queryKey: ["staff-ops", "training-assignments", assignmentId, "attempts"],
    queryFn: () =>
      apiFetchClient<DataResponse<TrainingAttempt[]>>(
        `${BASE}/training/assignments/${assignmentId}/attempts`,
      ),
    select: (response) => response.data,
    enabled: !!assignmentId,
  });
}

export function useStartTrainingAttempt(assignmentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<TrainingAttempt>>(
        `${BASE}/training/assignments/${assignmentId}/attempts`,
        { method: "POST" },
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["staff-ops", "training-assignments", assignmentId, "attempts"],
      }),
  });
}

export function useCompleteTrainingAttempt(assignmentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ attemptId, ...input }: { attemptId: string } & TrainingAttemptCompleteInput) =>
      apiFetchClient<DataResponse<TrainingAttempt>>(`${BASE}/training/attempts/${attemptId}/complete`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["staff-ops", "training-assignments", assignmentId, "attempts"],
      }),
  });
}

// --- Certifications ---------------------------------------------------------

export function useCertifications(staffUserId?: string) {
  const query = staffUserId ? `?staff_user_id=${staffUserId}` : "";
  return useQuery({
    queryKey: ["staff-ops", "certifications", staffUserId],
    queryFn: () => apiFetchClient<DataResponse<StaffCertification[]>>(`${BASE}/certifications${query}`),
    select: (response) => response.data,
  });
}

export function useCreateCertification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CertificationCreateInput) =>
      apiFetchClient<DataResponse<StaffCertification>>(`${BASE}/certifications`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "certifications"] }),
  });
}

export function useVerifyCertification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ certificationId, status }: { certificationId: string; status: string }) =>
      apiFetchClient<DataResponse<StaffCertification>>(
        `${BASE}/certifications/${certificationId}/verify`,
        { method: "POST", body: { verification_status: status } },
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "certifications"] }),
  });
}

// --- Skills ------------------------------------------------------------

export function useSkills() {
  return useQuery({
    queryKey: ["staff-ops", "skills"],
    queryFn: () => apiFetchClient<DataResponse<Skill[]>>(`${BASE}/skills`),
    select: (response) => response.data,
  });
}

export function useCreateSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SkillCreateInput) =>
      apiFetchClient<DataResponse<Skill>>(`${BASE}/skills`, { method: "POST", body: input }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "skills"] }),
  });
}

export function useStaffSkills(staffUserId: string | undefined) {
  return useQuery({
    queryKey: ["staff-ops", "staff-skills", staffUserId],
    queryFn: () =>
      apiFetchClient<DataResponse<StaffSkill[]>>(`${BASE}/staff-skills/${staffUserId}`),
    select: (response) => response.data,
    enabled: !!staffUserId,
  });
}

export function useSetStaffSkill(staffUserId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: StaffSkillSetInput) =>
      apiFetchClient<DataResponse<StaffSkill>>(`${BASE}/staff-skills/${staffUserId}`, {
        method: "PUT",
        body: input,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["staff-ops", "staff-skills", staffUserId] }),
  });
}

// --- Performance reviews -----------------------------------------------

export function usePerformanceReviews(staffUserId?: string) {
  const query = staffUserId ? `?staff_user_id=${staffUserId}` : "";
  return useQuery({
    queryKey: ["staff-ops", "reviews", staffUserId],
    queryFn: () => apiFetchClient<DataResponse<PerformanceReview[]>>(`${BASE}/reviews${query}`),
    select: (response) => response.data,
  });
}

export function useCreatePerformanceReview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: PerformanceReviewCreateInput) =>
      apiFetchClient<DataResponse<PerformanceReview>>(`${BASE}/reviews`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "reviews"] }),
  });
}

export function useUpdatePerformanceReview(reviewId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: PerformanceReviewUpdateInput) =>
      apiFetchClient<DataResponse<PerformanceReview>>(`${BASE}/reviews/${reviewId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "reviews"] }),
  });
}

export function useTransitionPerformanceReview(reviewId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: PerformanceReviewTransitionInput) =>
      apiFetchClient<DataResponse<PerformanceReview>>(`${BASE}/reviews/${reviewId}/transition`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-ops", "reviews"] }),
  });
}

// --- Disciplinary ------------------------------------------------------

export function useDisciplinaryRecords(staffUserId: string | undefined) {
  return useQuery({
    queryKey: ["staff-ops", "disciplinary-records", staffUserId],
    queryFn: () =>
      apiFetchClient<DataResponse<StaffDisciplinaryRecord[]>>(
        `${BASE}/disciplinary-records?staff_user_id=${staffUserId}`,
      ),
    select: (response) => response.data,
    enabled: !!staffUserId,
  });
}

export function useCreateDisciplinaryRecord() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: DisciplinaryRecordCreateInput) =>
      apiFetchClient<DataResponse<StaffDisciplinaryRecord>>(`${BASE}/disciplinary-records`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["staff-ops", "disciplinary-records"] }),
  });
}

// --- Availability --------------------------------------------------------

export function useAvailabilityWindows(staffUserId: string | undefined) {
  return useQuery({
    queryKey: ["staff-ops", "availability", staffUserId],
    queryFn: () =>
      apiFetchClient<DataResponse<AvailabilityWindow[]>>(`${BASE}/availability/${staffUserId}`),
    select: (response) => response.data,
    enabled: !!staffUserId,
  });
}

export function useCreateAvailabilityWindow(staffUserId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: AvailabilityWindowCreateInput) =>
      apiFetchClient<DataResponse<AvailabilityWindow>>(`${BASE}/availability/${staffUserId}`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["staff-ops", "availability", staffUserId] }),
  });
}

// --- Analytics -----------------------------------------------------------

export function useStaffAnalytics() {
  return useQuery({
    queryKey: ["staff-ops", "analytics"],
    queryFn: () => apiFetchClient<DataResponse<StaffAnalytics>>(`${BASE}/analytics`),
    select: (response) => response.data,
  });
}
