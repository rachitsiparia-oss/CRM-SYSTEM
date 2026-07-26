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

// --- Phase 6: Menu and Product Management ---
// Mirrors apps/api/app/menu/schemas.py.

export type FoodType = "vegetarian" | "non_vegetarian";
export type SpiceLevel = "mild" | "medium" | "hot" | "extra_hot";
export type AvailabilitySource =
  | "manual"
  | "inventory_derived"
  | "schedule"
  | "integration"
  | "override";

export interface MenuCategory {
  id: string;
  code: string;
  name: string;
  description: string | null;
  sort_order: number;
  is_active: boolean;
  version: number;
}

export interface ProductVariant {
  id: string;
  product_id: string;
  code: string;
  name: string;
  price_minor: number;
  sort_order: number;
  is_active: boolean;
  is_available: boolean;
  preparation_minutes: number | null;
  version: number;
}

export interface ProductListItem {
  id: string;
  product_code: string;
  name: string;
  display_name: string | null;
  category_id: string;
  food_type: FoodType;
  base_price_minor: number;
  is_active: boolean;
  is_available: boolean;
  is_featured: boolean;
  sort_order: number;
  image_storage_path: string | null;
}

export interface Product {
  id: string;
  product_code: string;
  barcode: string | null;
  category_id: string;
  name: string;
  display_name: string | null;
  slug: string;
  description: string | null;
  short_description: string | null;
  food_type: FoodType;
  is_jain_capable: boolean;
  is_vegan_capable: boolean;
  contains_egg: boolean;
  contains_dairy: boolean;
  contains_gluten: boolean;
  contains_nuts: boolean;
  contains_soy: boolean;
  contains_alcohol: boolean;
  spice_level: SpiceLevel | null;
  preparation_minutes: number | null;
  calories: number | null;
  base_price_minor: number;
  tax_category: string | null;
  is_active: boolean;
  is_available: boolean;
  availability_source: AvailabilitySource;
  manual_override_reason: string | null;
  dine_in_available: boolean;
  takeaway_available: boolean;
  delivery_available: boolean;
  image_storage_path: string | null;
  sort_order: number;
  is_featured: boolean;
  is_chef_recommended: boolean;
  version: number;
}

export interface ModifierGroup {
  id: string;
  name: string;
  min_select: number;
  max_select: number;
  is_required: boolean;
  sort_order: number;
  version: number;
}

export interface Modifier {
  id: string;
  name: string;
  default_price_minor: number;
  is_active: boolean;
  version: number;
}

export interface ModifierGroupItem {
  modifier_group_id: string;
  modifier_id: string;
  price_minor_override: number | null;
  sort_order: number;
  is_available: boolean;
}

export interface ProductModifierGroupMapping {
  product_id: string;
  modifier_group_id: string;
  sort_order: number;
}

export interface ProductImage {
  id: string;
  product_id: string;
  alt_text: string | null;
  sort_order: number;
  is_thumbnail: boolean;
  file_size_bytes: number;
  mime_type: string;
  signed_url: string;
}

// --- Phase 7: Orders and Order Lifecycle ---
// Mirrors apps/api/app/orders/schemas.py.

export type OrderSource =
  | "pos"
  | "walk_in"
  | "website"
  | "whatsapp"
  | "phone_call"
  | "zomato"
  | "swiggy"
  | "manual";
export type OrderType = "dine_in" | "takeaway" | "delivery";
export type OrderStatus =
  | "draft"
  | "pending_confirmation"
  | "confirmed"
  | "preparing"
  | "ready"
  | "completed"
  | "cancelled";
export type PaymentStatus = "pending" | "partial" | "paid" | "refunded" | "failed";
export type PaymentMethod = "cash" | "card" | "upi" | "online";
export type OrderDiscountType =
  | "flat"
  | "percentage"
  | "manual"
  | "coupon_placeholder"
  | "manager_override";
export type OrderChargeType = "packaging" | "delivery" | "service" | "other";
export type OrderTimelineEventType =
  | "created"
  | "assigned"
  | "status_changed"
  | "payment_updated"
  | "note_added"
  | "cancelled"
  | "completed"
  | "manual_edit";

export interface OrderItemModifierInput {
  modifier_id: string;
  quantity?: number;
}

export interface OrderItemInput {
  product_id: string;
  variant_id?: string | null;
  quantity?: number;
  modifiers?: OrderItemModifierInput[];
  kitchen_note?: string | null;
}

export interface OrderDiscountInput {
  discount_type: OrderDiscountType;
  amount_minor?: number | null;
  percentage?: number | null;
  reason: string;
  approved_by: string;
}

