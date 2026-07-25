# RKPR RESTAURANT CRM — OPERATIONS MODULES

## 1. DOCUMENT PURPOSE

This document defines the complete product behavior, operational workflows, permissions, data presentation, automation rules, validation, failure handling, reporting, and acceptance criteria for the RKPR Restaurant CRM operational modules.

It must remain fully consistent with `CLAUDE.md`, `PROJECT_PLAN.md`, `ARCHITECTURE_AND_TECH_STACK.md`, `DATABASE_AND_API.md`, and `CORE_CRM_MODULES.md`.

The operational modules covered here are:

1. Communication Hub
2. Lightweight Knowledge Base
3. Staff & HR
4. Operational Tasks, Notifications, and Cross-Module Coordination

This document is product-authoritative for these modules. It defines what users can see and do, how records move through their lifecycle, what data must be captured, which actions require approval, what is automated, and how operational failures are surfaced.

Dummy data must remain identical to prior documents. Dummy information is allowed only for seed fixtures such as staff examples, customer conversations, sample FAQs, training records, shift plans, tasks, and notifications. Architecture, providers, security, libraries, API contracts, deployment, and business-critical decisions are never dummy.

## 2. GLOBAL OPERATIONS RULES

### 2.1 Fast interaction

- All list screens use server-side pagination.
- Search is debounced and server-side.
- Conversation, article, staff, shift, and task views must not load the entire dataset into the browser.
- Secondary tabs lazy-load.
- Realtime updates patch only the visible record or queue.
- Large exports, imports, message sends, report generation, and bulk actions run asynchronously in the ARQ worker.
- One failed provider or background job must not block ordinary CRM navigation.
- Loading, empty, stale, conflict, offline, and error states must exist for every major screen.

### 2.2 Security and permissions

- Backend permission checks are authoritative, using the single canonical capability registry defined in `DATABASE_AND_API.md` §4.4.
- UI visibility is not treated as security.
- Sensitive staff, salary, leave, disciplinary, authentication, and customer communication data must be restricted by explicit permission.
- Messages, attachments, staff documents, and internal notes are private by default.
- Every sensitive action must be audited.
- External provider payloads, tokens, secrets, and credentials must never be shown in ordinary product screens.
- Record-detail routes must be protected against insecure direct object reference.

### 2.3 Data consistency

- Statuses and transitions must match `DATABASE_AND_API.md`.
- No UI may invent statuses unavailable to the backend.
- Every outbound message must retain channel, recipient, template or free-text source, consent basis, provider reference, delivery status, retry count, actor, and timestamps.
- Staff employment and access state must remain separate.
- Knowledge Base content is lightweight and structured. No embeddings, pgvector, semantic search, or RAG are permitted.
- Operational tasks must preserve assignment, priority, due time, completion evidence, linked records, and audit history.

### 2.4 Shared page patterns

Where applicable, each module uses:

- Page title and concise operational subtitle
- Primary action button
- Search
- Filter bar or filter drawer
- Saved views
- Summary metrics
- Main table, inbox, board, calendar, or queue
- Bulk-action toolbar only after selection
- Dedicated record detail view or side panel
- Activity timeline
- Empty state with a meaningful action
- Error state with retry and request ID
- Permission-denied state without protected content leakage

## 3. COMMUNICATION HUB MODULE

### 3.1 Purpose

The Communication Hub centralizes customer-facing and internal operational communication across supported channels. It is designed for fast handling of order questions, reservation requests, lead follow-ups, complaints, feedback, corporate enquiries, and service recovery.

The Communication Hub is not a generic omnichannel platform. It exists specifically to support RKPR Restaurant CRM workflows.

### 3.2 Supported channels

Supported channel values must remain stable and provider-neutral:

- website_chat
- whatsapp
- email
- sms
- phone_log
- internal_note
- system_notification

A channel may appear in the UI only when the corresponding integration or manual workflow is actually available.

### 3.3 Conversation statuses

- open
- pending_customer
- pending_staff
- pending_external
- escalated
- resolved
- closed
- spam
- failed

