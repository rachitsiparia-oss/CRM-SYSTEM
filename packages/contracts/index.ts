// Shared API contracts, error shapes, and pagination definitions —
// ARCHITECTURE_AND_TECH_STACK.md section 5.5. Backend types remain
// authoritative; this package must be refreshed through a documented
// process, not hand-duplicated ahead of the backend schema.

export type ErrorCode =
  | "validation_error"
  | "authentication_required"
  | "permission_denied"
  | "not_found"
  | "conflict"
  | "invalid_state_transition"
  | "rate_limited"
  | "external_dependency_unavailable"
  | "integration_configuration_error"
  | "retryable_processing_failure"
  | "internal_error";

export interface ApiErrorBody {
  error: {
    code: ErrorCode;
    message: string;
    field_errors?: Record<string, string[]>;
    request_id: string;
  };
}

export interface Meta {
  request_id: string;
}

export interface DataResponse<T> {
  data: T;
  meta: Meta;
}

export interface Pagination {
  page: number;
  page_size: number;
  total: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: Pagination;
  meta: Meta;
}

// --- Phase 3: Authentication, Users, Roles, and Permissions ---
// Mirrors apps/api/app/auth/schemas.py, apps/api/app/staff/schemas.py, and
// apps/api/app/roles/schemas.py. Keep these in sync by hand until a
// generation step exists — ARCHITECTURE_AND_TECH_STACK.md section 5.5.

export type AccountStatus = "invited" | "active" | "suspended" | "disabled" | "locked" | "archived";
export type EmploymentStatus = "full_time" | "part_time" | "contract" | "intern";
export type InvitationStatus = "pending" | "accepted" | "revoked" | "expired";

export interface RoleRef {
  id: string;
  code: string;
  name: string;
}

export interface CurrentUser {
  id: string;
  employee_code: string;
  first_name: string;
  last_name: string | null;
  display_name: string;
  email: string;
  phone_e164: string | null;
  department_id: string | null;
  job_title: string | null;
  account_status: AccountStatus;
  employment_status: EmploymentStatus;
  is_privileged: boolean;
  last_login_at: string | null;
  timezone: string;
  avatar_storage_path: string | null;
  preferred_language: string | null;
  roles: RoleRef[];
  permissions: string[];
}

export interface StaffUserListItem {
  id: string;
  employee_code: string;
  display_name: string;
  email: string;
  department_id: string | null;
  job_title: string | null;
  account_status: AccountStatus;
  employment_status: EmploymentStatus;
  is_privileged: boolean;
}

export interface StaffUserDetail {
  id: string;
  employee_code: string;
  first_name: string;
  last_name: string | null;
  display_name: string;
  email: string;
  phone_e164: string | null;
  department_id: string | null;
  job_title: string | null;
  account_status: AccountStatus;
  employment_status: EmploymentStatus;
  is_privileged: boolean;
  last_login_at: string | null;
  timezone: string;
  avatar_storage_path: string | null;
  preferred_language: string | null;
  roles: RoleRef[];
}

export interface Department {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
}

export interface RoleListItem {
  id: string;
  code: string;
  name: string;
  description: string | null;
  is_system_role: boolean;
  is_active: boolean;
}

export interface Permission {
  id: string;
  code: string;
  module: string;
  action: string;
  description: string | null;
  is_sensitive: boolean;
}

export interface RolePermissions {
  role: RoleListItem;
  permission_codes: string[];
}

export interface Invitation {
  id: string;
  email: string;
  first_name: string;
  last_name: string | null;
  department_id: string | null;
  intended_role_id: string;
  status: InvitationStatus;
  invited_at: string;
  expires_at: string;
}

// --- Phase 5: Customers and Leads ---
// Mirrors apps/api/app/customers/schemas.py and apps/api/app/leads/schemas.py.

export type CustomerType = "individual" | "corporate";
export type CustomerStatus = "active" | "inactive" | "blacklisted" | "archived" | "merged";
export type CustomerSegment =
  | "new"
  | "repeat"
  | "loyal"
  | "vip"
  | "at_risk"
  | "dormant"
  | "high_aov"
  | "family"
  | "corporate"
  | "college_group"
  | "delivery_first"
  | "dine_in_first"
  | "discount_sensitive"
  | "complaint_recovery";
export type DietaryPreference = "vegetarian" | "non_vegetarian" | "vegan" | "jain" | "no_preference";
export type SpicePreference = "mild" | "medium" | "spicy" | "extra_spicy";
export type NoteType =
  | "general"
  | "service_preference"
  | "complaint"
  | "recovery"
  | "corporate"
  | "delivery"
  | "reservation"
  | "dietary";
export type ConsentType =
  | "whatsapp_marketing"
  | "email_marketing"
  | "sms_marketing"
  | "loyalty"
  | "feedback_request"
  | "personalization";
export type ConsentStatus = "granted" | "withdrawn" | "unknown";

export interface CustomerListItem {
  id: string;
  customer_number: string;
  display_name: string;
  customer_type: CustomerType;
  primary_phone_e164: string | null;
  primary_email: string | null;
  customer_status: CustomerStatus;
  customer_segment: CustomerSegment | null;
  assigned_staff_id: string | null;
  completed_order_count: number;
  lifetime_value_minor: number;
  last_order_at: string | null;
}