export interface OrderTaxInput {
  tax_name: string;
  rate_percentage?: number | null;
  amount_minor?: number | null;
}

export interface OrderChargeInput {
  charge_type: OrderChargeType;
  amount_minor: number;
}

export interface OrderCreateInput {
  customer_id?: string | null;
  lead_id?: string | null;
  source: OrderSource;
  order_type: OrderType;
  assigned_staff_id?: string | null;
  items: OrderItemInput[];
  discounts?: OrderDiscountInput[];
  taxes?: OrderTaxInput[];
  charges?: OrderChargeInput[];
  internal_notes?: string | null;
  customer_notes?: string | null;
  estimated_completion_time?: string | null;
  idempotency_key: string;
}

export interface OrderUpdateInput {
  customer_id?: string | null;
  lead_id?: string | null;
  internal_notes?: string | null;
  customer_notes?: string | null;
  estimated_completion_time?: string | null;
  expected_version?: number | null;
}

export interface OrderItemModifier {
  id: string;
  modifier_id: string | null;
  modifier_name_snapshot: string;
  price_minor_snapshot: number;
  quantity: number;
}

export interface OrderItem {
  id: string;
  order_id: string;
  product_id: string | null;
  variant_id: string | null;
  product_name_snapshot: string;
  variant_name_snapshot: string | null;
  product_code_snapshot: string | null;
  quantity: number;
  unit_price_minor: number;
  discount_minor: number;
  tax_minor: number;
  final_price_minor: number;
  kitchen_note: string | null;
  status: "active" | "cancelled";
  modifiers: OrderItemModifier[];
}

export interface OrderDiscount {
  id: string;
  discount_type: OrderDiscountType;
  amount_minor: number;
  percentage: number | null;
  reason: string;
  approved_by: string;
  created_by: string;
  created_at: string;
}

export interface OrderTax {
  id: string;
  tax_name: string;
  rate_percentage: number | null;
  amount_minor: number;
  created_at: string;
}

export interface OrderCharge {
  id: string;
  charge_type: OrderChargeType;
  amount_minor: number;
  created_at: string;
}

export interface OrderPayment {
  id: string;
  order_id: string;
  method: PaymentMethod;
  status: PaymentStatus;
  amount_minor: number;
  reference: string | null;
  notes: string | null;
  recorded_by: string;
  recorded_at: string;
  updated_at: string | null;
  updated_by: string | null;
}

export interface OrderNote {
  id: string;
  order_id: string;
  content: string;
  is_internal: boolean;
  created_by: string;
  created_at: string;
  updated_at: string | null;
  updated_by: string | null;
}

export interface OrderTimelineEntry {
  id: string;
  order_id: string;
  event_type: OrderTimelineEventType;
  summary: string;
  event_metadata: Record<string, unknown> | null;
  performed_by: string | null;
  occurred_at: string;
}

export interface OrderStatusHistoryEntry {
  id: string;
  order_id: string;
  previous_status: OrderStatus | null;
  new_status: OrderStatus;
  actor_id: string | null;
  reason: string | null;
  created_at: string;
}

export interface OrderAssignment {
  id: string;
  order_id: string;
  staff_id: string;
  assigned_by: string | null;
  assigned_at: string;
  unassigned_at: string | null;
}

export interface OrderListItem {
  id: string;
  order_number: string;
  customer_id: string | null;
  source: OrderSource;
  order_type: OrderType;
  status: OrderStatus;
  payment_status: PaymentStatus;
  assigned_staff_id: string | null;
  grand_total_minor: number;
  estimated_completion_time: string | null;
  created_at: string;
}

export interface OrderStatusCounts {
  pending_confirmation: number;
  preparing: number;
  ready: number;
  completed: number;
  cancelled: number;
}

export interface RecentOrderActivity {
  order_id: string;
  order_number: string;
  event_type: OrderTimelineEventType;
  summary: string;
  occurred_at: string;
}

export interface OrderDashboardStats {
  today_order_count: number;
  status_counts_today: OrderStatusCounts;
  revenue_today_minor: number;
  average_order_value_minor: number;
  recent_activity: RecentOrderActivity[];
}

export interface Order {
  id: string;
  order_number: string;
  customer_id: string | null;
  lead_id: string | null;
  source: OrderSource;
  order_type: OrderType;
  status: OrderStatus;
  payment_status: PaymentStatus;
  assigned_staff_id: string | null;
  subtotal_minor: number;
  discount_minor: number;
  tax_minor: number;
  charges_minor: number;
  grand_total_minor: number;
  internal_notes: string | null;
  customer_notes: string | null;
  estimated_completion_time: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
  discounts: OrderDiscount[];
  taxes: OrderTax[];
  charges: OrderCharge[];
}