### 3.4 Conversation priorities

- low
- normal
- high
- urgent

Priority may be set manually or suggested by rules. AI may recommend priority but cannot silently change it.

### 3.5 Conversation types

- general_enquiry
- order_support
- reservation
- lead
- complaint
- feedback
- corporate_enquiry
- loyalty
- supplier
- internal_operations

### 3.6 Inbox layout

The Communication Hub must use a three-panel desktop layout where space permits:

1. Queue and saved views
2. Conversation list
3. Active conversation

On tablets and mobile devices, panels become separate navigable screens.

### 3.7 Default queues

- All open
- Mine
- Unassigned
- Waiting for staff
- Waiting for customer
- Escalated
- Complaints
- Reservation requests
- Order support
- Leads
- Failed outbound messages
- Closed recently

### 3.8 Conversation list fields

Each row displays:

- customer or guest name
- organization where relevant
- channel
- conversation type
- latest message preview
- unread count
- status
- priority
- assigned staff
- linked order, reservation, lead, or complaint indicator
- last activity time
- SLA state

### 3.9 Conversation search

Search supports:

- customer name
- organization
- phone
- email
- conversation number
- order number
- reservation number
- lead number
- message text where supported by indexed full-text search

Search must respect permissions and must not expose hidden conversations.

### 3.10 Conversation filters

- channel
- status
- priority
- type
- assigned staff
- team
- unread state
- SLA state
- date range
- linked record type
- customer segment
- complaint severity
- failed delivery state

### 3.11 Conversation header

Displays:

- customer or guest identity
- customer segment
- preferred language
- contact details
- consent indicators
- conversation status
- priority
- assigned staff
- linked records
- current SLA state
- customer warning flags where permitted

Primary actions:

- Assign
- Change status
- Change priority
- Add internal note
- Link record
- Create lead
- Create customer
- Create reservation request
- Create assisted order
- Create complaint
- Resolve
- Close

### 3.12 Message presentation

Each message shows:

- sender identity
- direction
- channel
- timestamp in `Asia/Kolkata`
- delivery state
- edited indicator where supported
- attachment indicator
- reply relationship where supported
- provider failure state when applicable

Delivery statuses:

- draft
- queued
- sending
- sent
- delivered
- read
- failed
- retrying
- cancelled

### 3.13 Outbound message workflow

1. User opens a conversation.
2. System verifies recipient and active channel.
3. System checks consent or lawful operational basis.
4. User selects template or writes a message.
5. System validates length, variables, attachments, and prohibited content.
6. User previews the final message.
7. Message is queued.
8. Background worker (ARQ) sends through the configured provider.
9. Provider reference and delivery events are stored.
10. Failures retry according to policy.
11. Permanent failure creates an actionable alert.

### 3.14 Consent-aware communication

Marketing communication must require current consent at send time.

Transactional or operational communication may use the relevant service basis, including:

- order confirmation
- payment status
- preparation update
- delivery update
- reservation confirmation
- reservation reminder
- complaint follow-up
- account or loyalty service message

A marketing template cannot be sent under a transactional classification.

### 3.15 Templates

Template categories:

- order_confirmation
- order_delay
- order_ready
- delivery_update
- payment_failed
- refund_update
- reservation_confirmation
- reservation_reminder
- reservation_change
- reservation_rejection
- lead_follow_up
- proposal_shared
- complaint_acknowledgement
- complaint_resolution
- feedback_request
- loyalty_update
- campaign

Template fields:

- code
- name
- channel
- category
- language
- content
- variables
- active state
- approval state
- provider template reference where required
- version
- created by
- updated by

### 3.16 Template variables

Allowed variables must be explicitly defined, such as:

- customer_name
- order_number
- order_status
- order_total
- reservation_number
- reservation_date
- reservation_time
- guest_count
- lead_number
- staff_name
- restaurant_name
- support_phone

Unknown variables must block publication.

### 3.17 Internal notes

Internal notes:

- are never sent to customers
- use a visually distinct style
- record author and timestamp
- may mention staff users
- may link orders, reservations, leads, complaints, or tasks
- may be restricted by note type
- must not expose secrets or raw provider payloads

### 3.18 Assignment workflow

A conversation may be assigned to:

- individual staff user
- team queue

Assignment changes must record:

- previous assignee
- new assignee
- actor
- reason where required
- timestamp

Auto-assignment may use deterministic rules such as channel, conversation type, active shift, or team availability. It must not depend on opaque AI decisions.

### 3.19 SLA handling

SLA metrics may include:

- first response due
- next response due
- resolution target
- overdue state

SLA calculation must pause or continue according to explicit status rules. `pending_customer` may pause response SLA when configured.

### 3.20 Escalation workflow

Escalation reasons:

- high severity complaint
- payment dispute
- refund request
- repeated failed response
- VIP customer issue
- legal or safety concern
- large corporate enquiry
- unresolved reservation conflict

Escalation must:

- assign or notify the appropriate manager
- change priority where authorized
- preserve original assignee history
- create an audit event
- remain visible until acknowledged

### 3.21 Conversation linking

A conversation may link to:

- customer
- lead
- order
- reservation
- complaint
- feedback record
- campaign
- loyalty account
- supplier
- staff task

Linking must not duplicate downstream records.

### 3.22 Attachments

Attachment requirements:

- validate type and size
- scan uploads
- store privately
- generate safe previews where supported
- use short-lived signed URLs
- preserve filename, MIME type, size, uploader, and timestamps
- restrict download by permission

Examples:

- payment proof
- order photograph
- complaint photograph
- proposal PDF
- corporate purchase order
- supplier invoice

### 3.23 Communication AI support

Allowed advisory features (available only from Phase 14 onward, once AI is credentialed):

- summarize long conversations
- suggest reply drafts
- identify unresolved questions
- recommend next action
- classify likely conversation type
- detect urgent language
- summarize complaint history

Requirements:

- clearly label AI-generated content
- ground suggestions in visible CRM data
- never send automatically
- never fabricate order, payment, reservation, policy, or refund information
- require explicit user review

### 3.24 Dummy communication fixtures

Development fixtures must stay consistent with prior documents:

- Ananya Rao asking whether Paneer Tikka Pizza can be prepared extra spicy
- Rahul Mehta following up on a delayed delivery order
- Shreya Kulkarni asking for Jain preparation on Jain Aloo Crunch Burger
- BrightWave Technologies requesting a recurring corporate lunch proposal

These are seed fixtures only.

### 3.25 Bulk actions

Allowed where permission exists:

- assign staff
- change team queue
- add tag
- mark read
- close eligible conversations
- export metadata

Bulk outbound messaging is handled through approved campaign or notification jobs, not ordinary inbox bulk actions.

### 3.26 Communication edge cases

- duplicate provider webhook
- message delivered after local timeout
- customer replies from a different phone
- conversation linked to merged customer
- staff disabled while assigned
- attachment scan failure
- provider template rejected
- withdrawn marketing consent before send
- retry after partial provider success
- two agents reply simultaneously
- message arrives after conversation closure

### 3.27 Communication acceptance criteria

- delivery events are idempotent
- consent is checked at send time
- internal notes never reach external channels
- permissions protect conversation access
- assignment history is preserved
- failed sends are visible and retryable
- linked records are accurate
- AI drafts remain advisory
- inbox remains fast with large message volume

## 4. LIGHTWEIGHT KNOWLEDGE BASE MODULE

### 4.1 Purpose

The Knowledge Base stores approved operational information for staff reference and consistent customer communication.

It is intentionally lightweight. It does not use embeddings, vector search, semantic retrieval, pgvector, or RAG.

### 4.2 Content types

- faq
- policy
- process
- menu_note
- reservation_note
- customer_service_script
- supplier_process
- staff_guide
- troubleshooting

### 4.3 Article statuses

- draft
- in_review
- approved
- published
- archived

### 4.4 Article fields

