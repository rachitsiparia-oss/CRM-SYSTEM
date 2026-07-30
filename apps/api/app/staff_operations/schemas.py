import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LifecycleStatus = Literal[
    "invited",
    "onboarding",
    "active",
    "on_leave",
    "suspended",
    "notice_period",
    "inactive",
    "terminated",
]
DocumentType = Literal[
    "identity_proof",
    "address_proof",
    "offer_letter",
    "employment_contract",
    "policy_acknowledgement",
    "food_safety_certificate",
    "medical_fitness_certificate",
    "training_certificate",
    "experience_letter",
    "exit_document",
    "other",
]
TransitionType = Literal["onboarding", "offboarding"]
ShiftStatus = Literal["scheduled", "published", "completed", "cancelled", "no_show"]
ShiftChangeRequestType = Literal["swap", "cover", "change"]
AttendanceStatus = Literal[
    "present", "absent", "late", "half_day", "on_leave", "weekly_off", "holiday", "missed_punch"
]
LeaveStatus = Literal["draft", "submitted", "approved", "rejected", "cancelled", "withdrawn"]
TrainingAssignmentStatus = Literal[
    "assigned", "in_progress", "completed", "failed", "overdue", "waived", "cancelled"
]
ProficiencyLevel = Literal["beginner", "intermediate", "advanced", "expert"]
ReviewStatus = Literal["draft", "in_progress", "submitted", "reviewed", "finalized", "acknowledged"]
DisciplinarySeverity = Literal["minor", "moderate", "severe"]
AvailabilityType = Literal["available", "unavailable", "preferred"]


# --- Employment profile ----------------------------------------------------


class EmploymentProfileCreateIn(BaseModel):
    staff_user_id: uuid.UUID
    joining_date: date
    reporting_manager_id: uuid.UUID | None = None
    secondary_supervisor_id: uuid.UUID | None = None
    work_location: str | None = None
    default_shift_template_id: uuid.UUID | None = None
    probation_end_date: date | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    emergency_contact_relation: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    address_city: str | None = None
    address_state: str | None = None
    address_postal_code: str | None = None
    uniform_size: str | None = None


class EmploymentProfileUpdateIn(BaseModel):
    reporting_manager_id: uuid.UUID | None = None
    secondary_supervisor_id: uuid.UUID | None = None
    work_location: str | None = None
    default_shift_template_id: uuid.UUID | None = None
    probation_end_date: date | None = None
    confirmation_date: date | None = None
    last_working_date: date | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    emergency_contact_relation: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    address_city: str | None = None
    address_state: str | None = None
    address_postal_code: str | None = None
    uniform_size: str | None = None
    restricted_notes: str | None = None
    version: int


class LifecycleTransitionIn(BaseModel):
    target_status: LifecycleStatus
    reason: str | None = None


class EmploymentProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    staff_user_id: uuid.UUID
    lifecycle_status: str
    reporting_manager_id: uuid.UUID | None
    secondary_supervisor_id: uuid.UUID | None
    work_location: str | None
    default_shift_template_id: uuid.UUID | None
    joining_date: date
    probation_end_date: date | None
    confirmation_date: date | None
    last_working_date: date | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    emergency_contact_relation: str | None
    uniform_size: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class EmploymentProfileSensitiveOut(EmploymentProfileOut):
    address_line1: str | None
    address_line2: str | None
    address_city: str | None
    address_state: str | None
    address_postal_code: str | None
    restricted_notes: str | None


# --- Documents --------------------------------------------------------------


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    staff_user_id: uuid.UUID
    document_type: str
    file_name: str
    mime_type: str
    size_bytes: int
    issue_date: date | None
    expiry_date: date | None
    verification_status: str
    verified_by: uuid.UUID | None
    verified_at: datetime | None
    reminder_eligible: bool
    created_at: datetime


class DocumentVerifyIn(BaseModel):
    verification_status: Literal["verified", "rejected", "expired"]


# --- Onboarding / offboarding ------------------------------------------------


class TransitionTemplateCreateIn(BaseModel):
    transition_type: TransitionType
    name: str = Field(min_length=1, max_length=160)
    department_id: uuid.UUID | None = None
    role_id: uuid.UUID | None = None


class TransitionTemplateStepCreateIn(BaseModel):
    step_order: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    step_type: str
    depends_on_step_id: uuid.UUID | None = None
    requires_approval: bool = False
    related_knowledge_article_id: uuid.UUID | None = None


class TransitionTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transition_type: str
    name: str
    department_id: uuid.UUID | None
    role_id: uuid.UUID | None
    is_active: bool


class TransitionPlanCreateIn(BaseModel):
    staff_user_id: uuid.UUID
    template_id: uuid.UUID | None = None
    transition_type: TransitionType


class TransitionPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    staff_user_id: uuid.UUID
    template_id: uuid.UUID | None
    transition_type: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    completion_percentage: int


class TransitionStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plan_id: uuid.UUID
    step_order: int
    title: str
    step_type: str
    status: str
    due_at: datetime | None
    completed_at: datetime | None
    requires_approval: bool
    approved_at: datetime | None


class TransitionStepCompleteIn(BaseModel):
    completion_evidence: str | None = None


# --- Shifts -------------------------------------------------------------


class ShiftTemplateCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    department_id: uuid.UUID | None = None
    start_time: time
    end_time: time
    break_minutes: int = 0
    is_overnight: bool = False
    grace_period_minutes: int = 0


class ShiftTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    department_id: uuid.UUID | None
    start_time: time
    end_time: time
    break_minutes: int
    is_overnight: bool
    grace_period_minutes: int
    is_active: bool


class StaffShiftCreateIn(BaseModel):
    staff_user_id: uuid.UUID
    shift_date: date
    shift_template_id: uuid.UUID | None = None
    start_at: datetime
    end_at: datetime
    department_id: uuid.UUID | None = None
    role_on_shift: str | None = None
    notes: str | None = None


class StaffShiftUpdateIn(BaseModel):
    start_at: datetime | None = None
    end_at: datetime | None = None
    role_on_shift: str | None = None
    notes: str | None = None
    version: int


class StaffShiftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    staff_user_id: uuid.UUID
    shift_date: date
    shift_template_id: uuid.UUID | None
    start_at: datetime
    end_at: datetime
    department_id: uuid.UUID | None
    role_on_shift: str | None
    status: str
    notes: str | None
    is_published: bool
    published_at: datetime | None
    version: int


class ShiftChangeRequestCreateIn(BaseModel):
    shift_id: uuid.UUID
    request_type: ShiftChangeRequestType
    proposed_staff_id: uuid.UUID | None = None
    reason: str | None = None


class ShiftChangeDecisionIn(BaseModel):
    approve: bool
    decision_reason: str | None = None


class ShiftChangeRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    shift_id: uuid.UUID
    requested_by: uuid.UUID
    request_type: str
    proposed_staff_id: uuid.UUID | None
    reason: str | None
    status: str
    decided_by: uuid.UUID | None
    decided_at: datetime | None
    decision_reason: str | None


# --- Attendance -----------------------------------------------------------


class AttendanceRecordCreateIn(BaseModel):
    staff_user_id: uuid.UUID
    attendance_date: date
    shift_id: uuid.UUID | None = None
    status: AttendanceStatus
    actual_check_in_at: datetime | None = None
    actual_check_out_at: datetime | None = None


class AttendanceCorrectionIn(BaseModel):
    status: AttendanceStatus | None = None
    actual_check_in_at: datetime | None = None
    actual_check_out_at: datetime | None = None
    reason: str = Field(min_length=1)


class AttendanceRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    staff_user_id: uuid.UUID
    attendance_date: date
    shift_id: uuid.UUID | None
    scheduled_start_at: datetime | None
    scheduled_end_at: datetime | None
    actual_check_in_at: datetime | None
    actual_check_out_at: datetime | None
    status: str
    late_minutes: int
    early_leave_minutes: int
    worked_minutes: int
    break_minutes: int
    source: str
    is_corrected: bool
    approval_state: str


# --- Leave ---------------------------------------------------------------


class LeaveTypeCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    code: str = Field(min_length=1, max_length=24)
    is_paid: bool = True
    requires_notice_days: int = 0
    max_consecutive_days: int | None = None
    allows_carry_forward: bool = False
    carry_forward_max_days: int | None = None


class LeaveTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    is_paid: bool
    requires_notice_days: int
    max_consecutive_days: int | None
    allows_carry_forward: bool
    is_active: bool


class LeaveRequestCreateIn(BaseModel):
    leave_type_id: uuid.UUID
    start_date: date
    end_date: date
    is_partial_day: bool = False
    partial_day_portion: Literal["first_half", "second_half"] | None = None
    reason: str | None = None


class LeaveDecisionIn(BaseModel):
    approve: bool
    decision_reason: str | None = None


class LeaveRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    staff_user_id: uuid.UUID
    leave_type_id: uuid.UUID
    start_date: date
    end_date: date
    is_partial_day: bool
    partial_day_portion: str | None
    reason: str | None
    status: str
    approver_id: uuid.UUID | None
    decision_reason: str | None
    decided_at: datetime | None


# --- Training --------------------------------------------------------------


class TrainingCourseCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category: str | None = None
    department_id: uuid.UUID | None = None
    role_id: uuid.UUID | None = None
    is_mandatory: bool = False
    validity_period_days: int | None = None
    passing_score: int | None = Field(default=None, ge=0, le=100)
    max_attempts: int = Field(default=3, ge=1)
    content_source: str | None = None


class TrainingCourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    title: str
    description: str | None
    category: str | None
    is_mandatory: bool
    validity_period_days: int | None
    passing_score: int | None
    max_attempts: int
    is_active: bool