export interface Customer {
  id: string;
  customer_number: string;
  customer_type: CustomerType;
  first_name: string | null;
  last_name: string | null;
  organization_name: string | null;
  display_name: string;
  primary_phone_e164: string | null;
  primary_email: string | null;
  date_of_birth: string | null;
  anniversary_date: string | null;
  preferred_language: string | null;
  dietary_preference: DietaryPreference | null;
  spice_preference: SpicePreference | null;
  customer_status: CustomerStatus;
  customer_segment: CustomerSegment | null;
  acquisition_source: string | null;
  assigned_staff_id: string | null;
  first_order_at: string | null;
  last_order_at: string | null;
  completed_order_count: number;
  lifetime_value_minor: number;
  average_order_value_minor: number;
  last_activity_at: string | null;
  merged_into_customer_id: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface CustomerAddress {
  id: string;
  customer_id: string;
  label: string | null;
  recipient_name: string | null;
  phone_e164: string | null;
  address_line1: string;
  address_line2: string | null;
  landmark: string | null;
  locality: string | null;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  latitude: string | null;
  longitude: string | null;
  delivery_instructions: string | null;
  is_default: boolean;
  is_active: boolean;
}

export interface CustomerNote {
  id: string;
  customer_id: string;
  note_type: NoteType;
  content: string;
  is_sensitive: boolean;
  created_by: string;
  created_at: string;
  updated_at: string | null;
  updated_by: string | null;
}

export interface Tag {
  id: string;
  name: string;
  normalized_name: string;
  description: string | null;
  is_active: boolean;
}

export interface CustomerConsent {
  id: string;
  customer_id: string;
  consent_type: ConsentType;
  status: ConsentStatus;
  source: string;
  policy_version: string | null;
  granted_at: string | null;
  withdrawn_at: string | null;
}

export interface DuplicateCustomerMatch {
  customer: CustomerListItem;
  match_reasons: string[];
}

export interface MergePreview {
  source: Customer;
  surviving: Customer;
  conflicting_fields: string[];
  source_address_count: number;
  source_tag_count: number;
  source_note_count: number;
}

export interface TimelineEntry {
  id: string;
  action_code: string;
  actor_id: string | null;
  created_at: string;
  safe_metadata: Record<string, unknown> | null;
}

export type LeadType =
  | "corporate_catering"
  | "recurring_office_order"
  | "event_booking"
  | "group_dining"
  | "partnership"
  | "franchise_or_business_enquiry"
  | "general_sales_enquiry";
export type LeadSource =
  | "website"
  | "phone"
  | "walk_in"
  | "whatsapp"
  | "zomato_import"
  | "swiggy_import"
  | "meta_campaign"
  | "google_campaign"
  | "referral"
  | "corporate_outreach"
  | "event_enquiry"
  | "offline_qr";
export type LeadStatus =
  | "new"
  | "contacted"
  | "qualified"
  | "interested"
  | "follow_up_scheduled"
  | "proposal_shared"
  | "negotiating"
  | "won"
  | "lost"
  | "closed";
export type LeadPriority = "low" | "normal" | "high" | "urgent";
export type LostReason =
  | "budget"
  | "timing"
  | "no_response"
  | "chose_competitor"
  | "service_unavailable"
  | "location_issue"
  | "menu_mismatch"
  | "duplicate"
  | "invalid_enquiry";
export type LeadActivityType =
  | "call"
  | "email"
  | "whatsapp"
  | "meeting"
  | "proposal"
  | "note"
  | "status_change"
  | "assignment"
  | "follow_up_created"
  | "follow_up_completed"
  | "file_added"
  | "customer_conversion"
  | "order_conversion";
export type FollowUpStatus = "scheduled" | "due" | "completed" | "cancelled" | "missed";

export interface LeadListItem {
  id: string;
  lead_number: string;
  display_name: string;
  organization_name: string | null;
  lead_type: LeadType;
  source: LeadSource;
  status: LeadStatus;
  priority: LeadPriority;
  estimated_value_minor: number | null;
  requested_date: string | null;
  party_size: number | null;
  assigned_staff_id: string | null;
  next_follow_up_at: string | null;
  last_contact_at: string | null;
  created_at: string;
}

export interface Lead {
  id: string;
  lead_number: string;
  lead_type: LeadType;
  display_name: string;
  organization_name: string | null;
  contact_name: string | null;
  phone_e164: string | null;
  email: string | null;
  source: LeadSource;
  campaign_reference: string | null;
  status: LeadStatus;
  priority: LeadPriority;
  estimated_value_minor: number | null;
  party_size: number | null;
  requested_date: string | null;
  requested_time: string | null;
  assigned_staff_id: string | null;
  next_follow_up_at: string | null;
  last_contact_at: string | null;
  won_customer_id: string | null;
  lost_reason: LostReason | null;
  description: string | null;
  qualification_notes: string | null;
  food_preferences: string | null;
  budget_notes: string | null;
  do_not_contact: boolean;
  converted_at: string | null;
  converted_by: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface LeadActivityEntry {
  id: string;
  lead_id: string;
  activity_type: LeadActivityType;
  summary: string;
  performed_by: string | null;
  occurred_at: string;
}

export interface LeadFollowUp {
  id: string;
  lead_id: string;
  assigned_to: string;
  scheduled_at: string;
  status: FollowUpStatus;
  completed_at: string | null;
  outcome: string | null;
  purpose: string | null;
  channel: string | null;
  completed_by: string | null;
}

export interface DuplicateLeadMatch {
  lead: LeadListItem;
  match_reasons: string[];
}

export interface ConversionPreview {
  lead: Lead;
  possible_customer_matches: CustomerListItem[];
  will_create_new_customer: boolean;
}