- article number
- title
- slug
- content type
- category
- summary
- body
- keywords
- audience
- status
- owner
- reviewer
- version
- effective date where applicable
- expiry or review date where applicable
- created time
- updated time
- published time

### 4.5 Categories

Seed categories may include:

- Restaurant Information
- Menu and Dietary Guidance
- Orders and Delivery
- Reservations
- Payments and Refunds
- Loyalty
- Complaints and Service Recovery
- Corporate Orders
- Staff Operations
- Supplier Operations

### 4.6 Search behavior

Search uses:

- exact title match
- keyword match
- database full-text search
- category filters
- status filters
- audience filters

No semantic search is permitted.

### 4.7 Article list page

Columns:

- article number
- title
- type
- category
- status
- audience
- owner
- reviewer
- version
- last updated
- review due

### 4.8 Article detail

Sections:

- title and summary
- current status
- owner and reviewer
- audience
- content body
- keywords
- linked templates or processes
- revision history
- publication history
- audit history

### 4.9 Authoring workflow

1. Create draft.
2. Enter title, type, category, audience, and content.
3. Add keywords.
4. Assign reviewer.
5. Submit for review.
6. Reviewer approves or requests changes.
7. Publish approved version.
8. Schedule review date where needed.
9. Archive superseded content.

### 4.10 Versioning

- Every published change creates a new version.
- Historical versions remain readable to authorized users.
- Published content cannot be silently overwritten.
- Reverting creates another version rather than deleting history.

### 4.11 Audience controls

Audience values may include:

- all_staff
- managers
- customer_support
- kitchen
- inventory
- reservations
- marketing
- finance
- hr

The backend must enforce audience access.

### 4.12 Knowledge Base approval rules

Approval is required for:

- refund policy
- cancellation policy
- reservation policy
- allergy or dietary guidance
- payment instructions
- corporate pricing guidance
- complaint recovery scripts
- staff-sensitive procedures

### 4.13 Dummy article fixtures

Examples consistent with the RKPR restaurant context:

- "RKPR Restaurant Opening Hours and Contact Details"
- "How to Handle Jain Preparation Requests"
- "Reservation Request Review Checklist"
- "Delayed Order Customer Communication Script"
- "Inventory Receipt and Batch Recording Process"
- "BrightWave Technologies Corporate Lunch Handling Notes"

Seed content must not invent providers, laws, or policies that were not approved elsewhere.

### 4.14 Knowledge Base links

Articles may link to:

- communication templates
- menu products
- reservation workflows
- complaint workflows
- staff training records
- supplier procedures
- operational tasks

### 4.15 Review reminders

The system may generate reminders for:

- review due soon
- expired policy
- draft inactive too long
- approved article not published
- article linked to inactive product or workflow

### 4.16 Knowledge Base AI support

Allowed advisory features (available only from Phase 14 onward, once AI is credentialed):

- grammar improvement
- summarization
- suggested keywords
- draft structure
- duplicate-topic warning

AI must not publish content or create policy facts automatically.

### 4.17 Import and export

- controlled article import with preview
- validation of title, type, category, status, and audience
- duplicate detection
- export of selected articles and metadata
- private export files
- audit logging

### 4.18 Knowledge Base edge cases

- duplicate slug
- article references archived product
- reviewer disabled
- publication during concurrent edit
- expired article still linked to template
- unauthorized audience access
- article restored from historical version
- missing approval for sensitive policy

### 4.19 Knowledge Base acceptance criteria

- no embeddings, vector search, pgvector, or RAG
- search is database-backed and bounded
- published versions are immutable
- audience permissions are enforced
- sensitive policies require approval
- review reminders work
- dummy content remains isolated from production

## 5. STAFF & HR MODULE

### 5.1 Purpose

The Staff & HR module manages staff profiles, departments, roles, schedules, attendance references, leave, training, documents, performance notes, operational assignments, and system access relationships.

It is not a payroll system unless payroll is separately approved and implemented.

### 5.2 Staff departments

Approved department examples:

- Management
- Operations
- Kitchen
- Front of House
- Customer Support
- Reservations
- Inventory and Procurement
- Finance
- Marketing
- Human Resources
- Delivery Coordination

### 5.3 Employment statuses

- active
- probation
- on_leave
- suspended
- notice_period
- inactive
- terminated

### 5.4 System access statuses

- invited
- active
- locked
- disabled
- expired

Employment status and system access status must remain separate.

### 5.5 Staff list page

Columns:

- employee number
- name
- department
- job title
- manager
- employment status
- access status
- phone
- email
- shift today
- open tasks
- training state
- joined date

### 5.6 Staff search and filters

Search:

- employee number
- name
- phone
- email
- job title

Filters:

- department
- employment status
- access status
- manager
- role
- shift state
- training state
- leave state
- joined-date range

### 5.7 Staff profile header

Displays:

- employee number
- full name
- preferred name
- job title
- department
- manager
- employment status
- access status
- current shift state
- contact details
- role summary

Primary actions depend on permission:

- Edit profile
- Assign manager
- Change department
- Manage role
- Schedule shift
- Record leave
- Add training
- Add document
- Add performance note
- Disable access
- Archive staff record

### 5.8 Staff profile tabs

#### Overview

- identity
- contact details
- emergency contact
- department and role
- reporting manager
- employment dates
- status
- current assignments

#### Schedule

- upcoming shifts
- completed shifts
- unavailability
- swaps
- overtime references where supported

#### Leave

- leave balances where configured
- requests
- approvals
- cancellations
- history

#### Training

- training modules
- completion state
- scores where applicable
- expiry dates
- certificates

#### Documents

- identity or employment documents
- offer or contract records
- training certificates
- policy acknowledgements

#### Performance

- goals
- manager notes
- recognition
- improvement plans
- review records

#### Access and Roles

- authentication identity
- roles
- permissions summary
- access state
- last login
- security events where permitted

#### Audit

Visible only with permission (`audit.view`).

### 5.9 Dummy staff consistency

Seed staff and role examples must remain consistent with `PROJECT_PLAN.md`, including the previously established RKPR management, operations, kitchen, inventory, reservation, marketing, finance, customer support, and shift-supervision examples. The canonical dummy active-staff total is **65** (`PROJECT_PLAN.md` §4.2).

The corporate account example remains assigned to Nikhil Jain where referenced in prior documents.

No later document may create conflicting employee names, roles, or reporting lines.

### 5.10 Staff creation workflow

1. Create employee profile.
2. Assign employee number.
3. Enter identity and contact data.
4. Assign department and job title.
5. Assign manager.
6. Set employment status.
7. Add work location and schedule rules.
8. Add required documents.
9. Add initial training requirements.
10. Invite to system only when access is required.
11. Assign role and permission scope.
12. Audit profile and access creation.

### 5.11 Role and permission management

Roles must map to explicit permissions using the canonical capability registry.

Example role groups:

- Owner
- General Manager
- Operations Manager
- Finance Manager
- Kitchen Manager
- Inventory Manager
- Reservation Manager
- Marketing Manager
- HR Manager
- Shift Supervisor
- Customer Support Agent
- Kitchen Staff
- Inventory Staff
- Reservation Staff

Role assignment requirements:

- authorized actor
- effective time
- optional expiry
- reason for sensitive roles
- audit event

### 5.12 Shift statuses

- scheduled
- confirmed
- started
- completed
- missed
- cancelled
- swapped

### 5.13 Shift fields

- shift number
- staff member
- department
- role for shift
- start time
- end time
- location
- break plan
- status
- assigned by
- notes

### 5.14 Shift scheduling workflow

1. Select date range.
2. Review demand and staffing requirements.
3. Create or copy shift plan.
4. Assign eligible staff.
5. Validate overlapping shifts and approved leave.
6. Publish schedule.
7. Notify affected staff.
8. Track confirmations or conflicts.
9. Record changes and audit history.

### 5.15 Shift validation

- end time must be after start time
- overlapping shifts require explicit handling
- inactive or terminated staff cannot be scheduled
- approved leave must block conflicting assignment
- role requirements must be met
- critical operational roles should trigger understaffing alerts