class TrainingAssignIn(BaseModel):
    course_id: uuid.UUID
    staff_user_id: uuid.UUID
    due_at: datetime | None = None


class TrainingAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    staff_user_id: uuid.UUID
    assigned_at: datetime
    due_at: datetime | None
    status: str


class TrainingAttemptStartIn(BaseModel):
    pass


class TrainingAttemptCompleteIn(BaseModel):
    score: int = Field(ge=0, le=100)
    completion_evidence: str | None = None


class TrainingAttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    assignment_id: uuid.UUID
    attempt_number: int
    started_at: datetime | None
    completed_at: datetime | None
    score: int | None
    is_pass: bool | None
    reviewer_id: uuid.UUID | None


# --- Certifications ---------------------------------------------------------


class CertificationCreateIn(BaseModel):
    staff_user_id: uuid.UUID
    certification_type: str = Field(min_length=1, max_length=120)
    issuer: str | None = None
    certificate_number: str | None = None
    issue_date: date
    expiry_date: date | None = None
    renewal_of_certification_id: uuid.UUID | None = None


class CertificationVerifyIn(BaseModel):
    verification_status: Literal["verified", "rejected", "expired"]


class CertificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    staff_user_id: uuid.UUID
    certification_type: str
    issuer: str | None
    certificate_number: str | None
    issue_date: date
    expiry_date: date | None
    verification_status: str
    verified_by: uuid.UUID | None
    verified_at: datetime | None
    renewal_of_certification_id: uuid.UUID | None


# --- Skills ------------------------------------------------------------


class SkillCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str | None = None
    description: str | None = None


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str | None
    description: str | None
    is_active: bool


class StaffSkillSetIn(BaseModel):
    skill_id: uuid.UUID
    proficiency_level: ProficiencyLevel = "beginner"
    notes: str | None = None


class StaffSkillVerifyIn(BaseModel):
    is_verified: bool


class StaffSkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    staff_user_id: uuid.UUID
    skill_id: uuid.UUID
    proficiency_level: str
    is_verified: bool
    verified_by: uuid.UUID | None
    verified_at: datetime | None
    notes: str | None


# --- Performance reviews -----------------------------------------------


class ReviewGoalIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    target_date: date | None = None


class PerformanceReviewCreateIn(BaseModel):
    staff_user_id: uuid.UUID
    cycle_label: str = Field(min_length=1, max_length=80)
    period_start_date: date
    period_end_date: date
    goals: list[ReviewGoalIn] = Field(default_factory=list)


class PerformanceReviewUpdateIn(BaseModel):
    overall_rating: int | None = Field(default=None, ge=1, le=5)
    strengths: str | None = None
    improvement_areas: str | None = None
    staff_comments: str | None = None
    manager_comments: str | None = None
    version: int


class PerformanceReviewTransitionIn(BaseModel):
    target_status: ReviewStatus


class PerformanceReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    staff_user_id: uuid.UUID
    reviewer_id: uuid.UUID
    cycle_label: str
    period_start_date: date
    period_end_date: date
    status: str
    overall_rating: int | None
    strengths: str | None
    improvement_areas: str | None
    staff_comments: str | None
    manager_comments: str | None
    staff_acknowledged_at: datetime | None
    finalized_at: datetime | None
    version: int


# --- Disciplinary ------------------------------------------------------


class DisciplinaryRecordCreateIn(BaseModel):
    staff_user_id: uuid.UUID
    incident_date: date
    category: str = Field(min_length=1, max_length=60)
    description: str = Field(min_length=1)
    severity: DisciplinarySeverity
    action_taken: str | None = None


class DisciplinaryRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    staff_user_id: uuid.UUID
    incident_date: date
    category: str
    description: str
    severity: str
    action_taken: str | None
    recorded_by: uuid.UUID
    status: str
    resolved_at: datetime | None


# --- Availability --------------------------------------------------------


class AvailabilityWindowCreateIn(BaseModel):
    availability_type: AvailabilityType
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    specific_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    reason: str | None = None
    effective_start_date: date | None = None
    effective_end_date: date | None = None


class AvailabilityWindowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    staff_user_id: uuid.UUID
    availability_type: str
    day_of_week: int | None
    specific_date: date | None
    start_time: time | None
    end_time: time | None
    reason: str | None


class StaffAnalyticsOut(BaseModel):
    active_staff: int
    staff_by_department: list[dict[str, object]]
    onboarding_in_progress: int
    documents_expiring_30d: int
    certifications_expiring_30d: int
    on_leave_today: int
    scheduled_today: int
    attendance_exceptions_today: int
    late_arrivals_today: int
    training_overdue: int
    mandatory_training_completion_pct: float
    knowledge_acknowledgement_completion_pct: float
    reviews_due: int
    open_shift_change_requests: int
