import uuid
from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.auth.dependencies import CurrentStaffUser
from app.core.responses import DataResponse, request_meta
from app.db.models import (
    AttendanceRecord,
    LeaveRequest,
    PerformanceReview,
    ShiftChangeRequest,
    StaffCertification,
    StaffDisciplinaryRecord,
    StaffDocument,
    StaffShift,
    StaffSkill,
    StaffTransitionPlan,
    StaffTransitionStep,
    StaffTransitionTemplate,
    StaffUser,
    TrainingAssignment,
    TrainingAttempt,
)
from app.db.session import get_db
from app.permissions.dependencies import require_permission
from app.permissions.service import has_permission
from app.staff_operations import (
    analytics,
    attendance,
    availability,
    certifications,
    disciplinary,
    documents,
    leave,
    profile,
    reviews,
    shifts,
    skills,
    training,
    transitions,
)
from app.staff_operations.schemas import (
    AttendanceCorrectionIn,
    AttendanceRecordCreateIn,
    AttendanceRecordOut,
    AvailabilityWindowCreateIn,
    AvailabilityWindowOut,
    CertificationCreateIn,
    CertificationOut,
    CertificationVerifyIn,
    DisciplinaryRecordCreateIn,
    DisciplinaryRecordOut,
    DocumentOut,
    DocumentVerifyIn,
    EmploymentProfileCreateIn,
    EmploymentProfileOut,
    EmploymentProfileSensitiveOut,
    EmploymentProfileUpdateIn,
    LeaveDecisionIn,
    LeaveRequestCreateIn,
    LeaveRequestOut,
    LeaveTypeCreateIn,
    LeaveTypeOut,
    LifecycleTransitionIn,
    PerformanceReviewCreateIn,
    PerformanceReviewOut,
    PerformanceReviewTransitionIn,
    PerformanceReviewUpdateIn,
    ShiftChangeDecisionIn,
    ShiftChangeRequestCreateIn,
    ShiftChangeRequestOut,
    ShiftTemplateCreateIn,
    ShiftTemplateOut,
    SkillCreateIn,
    SkillOut,
    StaffAnalyticsOut,
    StaffShiftCreateIn,
    StaffShiftOut,
    StaffShiftUpdateIn,
    StaffSkillOut,
    StaffSkillSetIn,
    TrainingAssignIn,
    TrainingAssignmentOut,
    TrainingAttemptCompleteIn,
    TrainingAttemptOut,
    TrainingCourseCreateIn,
    TrainingCourseOut,
    TransitionPlanCreateIn,
    TransitionPlanOut,
    TransitionStepCompleteIn,
    TransitionStepOut,
    TransitionTemplateCreateIn,
    TransitionTemplateOut,
    TransitionTemplateStepCreateIn,
)

router = APIRouter(prefix="/api/v1/staff-operations", tags=["staff-operations"])


async def _require_self_or_permission(
    session: AsyncSession, *, actor: StaffUser, target_staff_id: uuid.UUID, permission_code: str
) -> None:
    if actor.id == target_staff_id:
        return
    if not await has_permission(session, actor.id, permission_code):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Not authorized for this staff member."
        )


# --- Employment profiles -----------------------------------------------