### 5.16 Leave types

- casual
- sick
- earned
- unpaid
- emergency
- compensatory
- other

### 5.17 Leave statuses

- draft
- submitted
- pending_approval
- approved
- rejected
- cancelled

### 5.18 Leave workflow

1. Staff or manager creates request.
2. Dates and reason are entered.
3. Conflicts and balance rules are checked.
4. Request is submitted.
5. Authorized manager approves or rejects.
6. Approved leave blocks shift assignment.
7. Schedule owners are notified.
8. History remains available.

### 5.19 Training management

Training categories:

- food_safety
- customer_service
- order_operations
- reservation_handling
- inventory_receiving
- data_security
- complaint_resolution
- workplace_policy

Training statuses:

- assigned
- in_progress
- completed
- failed
- expired
- waived

### 5.20 Training fields

- training code
- title
- category
- description
- required roles
- assigned date
- due date
- completed date
- expiry date
- score
- certificate
- status

### 5.21 Staff documents

Document types may include:

- identity
- address
- contract
- offer_letter
- policy_acknowledgement
- training_certificate
- performance_record
- disciplinary_record
- medical_or_leave_support

All files must be private, permission-controlled, validated, scanned, and audited.

### 5.22 Performance notes

Performance data must be restricted.

Types:

- recognition
- coaching
- goal
- review
- warning
- improvement_plan

Performance notes must include author, date, type, summary, detail, visibility scope, and follow-up date where applicable.

### 5.23 Staff offboarding

1. Set final working date.
2. Transfer active tasks, conversations, leads, reservations, and approvals.
3. Remove or replace manager responsibilities.
4. Disable system access at the approved time.
5. Revoke active sessions.
6. Preserve audit and historical records.
7. Archive documents according to policy.
8. Mark employment status appropriately.

### 5.24 Staff access security

- no shared user accounts
- strong authentication
- session revocation
- least privilege
- permission review for sensitive roles
- disabled access blocks API and UI access
- role changes take effect consistently
- access events are audited

### 5.25 Staff reporting

- headcount by department
- active and inactive staff
- shift coverage
- unfilled shifts
- attendance references where available
- leave utilization
- training completion
- expiring training
- task completion
- access review report

### 5.26 Staff AI support

Allowed advisory features (available only from Phase 14 onward, once AI is credentialed):

- summarize non-sensitive workload
- identify scheduling conflicts
- suggest training reminders
- summarize task completion patterns

AI must not make hiring, firing, disciplinary, compensation, leave-approval, or access decisions.

### 5.27 Staff bulk actions

Allowed where permission exists:

- assign department
- assign manager
- assign training
- publish schedule notifications
- export non-sensitive directory data
- disable access through controlled workflow

Bulk termination, disciplinary action, and sensitive role assignment are not ordinary bulk actions.

### 5.28 Staff edge cases

- employment active but access disabled
- staff on leave with scheduled shift
- manager disabled
- duplicate work email
- expired training for critical role
- shift changed after notification
- offboarding with active approvals
- staff merged or duplicate profile attempt
- document scan failure
- role change during active session

### 5.29 Staff acceptance criteria

- employment and access states remain separate
- permissions are backend-enforced
- leave blocks conflicting shifts
- sensitive HR data is restricted
- offboarding transfers work and revokes access
- training expiry alerts work
- staff documents remain private
- role changes are audited

## 6. OPERATIONAL TASKS MODULE

### 6.1 Purpose

Operational tasks coordinate work across orders, reservations, leads, complaints, inventory, suppliers, staff, campaigns, and system issues.

Tasks are not a generic project-management replacement. They support daily restaurant operations.

### 6.2 Task statuses

- open
- in_progress
- blocked
- completed
- cancelled
- overdue

### 6.3 Task priorities

- low
- normal
- high
- urgent

### 6.4 Task types

- lead_follow_up
- reservation_review
- complaint_resolution
- refund_review
- inventory_count
- purchase_order_follow_up
- supplier_issue
- staff_training
- shift_coverage
- knowledge_review
- campaign_review
- integration_failure
- general_operations

### 6.5 Task fields

- task number
- title
- description
- type
- priority
- status
- assigned staff
- assigned team
- created by
- due time
- started time
- completed time
- linked record type
- linked record ID
- blocked reason
- completion note
- evidence attachment

### 6.6 Task list views

- My tasks
- Team tasks
- Due today
- Overdue
- High priority
- Blocked
- Completed recently
- Unassigned

### 6.7 Task creation sources

Tasks may be created:

- manually
- from a lead follow-up
- from a reservation review requirement
- from a complaint escalation
- from a refund request
- from critical inventory alert
- from supplier delay
- from training expiry
- from failed integration job
- from Knowledge Base review date

### 6.8 Task workflow

1. Task is created.
2. Assignee or team is selected.
3. Due time and priority are set.
4. Assignee acknowledges or starts task.
5. Blockers are recorded if needed.
6. Completion note or evidence is added.
7. Task is completed.
8. Linked record timeline is updated.

### 6.9 Task validation

- completed tasks require completion time
- blocked tasks require blocked reason
- sensitive task types require appropriate assignee permissions
- inactive staff cannot receive new tasks
- due time must be valid
- linked records must exist and be accessible

### 6.10 Recurring tasks

Allowed examples:

- daily opening checklist
- daily closing checklist
- weekly inventory cycle count
- monthly access review
- monthly supplier performance review
- policy review reminders

Recurring definitions must be explicit, auditable, and safe to update. Recurring task scheduling uses the ARQ scheduler.

### 6.11 Task notifications

Notify on:

- assignment
- reassignment
- due soon
- overdue
- blocked
- escalation
- completion where relevant

Notifications must be deduplicated and link directly to the task.

### 6.12 Task reporting

- open tasks by team
- overdue tasks
- average completion time
- completion rate
- blocked-task reasons
- tasks by source module
- workload by assignee

### 6.13 Task edge cases

- linked record deleted or archived
- assigned staff disabled
- duplicate automation task
- task completed after source condition cleared
- concurrent completion
- recurring task definition changed
- evidence upload failure

### 6.14 Task acceptance criteria

- every task has a clear owner or queue
- status transitions are validated
- recurring tasks do not duplicate
- overdue logic is accurate
- linked timelines update correctly
- sensitive tasks respect permissions

## 7. NOTIFICATIONS CENTER

### 7.1 Purpose

The Notifications Center surfaces actionable CRM events without replacing the underlying module queues.

### 7.2 Notification categories

- order
- reservation
- lead
- customer
- complaint
- inventory
- supplier
- staff
- task
- campaign
- knowledge
- integration
- security
- report

### 7.3 Notification fields

- notification ID
- category
- severity
- title
- body
- recipient user or role
- linked record
- created time
- read time
- acknowledged time
- resolved time
- deduplication key

### 7.4 Notification severities

- info
- warning
- high
- critical

### 7.5 Notification rules

- notify only authorized recipients
- deduplicate repeated conditions
- resolve when the source condition clears
- avoid repeated noisy alerts
- preserve critical security and audit events
- link to the exact record or filtered queue

### 7.6 Example notifications

- delayed order requires review
- reservation request pending
- high-value lead overdue
- critical mozzarella stock
- supplier delivery overdue
- food safety training expiring
- refund request awaiting approval
- failed outbound reservation confirmation
- Knowledge Base policy review due
- scheduled report generation failed

### 7.7 Notification acceptance criteria

- correct recipients
- correct link target
- no duplicate spam
- read and acknowledged states work
- cleared conditions resolve appropriately
- permission changes remove unauthorized access

## 8. CROSS-MODULE OPERATIONAL WORKFLOWS

### 8.1 Order support workflow

- customer contacts support
- conversation linked to order
- agent reviews order and payment timeline
- agent responds using verified data
- complaint or refund task created if needed
- resolution recorded
- customer timeline updated