@router.post("/profiles", status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: EmploymentProfileCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.profile.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[EmploymentProfileOut]:
    result = await profile.create_profile(session, actor=actor, payload=payload)
    return DataResponse(
        data=EmploymentProfileOut.model_validate(result), meta=request_meta(request)
    )


@router.get("/profiles/{staff_user_id}")
async def get_profile(
    staff_user_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.profile.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[EmploymentProfileOut | EmploymentProfileSensitiveOut]:
    result = await profile.get_profile(session, staff_user_id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Employment profile not found.")
    if await has_permission(session, actor.id, "staff.hr_sensitive.read"):
        return DataResponse(
            data=EmploymentProfileSensitiveOut.model_validate(result), meta=request_meta(request)
        )
    return DataResponse(
        data=EmploymentProfileOut.model_validate(result), meta=request_meta(request)
    )


@router.patch("/profiles/{staff_user_id}")
async def update_profile(
    staff_user_id: uuid.UUID,
    payload: EmploymentProfileUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.profile.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[EmploymentProfileOut]:
    existing = await profile.get_profile(session, staff_user_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Employment profile not found.")
    result = await profile.update_profile(session, actor=actor, profile=existing, payload=payload)
    return DataResponse(
        data=EmploymentProfileOut.model_validate(result), meta=request_meta(request)
    )


@router.post("/profiles/{staff_user_id}/transition")
async def transition_profile(
    staff_user_id: uuid.UUID,
    payload: LifecycleTransitionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.profile.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[EmploymentProfileOut]:
    existing = await profile.get_profile(session, staff_user_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Employment profile not found.")
    result = await profile.transition_lifecycle(
        session, actor=actor, profile=existing, payload=payload
    )
    return DataResponse(
        data=EmploymentProfileOut.model_validate(result), meta=request_meta(request)
    )


# --- Documents --------------------------------------------------------


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.documents.manage")),
    session: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    staff_user_id: uuid.UUID = Form(...),
    document_type: str = Form(...),
    issue_date: str | None = Form(default=None),
    expiry_date: str | None = Form(default=None),
    replaces_document_id: uuid.UUID | None = Form(default=None),
) -> DataResponse[DocumentOut]:
    data = await file.read()
    document = await documents.upload_document(
        session,
        actor=actor,
        staff_user_id=staff_user_id,
        document_type=document_type,
        data=data,
        filename=file.filename or "upload",
        declared_content_type=file.content_type or "application/octet-stream",
        issue_date=issue_date,
        expiry_date=expiry_date,
        replaces_document_id=replaces_document_id,
    )
    return DataResponse(data=DocumentOut.model_validate(document), meta=request_meta(request))


@router.get("/documents")
async def list_documents(
    request: Request,
    staff_user_id: uuid.UUID = Query(...),
    _actor: StaffUser = Depends(require_permission("staff.documents.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[DocumentOut]]:
    rows = await documents.list_documents(session, staff_user_id)
    return DataResponse(
        data=[DocumentOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/documents/{document_id}/verify")
async def verify_document(
    document_id: uuid.UUID,
    payload: DocumentVerifyIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.documents.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[DocumentOut]:
    document = await session.get(StaffDocument, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Document not found.")
    result = await documents.verify_document(
        session, actor=actor, document=document, payload=payload
    )
    return DataResponse(data=DocumentOut.model_validate(result), meta=request_meta(request))


@router.get("/documents/{document_id}/signed-url")
async def get_document_signed_url(
    document_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.documents.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, str]]:
    document = await session.get(StaffDocument, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Document not found.")
    url = await documents.get_document_signed_url(document)
    # HR identity/employment documents are sensitive PII — CLAUDE.md section
    # 6.6 requires auditing "file access... when sensitive", and unlike the
    # upload/verify actions on this same record, granting read access here
    # previously left no trail.
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="staff.document_accessed",
        target_type="staff_document",
        target_id=document.id,
        request=request,
        safe_metadata={
            "staff_user_id": str(document.staff_user_id),
            "document_type": document.document_type,
        },
    )
    return DataResponse(data={"signed_url": url}, meta=request_meta(request))


# --- Onboarding / offboarding --------------------------------------------


@router.post("/transition-templates", status_code=status.HTTP_201_CREATED)
async def create_transition_template(
    payload: TransitionTemplateCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.onboarding.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TransitionTemplateOut]:
    result = await transitions.create_template(session, actor=actor, payload=payload)
    return DataResponse(
        data=TransitionTemplateOut.model_validate(result), meta=request_meta(request)
    )


@router.post("/transition-templates/{template_id}/steps", status_code=status.HTTP_201_CREATED)
async def add_transition_template_step(
    template_id: uuid.UUID,
    payload: TransitionTemplateStepCreateIn,
    request: Request,
    _actor: StaffUser = Depends(require_permission("staff.onboarding.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, str]]:
    template = await session.get(StaffTransitionTemplate, template_id)
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Template not found.")
    await transitions.add_template_step(session, template=template, payload=payload)
    return DataResponse(data={"status": "ok"}, meta=request_meta(request))


@router.get("/transition-templates")
async def list_transition_templates(
    request: Request,
    transition_type: str | None = Query(default=None),
    _actor: StaffUser = Depends(require_permission("staff.onboarding.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[TransitionTemplateOut]]:
    rows = await transitions.list_templates(session, transition_type)
    return DataResponse(
        data=[TransitionTemplateOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/transition-plans", status_code=status.HTTP_201_CREATED)
async def create_transition_plan(
    payload: TransitionPlanCreateIn,
    request: Request,
    session: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(require_permission("staff.onboarding.view")),
) -> DataResponse[TransitionPlanOut]:
    required_permission = (
        "staff.onboarding.manage"
        if payload.transition_type == "onboarding"
        else "staff.offboarding.manage"
    )
    if not await has_permission(session, actor.id, required_permission):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Not authorized for this transition type."
        )
    result = await transitions.create_plan(session, actor=actor, payload=payload)
    return DataResponse(data=TransitionPlanOut.model_validate(result), meta=request_meta(request))


@router.get("/transition-plans/{plan_id}/steps")
async def list_transition_plan_steps(
    plan_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("staff.onboarding.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[TransitionStepOut]]:
    rows = await transitions.list_plan_steps(session, plan_id)
    return DataResponse(
        data=[TransitionStepOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/transition-steps/{step_id}/complete")
async def complete_transition_step(
    step_id: uuid.UUID,
    payload: TransitionStepCompleteIn,
    request: Request,
    actor: CurrentStaffUser,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TransitionStepOut]:
    step = await session.get(StaffTransitionStep, step_id)
    if step is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Step not found.")
    plan = await session.get(StaffTransitionPlan, step.plan_id)
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Plan not found.")
    await _require_self_or_permission(
        session,
        actor=actor,
        target_staff_id=plan.staff_user_id,
        permission_code="staff.onboarding.manage",
    )
    result = await transitions.complete_step(
        session, actor=actor, step=step, completion_evidence=payload.completion_evidence
    )
    return DataResponse(data=TransitionStepOut.model_validate(result), meta=request_meta(request))


@router.post("/transition-steps/{step_id}/approve")
async def approve_transition_step(
    step_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.onboarding.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TransitionStepOut]:
    step = await session.get(StaffTransitionStep, step_id)
    if step is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Step not found.")
    result = await transitions.approve_step(session, actor=actor, step=step)
    return DataResponse(data=TransitionStepOut.model_validate(result), meta=request_meta(request))


# --- Shifts -------------------------------------------------------------


@router.post("/shift-templates", status_code=status.HTTP_201_CREATED)
async def create_shift_template(
    payload: ShiftTemplateCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.shifts.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ShiftTemplateOut]:
    result = await shifts.create_shift_template(session, actor=actor, payload=payload)
    return DataResponse(data=ShiftTemplateOut.model_validate(result), meta=request_meta(request))


@router.get("/shift-templates")
async def list_shift_templates(
    request: Request,
    _actor: StaffUser = Depends(require_permission("staff.shifts.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[ShiftTemplateOut]]:
    rows = await shifts.list_shift_templates(session)
    return DataResponse(
        data=[ShiftTemplateOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/shifts", status_code=status.HTTP_201_CREATED)
async def create_shift(
    payload: StaffShiftCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.shifts.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StaffShiftOut]:
    result = await shifts.create_shift(session, actor=actor, payload=payload)
    return DataResponse(data=StaffShiftOut.model_validate(result), meta=request_meta(request))


@router.patch("/shifts/{shift_id}")
async def update_shift(
    shift_id: uuid.UUID,
    payload: StaffShiftUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.shifts.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StaffShiftOut]:
    shift = await session.get(StaffShift, shift_id)
    if shift is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Shift not found.")
    result = await shifts.update_shift(session, actor=actor, shift=shift, payload=payload)
    return DataResponse(data=StaffShiftOut.model_validate(result), meta=request_meta(request))


@router.post("/shifts/{shift_id}/publish")
async def publish_shift(
    shift_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.shifts.publish")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StaffShiftOut]:
    shift = await session.get(StaffShift, shift_id)
    if shift is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Shift not found.")
    result = await shifts.publish_shift(session, actor=actor, shift=shift)
    return DataResponse(data=StaffShiftOut.model_validate(result), meta=request_meta(request))


@router.get("/shifts")
async def list_shifts(
    request: Request,
    staff_user_id: uuid.UUID | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    _actor: StaffUser = Depends(require_permission("staff.shifts.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[StaffShiftOut]]:
    rows = await shifts.list_shifts(
        session, staff_user_id=staff_user_id, start_date=start_date, end_date=end_date
    )
    return DataResponse(
        data=[StaffShiftOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/shift-change-requests", status_code=status.HTTP_201_CREATED)
async def create_shift_change_request(
    payload: ShiftChangeRequestCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.shift_changes.request")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ShiftChangeRequestOut]:
    result = await shifts.create_change_request(session, actor=actor, payload=payload)
    return DataResponse(
        data=ShiftChangeRequestOut.model_validate(result), meta=request_meta(request)
    )


@router.post("/shift-change-requests/{request_id}/decide")
async def decide_shift_change_request(
    request_id: uuid.UUID,
    payload: ShiftChangeDecisionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.shift_changes.approve")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ShiftChangeRequestOut]:
    change_request = await session.get(ShiftChangeRequest, request_id)
    if change_request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Request not found.")
    result = await shifts.decide_change_request(
        session, actor=actor, request=change_request, payload=payload
    )
    return DataResponse(
        data=ShiftChangeRequestOut.model_validate(result), meta=request_meta(request)
    )


@router.get("/shift-change-requests")
async def list_shift_change_requests(
    request: Request,
    status_filter: str | None = Query(default=None, alias="status"),
    _actor: StaffUser = Depends(require_permission("staff.shifts.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[ShiftChangeRequestOut]]:
    rows = await shifts.list_change_requests(session, status_filter=status_filter)
    return DataResponse(
        data=[ShiftChangeRequestOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


# --- Attendance -----------------------------------------------------------


@router.post("/attendance", status_code=status.HTTP_201_CREATED)
async def record_attendance(
    payload: AttendanceRecordCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.attendance.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AttendanceRecordOut]:
    result = await attendance.record_attendance(session, actor=actor, payload=payload)
    return DataResponse(data=AttendanceRecordOut.model_validate(result), meta=request_meta(request))


@router.post("/attendance/{record_id}/correct")
async def correct_attendance(
    record_id: uuid.UUID,
    payload: AttendanceCorrectionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.attendance.correct")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AttendanceRecordOut]:
    record = await session.get(AttendanceRecord, record_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Attendance record not found.")
    result = await attendance.correct_attendance(
        session, actor=actor, record=record, payload=payload
    )
    return DataResponse(data=AttendanceRecordOut.model_validate(result), meta=request_meta(request))


@router.get("/attendance")
async def list_attendance(
    request: Request,
    staff_user_id: uuid.UUID | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    _actor: StaffUser = Depends(require_permission("staff.attendance.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[AttendanceRecordOut]]:
    rows = await attendance.list_attendance(
        session, staff_user_id=staff_user_id, start_date=start_date, end_date=end_date
    )
    return DataResponse(
        data=[AttendanceRecordOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


# --- Leave ---------------------------------------------------------------


@router.post("/leave-types", status_code=status.HTTP_201_CREATED)
async def create_leave_type(
    payload: LeaveTypeCreateIn,
    request: Request,
    _actor: StaffUser = Depends(require_permission("staff.leave.approve")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LeaveTypeOut]:
    result = await leave.create_leave_type(session, payload=payload)
    return DataResponse(data=LeaveTypeOut.model_validate(result), meta=request_meta(request))


@router.get("/leave-types")
async def list_leave_types(
    request: Request,
    _actor: StaffUser = Depends(require_permission("staff.leave.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[LeaveTypeOut]]:
    rows = await leave.list_leave_types(session)
    return DataResponse(
        data=[LeaveTypeOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/leave-requests", status_code=status.HTTP_201_CREATED)
async def submit_leave_request(
    payload: LeaveRequestCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.leave.request")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LeaveRequestOut]:
    result = await leave.submit_leave_request(session, actor=actor, payload=payload)
    return DataResponse(data=LeaveRequestOut.model_validate(result), meta=request_meta(request))


@router.post("/leave-requests/{leave_request_id}/decide")
async def decide_leave_request(
    leave_request_id: uuid.UUID,
    payload: LeaveDecisionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.leave.approve")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LeaveRequestOut]:
    leave_request = await session.get(LeaveRequest, leave_request_id)
    if leave_request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Leave request not found.")
    result = await leave.decide_leave_request(
        session, actor=actor, leave_request=leave_request, payload=payload
    )
    return DataResponse(data=LeaveRequestOut.model_validate(result), meta=request_meta(request))


@router.post("/leave-requests/{leave_request_id}/withdraw")
async def withdraw_leave_request(
    leave_request_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.leave.request")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LeaveRequestOut]:
    leave_request = await session.get(LeaveRequest, leave_request_id)
    if leave_request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Leave request not found.")
    await _require_self_or_permission(
        session,
        actor=actor,
        target_staff_id=leave_request.staff_user_id,
        permission_code="staff.leave.approve",
    )
    result = await leave.withdraw_leave_request(session, actor=actor, leave_request=leave_request)
    return DataResponse(data=LeaveRequestOut.model_validate(result), meta=request_meta(request))


@router.get("/leave-requests")
async def list_leave_requests(
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.leave.request")),
    session: AsyncSession = Depends(get_db),
    staff_user_id: uuid.UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
) -> DataResponse[list[LeaveRequestOut]]:
    has_view_all = await has_permission(session, actor.id, "staff.leave.view")
    scoped_staff_id = staff_user_id if has_view_all else actor.id
    rows = await leave.list_leave_requests(
        session, staff_user_id=scoped_staff_id, status_filter=status_filter
    )
    return DataResponse(
        data=[LeaveRequestOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


# --- Training --------------------------------------------------------------


@router.post("/training/courses", status_code=status.HTTP_201_CREATED)
async def create_training_course(
    payload: TrainingCourseCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.training.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TrainingCourseOut]:
    result = await training.create_course(session, actor=actor, payload=payload)
    return DataResponse(data=TrainingCourseOut.model_validate(result), meta=request_meta(request))


@router.get("/training/courses")
async def list_training_courses(
    request: Request,
    _actor: StaffUser = Depends(require_permission("staff.training.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[TrainingCourseOut]]:
    rows = await training.list_courses(session)
    return DataResponse(
        data=[TrainingCourseOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/training/assignments", status_code=status.HTTP_201_CREATED)
async def assign_training(
    payload: TrainingAssignIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.training.assign")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TrainingAssignmentOut]:
    result = await training.assign_training(session, actor=actor, payload=payload)
    return DataResponse(
        data=TrainingAssignmentOut.model_validate(result), meta=request_meta(request)
    )


@router.get("/training/assignments")
async def list_training_assignments(
    request: Request,
    staff_user_id: uuid.UUID | None = Query(default=None),
    course_id: uuid.UUID | None = Query(default=None),
    _actor: StaffUser = Depends(require_permission("staff.training.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[TrainingAssignmentOut]]:
    rows = await training.list_assignments(
        session, staff_user_id=staff_user_id, course_id=course_id
    )
    return DataResponse(
        data=[TrainingAssignmentOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/training/assignments/{assignment_id}/attempts", status_code=status.HTTP_201_CREATED)
async def start_training_attempt(
    assignment_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.training.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TrainingAttemptOut]:
    assignment = await session.get(TrainingAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
    await _require_self_or_permission(
        session,
        actor=actor,
        target_staff_id=assignment.staff_user_id,
        permission_code="staff.training.manage",
    )
    result = await training.start_attempt(session, assignment=assignment)
    return DataResponse(data=TrainingAttemptOut.model_validate(result), meta=request_meta(request))


@router.post("/training/attempts/{attempt_id}/complete")
async def complete_training_attempt(
    attempt_id: uuid.UUID,
    payload: TrainingAttemptCompleteIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.training.review")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TrainingAttemptOut]:
    attempt = await session.get(TrainingAttempt, attempt_id)
    if attempt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Attempt not found.")
    assignment = await session.get(TrainingAssignment, attempt.assignment_id)
    if assignment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
    result = await training.complete_attempt(
        session, actor=actor, attempt=attempt, assignment=assignment, payload=payload
    )
    return DataResponse(data=TrainingAttemptOut.model_validate(result), meta=request_meta(request))


@router.get("/training/assignments/{assignment_id}/attempts")
async def list_training_attempts(
    assignment_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("staff.training.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[TrainingAttemptOut]]:
    rows = await training.list_attempts(session, assignment_id)
    return DataResponse(
        data=[TrainingAttemptOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


# --- Certifications ---------------------------------------------------------


@router.post("/certifications", status_code=status.HTTP_201_CREATED)
async def create_certification(
    payload: CertificationCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.certifications.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CertificationOut]:
    result = await certifications.create_certification(session, actor=actor, payload=payload)
    return DataResponse(data=CertificationOut.model_validate(result), meta=request_meta(request))


@router.post("/certifications/{certification_id}/verify")
async def verify_certification(
    certification_id: uuid.UUID,
    payload: CertificationVerifyIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.certifications.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CertificationOut]:
    certification = await session.get(StaffCertification, certification_id)
    if certification is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Certification not found.")
    result = await certifications.verify_certification(
        session, actor=actor, certification=certification, payload=payload
    )
    return DataResponse(data=CertificationOut.model_validate(result), meta=request_meta(request))


@router.get("/certifications")
async def list_certifications(
    request: Request,
    staff_user_id: uuid.UUID | None = Query(default=None),
    _actor: StaffUser = Depends(require_permission("staff.certifications.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[CertificationOut]]:
    rows = await certifications.list_certifications(session, staff_user_id)
    return DataResponse(
        data=[CertificationOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


# --- Skills --------------------------------------------------------------


@router.post("/skills", status_code=status.HTTP_201_CREATED)
async def create_skill(
    payload: SkillCreateIn,
    request: Request,
    _actor: StaffUser = Depends(require_permission("staff.skills.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[SkillOut]:
    result = await skills.create_skill(session, payload)
    return DataResponse(data=SkillOut.model_validate(result), meta=request_meta(request))


@router.get("/skills")
async def list_skills(
    request: Request,
    _actor: StaffUser = Depends(require_permission("staff.skills.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[SkillOut]]:
    rows = await skills.list_skills(session)
    return DataResponse(data=[SkillOut.model_validate(r) for r in rows], meta=request_meta(request))


@router.put("/staff-skills/{staff_user_id}")
async def set_staff_skill(
    staff_user_id: uuid.UUID,
    payload: StaffSkillSetIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.skills.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StaffSkillOut]:
    result = await skills.set_staff_skill(
        session, actor=actor, staff_user_id=staff_user_id, payload=payload
    )
    return DataResponse(data=StaffSkillOut.model_validate(result), meta=request_meta(request))


@router.post("/staff-skills/{staff_skill_id}/verify")
async def verify_staff_skill(
    staff_skill_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.skills.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StaffSkillOut]:
    staff_skill = await session.get(StaffSkill, staff_skill_id)
    if staff_skill is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Staff skill not found.")
    result = await skills.verify_staff_skill(
        session, actor=actor, staff_skill=staff_skill, is_verified=True
    )
    return DataResponse(data=StaffSkillOut.model_validate(result), meta=request_meta(request))


@router.get("/staff-skills/{staff_user_id}")
async def list_staff_skills(
    staff_user_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("staff.skills.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[StaffSkillOut]]:
    rows = await skills.list_staff_skills(session, staff_user_id)
    return DataResponse(
        data=[StaffSkillOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


# --- Performance reviews -----------------------------------------------


@router.post("/reviews", status_code=status.HTTP_201_CREATED)
async def create_review(
    payload: PerformanceReviewCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.reviews.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[PerformanceReviewOut]:
    result = await reviews.create_review(session, actor=actor, payload=payload)
    return DataResponse(
        data=PerformanceReviewOut.model_validate(result), meta=request_meta(request)
    )


@router.patch("/reviews/{review_id}")
async def update_review(
    review_id: uuid.UUID,
    payload: PerformanceReviewUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.reviews.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[PerformanceReviewOut]:
    review = await session.get(PerformanceReview, review_id)
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Review not found.")
    result = await reviews.update_review(session, actor=actor, review=review, payload=payload)
    return DataResponse(
        data=PerformanceReviewOut.model_validate(result), meta=request_meta(request)
    )


@router.post("/reviews/{review_id}/transition")
async def transition_review(
    review_id: uuid.UUID,
    payload: PerformanceReviewTransitionIn,
    request: Request,
    actor: CurrentStaffUser,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[PerformanceReviewOut]:
    review = await session.get(PerformanceReview, review_id)
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Review not found.")
    if payload.target_status == "acknowledged":
        await _require_self_or_permission(
            session,
            actor=actor,
            target_staff_id=review.staff_user_id,
            permission_code="staff.reviews.manage",
        )
    elif not await has_permission(session, actor.id, "staff.reviews.manage"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not authorized for this transition.")
    result = await reviews.transition_review(
        session, actor=actor, review=review, target_status=payload.target_status
    )
    return DataResponse(
        data=PerformanceReviewOut.model_validate(result), meta=request_meta(request)
    )


@router.get("/reviews")
async def list_reviews(
    request: Request,
    actor: CurrentStaffUser,
    session: AsyncSession = Depends(get_db),
    staff_user_id: uuid.UUID | None = Query(default=None),
) -> DataResponse[list[PerformanceReviewOut]]:
    has_manage = await has_permission(session, actor.id, "staff.reviews.manage")
    scoped_staff_id = staff_user_id if has_manage else actor.id
    rows = await reviews.list_reviews(session, scoped_staff_id)
    return DataResponse(
        data=[PerformanceReviewOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


# --- Disciplinary ------------------------------------------------------


@router.post("/disciplinary-records", status_code=status.HTTP_201_CREATED)
async def create_disciplinary_record(
    payload: DisciplinaryRecordCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("staff.disciplinary.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[DisciplinaryRecordOut]:
    result = await disciplinary.create_disciplinary_record(session, actor=actor, payload=payload)
    return DataResponse(
        data=DisciplinaryRecordOut.model_validate(result), meta=request_meta(request)
    )


@router.post("/disciplinary-records/{record_id}/resolve")
async def resolve_disciplinary_record(
    record_id: uuid.UUID,
    resolution_status: str,
    request: Request,
    _actor: StaffUser = Depends(require_permission("staff.disciplinary.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[DisciplinaryRecordOut]:
    record = await session.get(StaffDisciplinaryRecord, record_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Record not found.")
    result = await disciplinary.resolve_disciplinary_record(
        session, record=record, resolution_status=resolution_status
    )
    return DataResponse(
        data=DisciplinaryRecordOut.model_validate(result), meta=request_meta(request)
    )


@router.get("/disciplinary-records")
async def list_disciplinary_records(
    request: Request,
    staff_user_id: uuid.UUID = Query(...),
    _actor: StaffUser = Depends(require_permission("staff.disciplinary.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[DisciplinaryRecordOut]]:
    rows = await disciplinary.list_disciplinary_records(session, staff_user_id)
    return DataResponse(
        data=[DisciplinaryRecordOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


# --- Availability --------------------------------------------------------


@router.post("/availability/{staff_user_id}", status_code=status.HTTP_201_CREATED)
async def create_availability_window(
    staff_user_id: uuid.UUID,
    payload: AvailabilityWindowCreateIn,
    request: Request,
    actor: CurrentStaffUser,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AvailabilityWindowOut]:
    await _require_self_or_permission(
        session,
        actor=actor,
        target_staff_id=staff_user_id,
        permission_code="staff.availability.manage",
    )
    result = await availability.create_availability_window(
        session, actor=actor, staff_user_id=staff_user_id, payload=payload
    )
    return DataResponse(
        data=AvailabilityWindowOut.model_validate(result), meta=request_meta(request)
    )


@router.get("/availability/{staff_user_id}")
async def list_availability_windows(
    staff_user_id: uuid.UUID,
    request: Request,
    actor: CurrentStaffUser,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[AvailabilityWindowOut]]:
    await _require_self_or_permission(
        session,
        actor=actor,
        target_staff_id=staff_user_id,
        permission_code="staff.availability.view",
    )
    rows = await availability.list_availability_windows(session, staff_user_id)
    return DataResponse(
        data=[AvailabilityWindowOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


# --- Analytics -----------------------------------------------------------


@router.get("/analytics")
async def staff_analytics(
    request: Request,
    _actor: StaffUser = Depends(require_permission("staff.analytics.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StaffAnalyticsOut]:
    data = await analytics.get_staff_analytics(session)
    return DataResponse(data=StaffAnalyticsOut.model_validate(data), meta=request_meta(request))