### 8.2 Reservation communication workflow

- reservation request created
- pending-review notification generated
- staff reviews request
- approved reservation confirmation queued
- delivery events tracked
- communication failure creates task and alert
- reminder scheduled

### 8.3 Corporate lead workflow

- BrightWave Technologies lead created
- assigned to Nikhil Jain
- follow-up task created
- proposal communication logged
- lead converted to corporate customer and recurring order arrangement when approved
- all references preserved

### 8.4 Complaint recovery workflow

- complaint created from conversation, feedback, order, or reservation
- severity assessed
- manager notified for high severity
- recovery task assigned
- approved refund, discount, or loyalty adjustment performed through the correct module
- resolution message sent
- customer segment may update to complaint_recovery
- audit history preserved

### 8.5 Inventory incident workflow

- critical stock or supplier issue detected
- inventory manager notified
- task created
- affected products identified
- purchase order or supplier follow-up initiated
- availability override used only if authorized
- condition resolves when stock is received or issue closed

### 8.6 Staff absence workflow

- leave approved
- conflicting shifts identified
- shift-coverage task created
- manager and operations team notified
- replacement assigned
- published schedule updated
- notification history preserved

### 8.7 Knowledge review workflow

- policy review date approaches
- owner and reviewer notified
- review task created
- article updated and submitted
- reviewer approves
- new version published
- old version retained

## 9. OPERATIONAL REPORTING MATRIX

Communication Hub:

- conversation volume by channel
- first response time
- resolution time
- SLA compliance
- failed outbound messages
- complaint volume
- workload by agent

Knowledge Base:

- article count by status
- review due
- search terms with no result
- article usage
- outdated linked content

Staff & HR:

- headcount
- shift coverage
- leave
- training completion
- expiring documents or certifications
- access review

Tasks:

- overdue tasks
- completion time
- workload by team
- blocked reasons
- task source distribution

Notifications:

- volume by category
- unresolved critical alerts
- acknowledgement time
- duplicate suppression statistics

## 10. PERFORMANCE TARGETS

- Inbox list and task list endpoints return bounded responses.
- Conversation threads use cursor pagination.
- Message sending is asynchronous (ARQ).
- Attachment processing never blocks the page request.
- Knowledge search uses indexed database queries.
- Staff schedules load only the selected date range.
- Notification polling or realtime subscriptions remain scoped.
- Dashboard widgets use pre-aggregated endpoints where practical.
- Reconnect triggers authoritative re-fetch.

## 11. SECURITY TARGETS

- Every action maps to an explicit permission from the canonical capability registry.
- Sensitive HR and staff data is excluded by default.
- Customer communications respect consent and operational purpose.
- Files are private and scanned.
- Message provider events are verified and deduplicated.
- Staff access revocation blocks both UI and API.
- Internal notes cannot leak to external channels.
- Knowledge audience access is backend-enforced.
- Sensitive task and notification data is permission-controlled.

## 12. OPERATIONS MODULE DEFINITION OF DONE

An operations module is complete only when:

- behavior matches this document
- database and API behavior matches `DATABASE_AND_API.md`
- architecture matches `ARCHITECTURE_AND_TECH_STACK.md`
- security and coding rules match `CLAUDE.md`
- dummy seed data remains consistent with `PROJECT_PLAN.md`
- all list views are paginated
- permissions are tested
- loading, empty, error, stale-data, and conflict states exist
- status transitions are validated
- sensitive actions are audited
- primary workflows have automated tests
- cross-module links and timelines reconcile
- mobile and tablet behavior is usable
- no fake provider, integration, HR, or messaging capability is displayed as functional

## 13. FINAL OPERATIONS COMMAND

Build the RKPR operational modules as production-grade restaurant software, not static admin pages. Communication, knowledge, staff, tasks, and notifications must be fast, permission-aware, auditable, failure-tolerant, and consistent with the approved CRM architecture and data model. Preserve dummy information only as development fixtures. Never substitute dummy data for providers, tools, security, policy, permissions, financial behavior, deployment, or production decisions.
